import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.repo.user import UserRepository
from app.repo.robot import RobotRepository
from app.repo.inventory import InventoryHistoryRepository
from app.repo.product import ProductRepository
from app.schemas.user import DbUser, UserUpdate
from app.schemas.robot import RobotBase, Location, ScanResult
from app.schemas.inventory import InventoryRecordCreate
from app.core.exeptions import UserNotFoundException, UserAlreadyExistsException


@pytest.mark.asyncio
async def test_user_create(db_session):
    """Создание пользователя в БД"""
    repo = UserRepository(db_session)
    
    user_data = DbUser(
        id=str(uuid4()),
        email="test@example.com",
        password_hash="hashed_password",
        user_name="Test User",
        role="VIEWER"
    )
    
    user = await repo.create_user(user_data)
    
    assert user.email == "test@example.com"
    assert user.user_name == "Test User"
    assert user.role == "VIEWER"


@pytest.mark.asyncio
async def test_user_get_by_email(db_session):
    """Получение пользователя по email"""
    repo = UserRepository(db_session)
    
    user_data = DbUser(
        id=str(uuid4()),
        email="findme@example.com",
        password_hash="hashed",
        user_name="Find Me",
        role="VIEWER"
    )
    
    await repo.create_user(user_data)
    
    found = await repo.get_by_email("findme@example.com")
    assert found is not None
    assert found.email == "findme@example.com"


@pytest.mark.asyncio
async def test_user_exists_by_email(db_session):
    """Проверка существования пользователя"""
    repo = UserRepository(db_session)
    
    user_data = DbUser(
        id=str(uuid4()),
        email="exists@example.com",
        password_hash="hashed",
        user_name="Exists",
        role="VIEWER"
    )
    
    await repo.create_user(user_data)
    
    exists = await repo.exists_by_email("exists@example.com")
    assert exists is True
    
    not_exists = await repo.exists_by_email("notexists@example.com")
    assert not_exists is False


@pytest.mark.asyncio
async def test_user_update(db_session):
    """Обновление данных пользователя"""
    repo = UserRepository(db_session)
    
    user_data = DbUser(
        id=str(uuid4()),
        email="update@example.com",
        password_hash="hashed",
        user_name="Old Name",
        role="VIEWER"
    )
    
    user = await repo.create_user(user_data)
    
    update_data = UserUpdate(user_name="New Name", role="MANAGER")
    updated = await repo.change(user.id, update_data)
    
    assert updated.user_name == "New Name"
    assert updated.role == "MANAGER"


@pytest.mark.asyncio
async def test_robot_create(db_session):
    """Создание робота"""
    repo = RobotRepository(db_session)
    
    robot_data = RobotBase(
        robot_id="RB-CREATE-001",
        last_update=datetime.utcnow(),
        location=Location(zone="A", row=1, shelf=1),
        scan_results=[],
        battery_level=100.0,
        next_checkpoint="A-1-2",
        status="active"
    )
    
    robot = await repo.create(robot_data)
    await db_session.commit()
    
    assert robot.robot_id == "RB-CREATE-001"
    assert robot.battery_level == 100.0


@pytest.mark.asyncio
async def test_robot_get_by_id(db_session):
    """Получение робота по ID"""
    repo = RobotRepository(db_session)
    
    robot_data = RobotBase(
        robot_id="RB-FIND-001",
        last_update=datetime.utcnow(),
        location=Location(zone="B", row=5, shelf=3),
        scan_results=[],
        battery_level=85.0,
        next_checkpoint="B-5-4",
        status="active"
    )
    
    await repo.create(robot_data)
    await db_session.commit()
    
    found = await repo.get_by_id("RB-FIND-001")
    assert found is not None
    assert found.robot_id == "RB-FIND-001"


@pytest.mark.asyncio
async def test_robot_upsert_create(db_session):
    """Upsert создает нового робота"""
    repo = RobotRepository(db_session)
    
    robot_data = RobotBase(
        robot_id="RB-UPSERT-NEW",
        last_update=datetime.utcnow(),
        location=Location(zone="A", row=1, shelf=1),
        scan_results=[],
        battery_level=100.0,
        next_checkpoint="A-1-2",
        status="active"
    )
    
    robot, created = await repo.upsert_robot(robot_data)
    await db_session.commit()
    
    assert created is True
    assert robot.robot_id == "RB-UPSERT-NEW"


@pytest.mark.asyncio
async def test_robot_upsert_update(db_session):
    """Upsert обновляет существующего робота"""
    repo = RobotRepository(db_session)
    
    # Создаем робота
    robot_data = RobotBase(
        robot_id="RB-UPSERT-EXIST",
        last_update=datetime.utcnow(),
        location=Location(zone="A", row=1, shelf=1),
        scan_results=[],
        battery_level=100.0,
        next_checkpoint="A-1-2",
        status="active"
    )
    
    await repo.create(robot_data)
    await db_session.commit()
    
    # Обновляем через upsert
    updated_data = RobotBase(
        robot_id="RB-UPSERT-EXIST",
        last_update=datetime.utcnow(),
        location=Location(zone="B", row=10, shelf=5),
        scan_results=[],
        battery_level=50.0,
        next_checkpoint="B-10-6",
        status="active"
    )
    
    robot, created = await repo.upsert_robot(updated_data)
    await db_session.commit()
    
    assert created is False
    assert robot.zone == "B"
    assert robot.battery_level == 50.0


