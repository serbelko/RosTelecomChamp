# robot_emulator.py
import json
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def iso_utc_now() -> str:
    # ISO 8601 с 'Z' как требуют многие OpenAPI клиенты
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Product:
    id: str
    name: str


class RobotEmulator:
    def __init__(self, robot_id: str, api_base: str, update_interval: float = 10.0):
        """
        robot_id: строковый ID, например 'RB-001'
        api_base: базовый URL бэкенда, например 'http://backend:8000'
        """
        self.robot_id = robot_id
        self.api_base = api_base.rstrip("/")
        self.update_interval = update_interval

        # Состояние робота
        self.battery = 100.0
        self.zone = "A"
        self.row = 1
        self.shelf = 1
        self.status = "online"  # опционально по схеме

        # Токен авторизации, получим при регистрации
        self.token: Optional[str] = None

        # Тестовые товары (могут не существовать в БД — бекенд должен уметь ensure_exist)
        self.products: List[Product] = [
            Product("TEL-4567", "Роутер RT-AC68U"),
            Product("TEL-8901", "Модем DSL-2640U"),
            Product("TEL-2435", "Коммутатор SG-108"),
            Product("TEL-6789", "IP-телефон T46S"),
            Product("TEL-3456", "Кабель UTP Cat6"),
        ]

        # Настроим сессию requests с ретраями на сетевые сбои
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=frozenset(["GET", "POST"]),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ============ Данные/движение ============

    def generate_scan_results(self) -> List[Dict]:
        k = random.randint(1, 3)
        picked = random.sample(self.products, k=k)
        results: List[Dict] = []
        for p in picked:
            qty = random.randint(5, 100)
            if qty > 20:
                st = "OK"
            elif qty > 10:
                st = "LOW_STOCK"
            else:
                st = "CRITICAL"
            results.append(
                {
                    "product_id": p.id,
                    "product_name": p.name,   # по схеме поле опционально, можно не присылать
                    "quantity": qty,
                    "status": st,
                }
            )
        return results

    def step_location(self) -> None:
        """Простейший патруль по полкам A..E, рядам 1..20, полкам 1..10"""
        self.shelf += 1
        if self.shelf > 10:
            self.shelf = 1
            self.row += 1
        if self.row > 20:
            self.row = 1
            self.zone = chr(ord(self.zone) + 1)
            if self.zone > "E":
                self.zone = "A"

        # трата батареи
        self.battery -= random.uniform(0.1, 0.5)
        if self.battery < 20:
            # "зарядка" и отметим статус
            self.status = "charging"
            self.battery = 100.0
        else:
            self.status = "online"

    # ============ HTTP-взаимодействие ============

    def headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def register(self) -> None:
        """POST /api/robots/register -> получить токен."""
        url = f"{self.api_base}/api/robots/register"
        payload = {
            "robot_id": self.robot_id,
            # стартовые координаты/батарея — поля опциональные по схеме
            "zone": self.zone,
            "row": self.row,
            "shelf": self.shelf,
            "battery_level": round(self.battery, 1),
            "status": self.status,
        }
        resp = self.session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"[{self.robot_id}] Register failed {resp.status_code}: {resp.text}")
        data = resp.json()
        tok = data.get("token")
        if not tok:
            raise RuntimeError(f"[{self.robot_id}] Register ok but token missing: {data}")
        self.token = tok
        print(f"[{self.robot_id}] Registered, token acquired")

    def send_telemetry_once(self) -> None:
        """POST /api/robots/data с телеметрией RobotBase."""
        if not self.token:
            self.register()

        url = f"{self.api_base}/api/robots/data"
        body = {
            "robot_id": self.robot_id,
            "timestamp": iso_utc_now(),
            "location": {"zone": self.zone, "row": self.row, "shelf": self.shelf},
            "scan_results": self.generate_scan_results(),
            "battery_level": round(self.battery, 1),
            "next_checkpoint": f"{self.zone}-{self.row}-{self.shelf}",
            # "status" — опционально, но может быть полезно
            "status": self.status,
        }

        resp = self.session.post(url, json=body, headers=self.headers(), timeout=10)

        if resp.status_code == 401:
            # токен просрочен/неверен — пере-регистрация
            print(f"[{self.robot_id}] 401 Unauthorized, re-registering...")
            self.token = None
            self.register()
            resp = self.session.post(url, json=body, headers=self.headers(), timeout=10)

        if resp.status_code != 200:
            raise RuntimeError(f"[{self.robot_id}] Telemetry failed {resp.status_code}: {resp.text}")

        print(f"[{self.robot_id}] Telemetry OK")

    def run_forever(self) -> None:
        """Основной цикл с экспоненциальным бэкоффом при сетевых ошибках."""
        backoff = 1.0
        while True:
            try:
                self.send_telemetry_once()
                self.step_location()
                backoff = 1.0
                time.sleep(self.update_interval)
            except requests.exceptions.RequestException as e:
                print(f"[{self.robot_id}] Network error: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
            except Exception as e:
                print(f"[{self.robot_id}] Error: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)


def main():
    api_url = os.getenv("API_URL", "http://backend:8000").strip().rstrip("/")
    robots_count = int(os.getenv("ROBOTS_COUNT", "5"))
    update_interval = float(os.getenv("UPDATE_INTERVAL", "10"))

    threads: List[threading.Thread] = []
    for i in range(1, robots_count + 1):
        rid = f"RB-{i:03d}"
        emu = RobotEmulator(robot_id=rid, api_base=api_url, update_interval=update_interval)
        t = threading.Thread(target=emu.run_forever, name=f"robot-{rid}", daemon=True)
        t.start()
        threads.append(t)

    # держим главный поток
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down robot emulator")


if __name__ == "__main__":
    main()
