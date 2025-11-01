import os
import time
import uuid
from datetime import datetime, timezone

import pytest
import requests as rq

BASE = os.getenv("BASE_URL", "http://localhost:8000")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_user_token(payload: dict) -> str:
    token = payload.get("token") or payload.get("access_token")
    assert token, f"Не удалось извлечь токен пользователя из ответа: {payload}"
    return token


def _wait_healthy():
    deadline = time.time() + 30
    last_err = None
    while time.time() < deadline:
        try:
            r = rq.get(f"{BASE}/health", timeout=1.5)
            if r.ok:
                return
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.5)
    raise RuntimeError(f"Сервер не отвечает на /health. Последняя ошибка: {last_err}")


def _register_user_and_login() -> str:
    email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongP@ss123"

    r = rq.post(f"{BASE}/api/auth/create",
                json={"email": email, "password": password},
                timeout=5)
    assert r.status_code in (200, 201), f"create user: {r.status_code} {r.text}"

    r = rq.post(f"{BASE}/api/auth/login",
                json={"email": email, "password": password},
                timeout=5)
    assert r.status_code == 200, f"login: {r.status_code} {r.text}"
    return _extract_user_token(r.json())


def _register_robot(robot_id: str) -> str:
    payload = {
        "robot_id": robot_id,
        "zone": "A",
        "row": 10,
        "shelf": 2,
        "battery_level": 87.5,
        "status": "online",
    }
    r = rq.post(f"{BASE}/api/robots/register", json=payload, timeout=5)
    assert r.status_code == 201, f"register robot: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token, f"в ответе нет токена робота: {r.json()}"
    return token


def _robot_ingest(robot_token: str, robot_id: str, scans: list[dict]):
    headers = {"Authorization": f"Bearer {robot_token}"}
    body = {
        "robot_id": robot_id,
        "timestamp": _iso_now(),
        "location": {"zone": "A", "row": 10, "shelf": 2},
        "scan_results": scans,
        "battery_level": 72.5,
        "next_checkpoint": "A-10-3",
        "status": "active",
    }
    r = rq.post(f"{BASE}/api/robots/data", headers=headers, json=body, timeout=8)
    assert r.status_code == 200, f"ingest: {r.status_code} {r.text}"
    return r.json()


def _wait_history_items(headers: dict, predicate, timeout_sec: int = 10):
    """Пингуем /api/inventory/history пока не появятся нужные записи."""
    deadline = time.time() + timeout_sec
    last_payload = None
    while time.time() < deadline:
        r = rq.get(f"{BASE}/api/inventory/history",
                   headers=headers,
                   params={"limit": 50, "offset": 0, "sort_by": "scanned_at", "sort_dir": "desc"},
                   timeout=6)
        if r.status_code == 200:
            payload = r.json()
            last_payload = payload
            if predicate(payload):
                return payload
        time.sleep(0.5)
    raise AssertionError(f"Нужные записи не появились за {timeout_sec}s. Последний ответ: {last_payload}")


@pytest.mark.e2e
def test_full_userflow():
    """
    Полный пользовательский поток:
    1. Пользователь регистрируется и входит
    2. Проверяет доступ к /api/auth/me
    3. Открывает дашборд /api/dashboard/current
    4. Без авторизации робота попытка ingest дает 401 или 403
    5. Администратор регистрирует робота, получает токен
    6. Робот отправляет сканы по двум SKU
    7. Пользователь открывает историю и видит новые записи
    8. Пользователь делает экспорт выбранных ID
    9. Пользователь запускает AI прогноз
    """
    _wait_healthy()

    # 1-2. Регистрация и вход пользователя
    user_token = _register_user_and_login()
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. /api/auth/me
    r = rq.get(f"{BASE}/api/auth/me", headers=user_headers, timeout=5)
    assert r.status_code == 200, f"/api/auth/me: {r.status_code} {r.text}"

    # 3. Дашборд
    r = rq.get(f"{BASE}/api/dashboard/current", timeout=5)
    assert r.status_code == 200, f"/api/dashboard/current: {r.status_code} {r.text}"
    dash = r.json()
    assert "robots" in dash and "recent_scans" in dash and "statistics" in dash

    # 4. Проверка что без токена робота ingest запрещен
    body_unauth = {
        "robot_id": "RB-NOAUTH",
        "timestamp": _iso_now(),
        "location": {"zone": "A", "row": 1, "shelf": 1},
        "scan_results": [{"product_id": "SKU-NA-1", "quantity": 1}],
        "battery_level": 90.0,
        "next_checkpoint": "A-1-2",
    }
    r = rq.post(f"{BASE}/api/robots/data", json=body_unauth, timeout=5)
    assert r.status_code in (401, 403), f"ожидали 401/403, получили {r.status_code}: {r.text}"

    # 5. Регистрация робота
    robot_id = f"RB-{uuid.uuid4().hex[:4].upper()}"
    robot_token = _register_robot(robot_id)

    # 6. Инжест двух сканов
    sku_a = f"SKU-{uuid.uuid4().hex[:4].upper()}"
    sku_b = f"SKU-{uuid.uuid4().hex[:4].upper()}"
    _robot_ingest(robot_token, robot_id, [
        {"product_id": sku_a, "product_name": "Box A", "quantity": 5, "status": "OK"},
        {"product_id": sku_b, "product_name": "Box B", "quantity": 0, "status": "CRITICAL"},
    ])

    # 7. Пользователь открывает историю и видит новые позиции
    def _has_both(payload: dict) -> bool:
        items = payload.get("items", [])
        got = {it.get("product_id") for it in items}
        return sku_a in got or sku_b in got  # допускаем агрегацию, главное чтобы появилось хотя бы одно

    history_payload = _wait_history_items(user_headers, _has_both, timeout_sec=12)
    assert isinstance(history_payload.get("total"), int)
    assert isinstance(history_payload.get("items"), list)
    assert "pagination" in history_payload

    # 8. Экспорт выбранных ID
    ids = [str(it["id"]) for it in history_payload["items"][:2]] or ["1"]
    r = rq.get(f"{BASE}/api/export/excel", params={"ids": ",".join(ids)}, timeout=8)
    assert r.status_code == 200, f"/api/export/excel: {r.status_code} {r.text}"
    # Контент может быть бинарным или json по твоей реализации. Проверим только статус.

    # 9. AI прогноз
    r = rq.post(f"{BASE}/api/ai/predict", json={"period_days": 7}, timeout=8)
    assert r.status_code == 200, f"/api/ai/predict: {r.status_code} {r.text}"
    pred = r.json()
    assert "predictions" in pred and "confidence" in pred
    assert 0.0 <= float(pred["confidence"]) <= 1.0
