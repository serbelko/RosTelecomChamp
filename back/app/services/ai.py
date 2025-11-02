from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Sequence

import httpx

from app.repo.product import ProductRepository
from app.repo.inventory import InventoryHistoryRepository
from app.schemas.ai import (
    AIPredictionRequest,
    AIPredictionResponse,
    ProductPrediction,
)
from app.db.base import AiPrediction


# БАЗОВЫЕ НАСТРОЙКИ OPENROUTER
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
# Можно указать список через запятую в OPENROUTER_MODELS.
# Если переменная не задана, возьмём рабочую у вас модель и пару резервов.
OPENROUTER_MODELS_ENV = os.getenv("OPENROUTER_MODELS", "").strip()
if OPENROUTER_MODELS_ENV:
    OPENROUTER_MODELS = [m.strip() for m in OPENROUTER_MODELS_ENV.split(",") if m.strip()]
else:
    OPENROUTER_MODELS = [
        os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-0528-qwen3-8b:free"),
        "deepseek/deepseek-chat-v3.1",
        "nvidia/nemotron-nano-9b-v2:free",
    ]
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Итоговый путь к Chat Completions
OPENROUTER_CHAT_COMPLETIONS_URL = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

SYSTEM_PROMPT = (
    "Ты аналитик склада. На основе списка товаров с текущим остатком, "
    "оптимальным запасом и короткой историей сканов сделай прогноз на заданный период. "
    "Верни только валидный JSON по схеме. Никаких пояснений, комментариев, markdown."
)

def _build_user_prompt(period_days: int, products_payload: dict) -> str:
    ctx = json.dumps(
        {"period_days": period_days, "products": products_payload["products"]},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        "Цели:\n"
        "1) Оценить expected_demand за период\n"
        "2) Дни до исчерпания\n"
        "3) Рекомендованный заказ\n"
        "\n"
        "Правила:\n"
        "- Только JSON объект. Без текста.\n"
        "- Один product_id в predictions на каждый входной товар, порядок совпадает с входом.\n"
        "- Числа неотрицательные. expected_demand и recommended_order_quantity целые. "
        "days_until_stockout с 1 десятичной. Без экспоненциальной записи.\n"
        "- Если данных мало, прогноз консервативный и пониженный confidence.\n"
        "- Рецепты:\n"
        "  avg_daily_demand по убыванию остатков и частоте наблюдений\n"
        "  days_until_stockout = current_qty / max(avg_daily_demand, 1e-9)\n"
        "  recommended_order_quantity = max(0, target - current_qty),\n"
        "  где target = max(optimal_stock, expected_demand), если optimal_stock задан, "
        "иначе target = expected_demand\n"
        "\n"
        "Схема ответа:\n"
        "{"
        "\"predictions\":[{\"product_id\":\"str\",\"category\":\"str|null\",\"expected_demand\":0,"
        "\"days_until_stockout\":0.0,\"recommended_order_quantity\":0}],"
        "\"confidence\":0.0}"
        "\n\n"
        f"INPUT={ctx}\n"
        "OUTPUT=JSON_ONLY"
    )

_JSON_RE = re.compile(r"\{.*\}", flags=re.S)
def _extract_json_block(text: str) -> str:
    m = _JSON_RE.search(text or "")
    if not m:
        raise ValueError("LLM did not return JSON object")
    return m.group(0)


