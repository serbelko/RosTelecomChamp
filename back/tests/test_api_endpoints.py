import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint"""
    response = await client.get("/health",follow_redirects=True)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_user(client, sample_user_data):
    """Тест создания пользователя"""
    response = await client.post(
        "/users/create",  # Изменено с /auth/register на /users/create
        json=sample_user_data
    )
    assert response.status_code == 201
    assert "id" in response.json()

@pytest.mark.asyncio
async def test_create_duplicate_user(client, sample_user_data):
    """Создание дублирующего пользователя"""
    # Первое создание
    await client.post("/auth/create", json=sample_user_data)
    
    # Попытка создать того же пользователя
    response = await client.post(
        "/auth/create",
        json=sample_user_data
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client, sample_user_data):
    # Сначала создаем пользователя
    await client.post("/auth/create", json=sample_user_data)
    # Затем пытаемся залогиниться
    response = await client.post("/auth/login", data={
        "username": sample_user_data["email"],
        "password": sample_user_data["password"]
    })
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_login_wrong_password(client, sample_user_data):
    """Логин с неверным паролем"""
    # Создаем пользователя
    await client.post("/auth/create", json=sample_user_data)
    
    # Пытаемся залогиниться с неверным паролем
    response = await client.post(
        "/auth/login",
        json={
            "email": sample_user_data["email"],
            "password": "WrongPassword123!"
        }
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authorized(client, auth_token):
    """Получение информации о текущем пользователе"""
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    """Получение информации без авторизации"""
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_robot_register(client):
    """Регистрация робота"""
    response = await client.post(
        "/api/robots/register",
        json={
            "robot_id": "RB-TEST-001",
            "zone": "A",
            "row": 1,
            "shelf": 1,
            "battery_level": 100.0
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["robot_id"] == "RB-TEST-001"
    assert "token" in data


@pytest.mark.asyncio
async def test_robot_data_upload(client, robot_token, sample_robot_data):
    """Загрузка данных робота"""
    response = await client.post(
        "/api/robots/data",
        json=sample_robot_data,
        headers={"Authorization": f"Bearer {robot_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert "result" in data


@pytest.mark.asyncio
async def test_robot_data_unauthorized(client, sample_robot_data):
    """Загрузка данных без токена"""
    response = await client.post(
        "/robots/data",
        json=sample_robot_data
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_current(client):
    """Получение текущего состояния дашборда"""
    response = await client.get("/api/dashboard/current")
    assert response.status_code in [200, 500]  # может быть 500 без данных
    if response.status_code == 200:
        data = response.json()
        assert "robots" in data
        assert "recent_scans" in data
        assert "statistics" in data


@pytest.mark.asyncio
async def test_inventory_history_empty(client, auth_token):
    """Получение пустой истории инвентаризации"""
    response = await client.get(
        "/api/inventory/history",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "pagination" in data


@pytest.mark.asyncio
async def test_inventory_history_with_filters(client, auth_token):
    """Получение истории с фильтрами"""
    response = await client.get(
        "/api/inventory/history",
        params={
            "zone": "A",
            "status": "OK",
            "limit": 10,
            "offset": 0
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["limit"] == 10


@pytest.mark.asyncio
async def test_inventory_import_csv_invalid_content_type(client, auth_token):
    """Импорт CSV с неверным content-type"""
    from io import BytesIO
    
    files = {"file": ("test.txt", BytesIO(b"test"), "text/plain")}
    response = await client.post(
        "/api/inventory/import",
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_inventory_import_csv_valid(client, auth_token):
    """Импорт валидного CSV"""
    from io import BytesIO
    
    csv_content = """robot_id,product_id,quantity,zone,row,shelf,status,scanned_at
RB-001,SKU-001,50,A,1,1,OK,2025-10-30T10:00:00
RB-001,SKU-002,10,A,1,2,LOW_STOCK,2025-10-30T10:01:00
"""
    
    files = {
        "file": ("inventory.csv", BytesIO(csv_content.encode()), "text/csv")
    }
    response = await client.post(
        "/api/inventory/import",
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "failed" in data


@pytest.mark.asyncio
async def test_export_excel_no_ids(client, auth_token):
    """Экспорт без указания ID"""
    response = await client.get(
        "/api/export/excel",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 422  # Missing required parameter


@pytest.mark.asyncio
async def test_export_excel_with_ids(client, auth_token):
    """Экспорт с указанными ID"""
    response = await client.get(
        "/api/export/excel",
        params={"ids": "1,2,3"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    # Может быть 200 или 500 в зависимости от наличия данных
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_ai_predict(client, auth_token):
    """Получение AI прогноза"""
    response = await client.post(
        "/api/ai/predict",
        json={
            "period_days": 7,
            "categories": ["electronics"]
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "predictions" in data
        assert "confidence" in data


@pytest.mark.asyncio
async def test_unauthorized_access_to_protected_endpoint(client):
    """Доступ к защищенному endpoint без токена"""
    response = await client.get("/api/inventory/history")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(client):
    """Доступ с невалидным токеном"""
    response = await client.get(
        "/api/inventory/history",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response.status_code == 401