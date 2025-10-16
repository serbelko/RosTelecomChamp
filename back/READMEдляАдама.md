# 🚀 Установка и настройка окружения

## 1. Установка Python-зависимостей

Создай и активируй виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Установи все зависимости:

```bash
pip install -r requirements.txt
```

---

## 2. Установка Docker и Compose

### Для Ubuntu / Debian

```bash
sudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl enable --now docker
```

Проверь установку:

```bash
docker --version
docker-compose --version   # или docker compose version
```

---

## 3. Исправление ошибки `Permission denied`

Если при вызове `docker ps` или `docker compose` получаешь ошибку типа:

```
docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))
```

Выполни эти шаги:

### 1) Проверь, что демон запущен

```bash
sudo systemctl status docker
```

Если не active:

```bash
sudo systemctl enable --now docker
```

### 2) Проверь права на сокет

```bash
ls -l /var/run/docker.sock
# должно быть: srw-rw---- 1 root docker ... /var/run/docker.sock
```

Если группа `docker`, а тебя в ней нет, будет Permission denied.

### 3) Добавь себя в группу docker

```bash
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker $USER
newgrp docker
```

Проверь:

```bash
id -nG | tr ' ' '\n' | grep -x docker
```

### 4) Перезапусти демон

```bash
sudo systemctl restart docker
```

### 5) Проверка

```bash
docker ps
docker compose version
```

---

## 4. Базовые команды Docker

| Команда                               | Назначение                     |
| ------------------------------------- | ------------------------------ |
| `docker ps`                           | Показать запущенные контейнеры |
| `docker ps -a`                        | Показать все контейнеры        |
| `docker images`                       | Локальные образы               |
| `docker pull <image>`                 | Скачать образ                  |
| `docker run -d -p 5432:5432 postgres` | Запустить PostgreSQL           |
| `docker stop <container>`             | Остановить                     |
| `docker start <container>`            | Запустить                      |
| `docker rm <container>`               | Удалить                        |
| `docker rmi <image>`                  | Удалить образ                  |
| `docker logs <container>`             | Логи                           |
| `docker exec -it <container> bash`    | Войти в контейнер              |
| `docker compose up -d`                | Поднять все сервисы            |
| `docker compose down`                 | Остановить и удалить           |
| `docker compose logs -f`              | Логи всех сервисов             |

---

## 5. Базовые команды PostgreSQL

Если PostgreSQL в контейнере:

```bash
docker exec -it postgres bash
psql -U app_user -d app_db
```

Если локально:

```bash
psql -h localhost -U app_user -d app_db
```

| Команда                | Описание          |
| ---------------------- | ----------------- |
| `\l`                   | Список баз        |
| `\c app_db`            | Подключиться      |
| `\dt`                  | Таблицы           |
| `\d table_name`        | Структура таблицы |
| `SELECT * FROM users;` | SQL-запрос        |
| `\q`                   | Выйти             |

---

## 6. Быстрая проверка Docker + Postgres

```bash
docker run --name postgres_local -e POSTGRES_USER=app_user -e POSTGRES_PASSWORD=app_pass -e POSTGRES_DB=app_db -p 5432:5432 -d postgres:15
```

Проверь:

```bash
psql postgresql://app_user:app_pass@localhost:5432/app_db
```

Если видишь `app_db=#`, значит, база жива.

---

## 7. Запуск проекта

```bash
uvicorn app.main:app --reload
```

или, если есть `docker-compose.yml`:

```bash
docker compose up -d
```

---

🧠 **Итог:**
После этих шагов у тебя будет:

* Активное Python-окружение
* Рабочий Docker + Compose
* Запущенный PostgreSQL
* Права без sudo
* Готовность к запуску FastAPI