class AIService:
    """
    LLM-прогнозатор через OpenRouter. Собирает компактный контекст из БД, вызывает модель,
    валидирует JSON, пишет агрегаты в AiPrediction и возвращает AIPredictionResponse.
    """

    def __init__(
        self,
        product_repo: ProductRepository,
        inventory_repo: InventoryHistoryRepository,
    ) -> None:
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo

        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

    async def predict(self, req: AIPredictionRequest) -> AIPredictionResponse:
        period_days = max(1, min(30, req.period_days or 7))

        # 1) Товары и фильтр по категориям
        products = await self.product_repo.list_all()
        if req.categories:
            cats = set(map(str.lower, req.categories))
            products = [p for p in products if (p.category or "").lower() in cats]
        if not products:
            return AIPredictionResponse(predictions=[], confidence=0.0)

        product_ids = [p.id for p in products]

        # 2) Текущий остаток и компактная история
        latest_by_pid = await self._latest_quantity_by_product(product_ids)
        history_pack = await self._history_compact(product_ids, days=30, limit_per_product=32)

        payload = {"products": []}
        for p in products:
            payload["products"].append({
                "product_id": p.id,
                "category": p.category,
                "optimal_stock": p.optimal_stock,
                "current_qty": latest_by_pid.get(p.id, 0),
                "history": history_pack.get(p.id, []),
            })

        # 3) Вызов LLM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(period_days, payload)},
        ]
        json_text = await self._call_llm(messages)

        # 4) Мини-валидация и сбор ответа
        obj = json.loads(json_text)
        preds_in = obj.get("predictions") or []
        overall_conf = obj.get("confidence", 0.8)

        today = date.today()
        session = self.inventory_repo.session

        predictions: List[ProductPrediction] = []
        for item in preds_in:
            product_id = str(item.get("product_id"))
            category = item.get("category")
            expected_demand = int(max(0, int(item.get("expected_demand", 0))))
            days_until_stockout = item.get("days_until_stockout")
            try:
                dus = float(days_until_stockout) if days_until_stockout is not None else None
            except Exception:
                dus = None
            recommended_order = int(max(0, int(item.get("recommended_order_quantity", 0))))

            predictions.append(
                ProductPrediction(
                    product_id=product_id,
                    category=category,
                    expected_demand=expected_demand,
                    expected_stockout_in_days=dus,
                )
            )

            session.add(
                AiPrediction(
                    product_id=product_id,
                    prediction_date=today,
                    days_until_stockout=int(dus) if dus is not None else None,
                    recommended_order=recommended_order,
                    confidence_score=float(overall_conf) if overall_conf is not None else None,
                )
            )

        await session.flush()

        try:
            conf = float(overall_conf)
        except Exception:
            conf = 0.8
        return AIPredictionResponse(predictions=predictions, confidence=round(conf, 2))

    async def _call_llm(self, messages: List[Dict]) -> str:
        """
        1) Пробуем серверный фолбэк OpenRouter через поле `models` (один запрос).
        2) Если получили 404/400 по модели, делаем клиентский перебор по одной.
        3) На 429/5xx используем экспоненциальные задержки.
        """
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            # Рекомендуется указывать реферер и X-Title, если есть публичный URL проекта:
            # "HTTP-Referer": os.getenv("APP_PUBLIC_URL", ""),
            # "X-Title": "Warehouse Forecast Service",
        }

        common = {
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 700,
        }

        delays = [0, 2, 5]  # на случай 429/5xx
        transient = {429, 502, 503, 504}

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Попытка 1: единый запрос с серверным фолбэком
            body = dict(common)
            body["models"] = OPENROUTER_MODELS
            for d in delays:
                if d:
                    await asyncio.sleep(d)
                try:
                    r = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, json=body, headers=headers)
                    if r.status_code in transient:
                        continue
                    if r.status_code in (400, 404):
                        # Скорее всего конкретная модель недоступна для ключа или в пуле
                        break  # пойдём на клиентский перебор
                    r.raise_for_status()
                    return self._extract_and_validate_json(r.json())
                except httpx.HTTPStatusError as e:
                    # печатаем тело ошибки для ясности
                    raise RuntimeError(f"OpenRouter {e.response.status_code}: {e.response.text}") from e
                except httpx.HTTPError:
                    # сетевой сбой - подождём и повторим
                    continue
                except (ValueError, json.JSONDecodeError) as e:
                    # ответ пришёл, но невалидный формат
                    raise RuntimeError(f"LLM returned invalid format: {e}") from e

            # Попытка 2: клиентский перебор по одной модели
            last_err: Optional[Exception] = None
            for model in OPENROUTER_MODELS:
                body_single = dict(common)
                body_single["model"] = model
                for d in delays:
                    if d:
                        await asyncio.sleep(d)
                    try:
                        r = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, json=body_single, headers=headers)
                        if r.status_code in transient:
                            last_err = RuntimeError(f"Transient {r.status_code}: {r.text}")
                            continue
                        r.raise_for_status()
                        return self._extract_and_validate_json(r.json())
                    except httpx.HTTPStatusError as e:
                        # 404 по модели или иной статус - пробуем следующую
                        last_err = RuntimeError(f"OpenRouter {e.response.status_code}: {e.response.text}")
                        break
                    except httpx.HTTPError as e:
                        last_err = e
                        continue
                    except (ValueError, json.JSONDecodeError) as e:
                        last_err = e
                        break

            raise RuntimeError(f"LLM call failed: {last_err}")

    @staticmethod
    def _extract_and_validate_json(data: Dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"No choices in response: {data}")
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        json_text = _extract_json_block(content)
        json.loads(json_text)  # валидация
        return json_text

    async def _latest_quantity_by_product(self, product_ids: Sequence[str]) -> Dict[str, int]:
        from sqlalchemy import select, func, and_
        from app.db.base import InventoryHistory
        s = self.inventory_repo.session
        sub = (
            select(
                InventoryHistory.product_id,
                func.max(InventoryHistory.scanned_at).label("max_ts"),
            )
            .where(InventoryHistory.product_id.in_(product_ids))
            .group_by(InventoryHistory.product_id)
            .subquery()
        )
        stmt = (
            select(InventoryHistory.product_id, InventoryHistory.quantity)
            .join(sub, and_(
                InventoryHistory.product_id == sub.c.product_id,
                InventoryHistory.scanned_at == sub.c.max_ts,
            ))
        )
        rows = (await s.execute(stmt)).all()
        return {pid: int(qty or 0) for pid, qty in rows}

    async def _history_compact(self, product_ids: Sequence[str], *, days: int, limit_per_product: int) -> Dict[str, List[Dict]]:
        from sqlalchemy import select, and_, desc
        from app.db.base import InventoryHistory
        s = self.inventory_repo.session
        dt_from = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                InventoryHistory.product_id,
                InventoryHistory.scanned_at,
                InventoryHistory.quantity,
                InventoryHistory.status,
            )
            .where(and_(
                InventoryHistory.product_id.in_(product_ids),
                InventoryHistory.scanned_at >= dt_from,
            ))
            .order_by(InventoryHistory.product_id, desc(InventoryHistory.scanned_at))
        )
        rows = (await s.execute(stmt)).all()
        acc: Dict[str, List[Dict]] = {}
        for pid, ts, qty, status in rows:
            bucket = acc.setdefault(pid, [])
            if len(bucket) < limit_per_product:
                bucket.append({"ts": ts.isoformat(), "qty": int(qty or 0), "status": status})
        return acc
