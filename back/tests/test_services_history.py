import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.history import HistoryService
from app.repo.inventory import InventoryHistoryRepository
from app.schemas.inventory import InventoryRecordCreate
from app.db.base import InventoryHistory


@pytest.fixture
def mock_history_repo():
    repo = AsyncMock(spec=InventoryHistoryRepository)
    repo.session = AsyncMock()
    repo.session.commit = AsyncMock()
    repo.session.refresh = AsyncMock()
    return repo


@pytest.fixture
def history_service(mock_history_repo):
    return HistoryService(repo=mock_history_repo)


@pytest.mark.asyncio
async def test_create_record(history_service, mock_history_repo):
    """Создание одной записи"""
    mock_record = InventoryHistory(
        id=1,
        robot_id="RB-001",
        product_id="SKU-001",
        quantity=50,
        zone="A",
        row_number=1,
        shelf_number=1,
        status="OK",
        scanned_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    mock_history_repo.create_one.return_value = mock_record
    
    record_create = InventoryRecordCreate(
        robot_id="RB-001",
        product_id="SKU-001",
        quantity=50,
        zone="A",
        row_number=1,
        shelf_number=1,
        status="OK",
        scanned_at=datetime.utcnow()
    )
    
    result = await history_service.create_record(record_create)
    
    assert result.id == 1
    assert result.product_id == "SKU-001"
    mock_history_repo.create_one.assert_called_once()
    mock_history_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_batch(history_service, mock_history_repo):
    """Массовое создание записей"""
    mock_records = [
        InventoryHistory(
            id=i,
            robot_id="RB-001",
            product_id=f"SKU-{i:03d}",
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=i,
            status="OK",
            scanned_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        for i in range(1, 4)
    ]
    
    mock_history_repo.create_many.return_value = mock_records
    
    records_create = [
        InventoryRecordCreate(
            robot_id="RB-001",
            product_id=f"SKU-{i:03d}",
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=i,
            status="OK",
            scanned_at=datetime.utcnow()
        )
        for i in range(1, 4)
    ]
    
    results = await history_service.create_batch(records_create)
    
    assert len(results) == 3
    assert results[0].product_id == "SKU-001"
    assert results[2].product_id == "SKU-003"
    mock_history_repo.create_many.assert_called_once()


@pytest.mark.asyncio
async def test_get_history_with_filters(history_service, mock_history_repo):
    """Получение истории с фильтрами"""
    mock_records = [
        InventoryHistory(
            id=1,
            robot_id="RB-001",
            product_id="SKU-001",
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=1,
            status="OK",
            scanned_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
    ]
    
    mock_history_repo.list.return_value = (mock_records, 1)
    
    result = await history_service.get_history(
        dt_from=None,
        dt_to=None,
        zones=["A"],
        statuses=["OK"],
        product_id=None,
        q=None,
        limit=50,
        offset=0
    )
    
    # Проверяем базовые поля
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].zone == "A"


@pytest.mark.asyncio
async def test_get_recent_scans(history_service, mock_history_repo):
    """Получение последних сканов"""
    mock_records = [
        InventoryHistory(
            id=i,
            robot_id="RB-001",
            product_id=f"SKU-{i:03d}",
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=1,
            status="OK",
            scanned_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        for i in range(1, 6)
    ]
    
    mock_history_repo.recent_scans.return_value = mock_records
    
    results = await history_service.get_recent_scans(limit=5)
    
    assert len(results) == 5
    mock_history_repo.recent_scans.assert_called_once_with(limit=5)


@pytest.mark.asyncio
async def test_get_records_by_ids(history_service, mock_history_repo):
    """Получение записей по ID"""
    mock_records = [
        InventoryHistory(
            id=1,
            robot_id="RB-001",
            product_id="SKU-001",
            quantity=50,
            zone="A",
            row_number=1,
            shelf_number=1,
            status="OK",
            scanned_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        ),
        InventoryHistory(
            id=3,
            robot_id="RB-001",
            product_id="SKU-003",
            quantity=30,
            zone="B",
            row_number=2,
            shelf_number=2,
            status="LOW_STOCK",
            scanned_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
    ]
    
    mock_history_repo.get_by_ids.return_value = mock_records
    
    results = await history_service.get_records_by_ids([1, 3])
    
    assert len(results) == 2
    assert results[0].id == 1
    assert results[1].id == 3


@pytest.mark.asyncio
async def test_get_summary(history_service, mock_history_repo):
    """Получение сводной статистики"""
    mock_summary = {
        "total": 100,
        "unique_products": 25,
        "OK": 70,
        "LOW_STOCK": 20,
        "CRITICAL": 10
    }
    
    mock_history_repo.summary.return_value = mock_summary
    
    result = await history_service.get_summary(
        dt_from=None,
        dt_to=None,
        zones=None,
        statuses=None,
        product_id=None
    )
    
    assert result.total == 100
    assert result.unique_products == 25
    assert result.OK == 70
    assert result.LOW_STOCK == 20
    assert result.CRITICAL == 10


@pytest.mark.asyncio
async def test_get_activity_last_hour(history_service, mock_history_repo):
    """Получение активности за последний час"""
    now = datetime.utcnow()
    mock_activity = [
        (now, 10),
        (now, 15),
        (now, 8)
    ]
    
    mock_history_repo.activity_last_hour.return_value = mock_activity
    
    result = await history_service.get_activity_last_hour()
    
    assert len(result.points) == 3
    assert result.points[0].count == 10
    assert result.points[1].count == 15
    assert result.points[2].count == 8


@pytest.mark.asyncio
async def test_delete_records(history_service, mock_history_repo):
    """Удаление записей"""
    mock_history_repo.delete_by_ids.return_value = 3
    
    deleted_count = await history_service.delete_records([1, 2, 3])
    
    assert deleted_count == 3
    mock_history_repo.delete_by_ids.assert_called_once_with([1, 2, 3])
    mock_history_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_records_none_found(history_service, mock_history_repo):
    """Удаление несуществующих записей"""
    mock_history_repo.delete_by_ids.return_value = 0
    
    deleted_count = await history_service.delete_records([999, 1000])
    
    assert deleted_count == 0