@pytest.mark.asyncio
async def test_product_ensure_exist(db_session):
    """Гарантирование существования продуктов"""
    repo = ProductRepository(db_session)
    
    products = {
        "SKU-001": "Product 1",
        "SKU-002": "Product 2",
        "SKU-003": "Product 3"
    }
    
    await repo.ensure_products_exist(products)
    await db_session.commit()
    
    all_products = await repo.list_all()
    product_ids = [p.id for p in all_products]
    
    assert "SKU-001" in product_ids
    assert "SKU-002" in product_ids
    assert "SKU-003" in product_ids


@pytest.mark.asyncio
async def test_inventory_create_one(db_session):
    """Создание одной записи инвентаризации"""
    # Сначала создадим продукт
    product_repo = ProductRepository(db_session)
    await product_repo.ensure_products_exist({"SKU-INV-001": "Test Product"})
    await db_session.commit()
    
    repo = InventoryHistoryRepository(db_session)
    
    record = InventoryRecordCreate(
        robot_id="RB-001",
        product_id="SKU-INV-001",
        quantity=50,
        zone="A",
        row_number=1,
        shelf_number=1,
        status="OK",
        scanned_at=datetime.utcnow()
    )
    
    created = await repo.create_one(record)
    await db_session.commit()
    
    assert created.product_id == "SKU-INV-001"
    assert created.quantity == 50


@pytest.mark.asyncio
async def test_inventory_list_with_filters(db_session):
    """Получение списка с фильтрами"""
    # Создаем продукт и записи
    product_repo = ProductRepository(db_session)
    await product_repo.ensure_products_exist({"SKU-FILTER-001": "Filter Product"})
    await db_session.commit()
    
    repo = InventoryHistoryRepository(db_session)
    
    # Создаем несколько записей
    for i in range(5):
        record = InventoryRecordCreate(
            robot_id="RB-001",
            product_id="SKU-FILTER-001",
            quantity=10 * (i + 1),
            zone="A" if i < 3 else "B",
            row_number=i,
            shelf_number=i,
            status="OK" if i < 3 else "LOW_STOCK",
            scanned_at=datetime.utcnow() - timedelta(hours=i)
        )
        await repo.create_one(record)
    
    await db_session.commit()
    
    # Фильтруем по зоне A
    items, total = await repo.list(zones=["A"], limit=10, offset=0)
    
    assert total == 3
    assert all(item.zone == "A" for item in items)


@pytest.mark.asyncio
async def test_inventory_recent_scans(db_session):
    """Получение последних сканов"""
    product_repo = ProductRepository(db_session)
    await product_repo.ensure_products_exist({"SKU-RECENT-001": "Recent Product"})
    await db_session.commit()
    
    repo = InventoryHistoryRepository(db_session)
    
    # Создаем записи с разным временем
    for i in range(10):
        record = InventoryRecordCreate(
            robot_id="RB-001",
            product_id="SKU-RECENT-001",
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=1,
            status="OK",
            scanned_at=datetime.utcnow() - timedelta(minutes=i)
        )
        await repo.create_one(record)
    
    await db_session.commit()
    
    recent = await repo.recent_scans(limit=5)
    
    assert len(recent) == 5
    # Проверяем, что отсортировано по убыванию времени
    for i in range(len(recent) - 1):
        assert recent[i].scanned_at >= recent[i + 1].scanned_at


@pytest.mark.asyncio
async def test_inventory_summary(db_session):
    """Получение сводной статистики"""
    product_repo = ProductRepository(db_session)
    await product_repo.ensure_products_exist({
        "SKU-STAT-001": "Product 1",
        "SKU-STAT-002": "Product 2"
    })
    await db_session.commit()
    
    repo = InventoryHistoryRepository(db_session)
    
    # Создаем записи с разными статусами
    records = [
        ("SKU-STAT-001", "OK"),
        ("SKU-STAT-001", "LOW_STOCK"),
        ("SKU-STAT-002", "CRITICAL"),
        ("SKU-STAT-002", "OK"),
    ]
    
    for product_id, status in records:
        record = InventoryRecordCreate(
            robot_id="RB-001",
            product_id=product_id,
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=1,
            status=status,
            scanned_at=datetime.utcnow()
        )
        await repo.create_one(record)
    
    await db_session.commit()
    
    summary = await repo.summary()
    
    assert summary["total"] == 4
    assert summary["unique_products"] == 2
    assert summary["OK"] == 2
    assert summary["LOW_STOCK"] == 1
    assert summary["CRITICAL"] == 1