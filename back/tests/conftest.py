import os
import sys
import asyncio
import pytest
from pathlib import Path
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Ensure project's `back` package is importable
tests_dir = Path(__file__).resolve().parent
project_back = str(tests_dir.parent)
if project_back not in sys.path:
    sys.path.insert(0, project_back)

from app.db.base import Base, Robots, Product
from app.core.security import SecurityManager
from app.core.settings import settings
from app.db.session import get_session

# Set minimal environment variables for testing
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("PASSWORD_MIN_LENGTH", "4")
os.environ.setdefault("ASYNC_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/test_db")

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for all tests"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session():
    """Create clean database for each test"""
    engine = create_async_engine(
        settings.ASYNC_DATABASE_URL,
        echo=False,
        future=True
    )
    
    async_session = async_sessionmaker(
        engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    await engine.dispose()

@pytest.fixture
async def client(db_session):
    """Create test client"""
    from main import app
    
    async def override_get_db():
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            raise
    
    app.dependency_overrides[get_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Disable redirect following
        client.follow_redirects = False
        yield client
    
    app.dependency_overrides.clear()
    
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "testpassword",
        "full_name": "Test User"
    }

@pytest.fixture
def sample_robot_data():
    """Sample robot data for testing"""
    return {
        "robot_id": "RB-001",
        "name": "Test Robot",
        "location": "Test Location",
        "products": [
            {
                "sku": "TEST-SKU-1",
                "quantity": 10,
                "scan_time": datetime.utcnow().isoformat()
            }
        ]
    }

@pytest.fixture
async def test_robot(db_session):
    """Create test robot"""
    robot = Robots(
        robot_id="RB-001",
        name="Test Robot",
        location="Test Location"
    )
    db_session.add(robot)
    await db_session.flush()
    await db_session.refresh(robot)
    return robot

@pytest.fixture
async def test_product(db_session):
    """Create test product"""
    product = Product(
        sku="TEST-SKU",
        name="Test Product"
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)
    return product

@pytest.fixture
async def auth_token(db_session, sample_user_data):
    """Create user and return auth token"""
    from app.repo.user import UserRepository
    
    user_repo = UserRepository(db_session)
    user = await user_repo.create_user(
        email=sample_user_data["email"],
        password=sample_user_data["password"],
        full_name=sample_user_data["full_name"]
    )
    await db_session.flush()
    
    security = SecurityManager()
    token = security.create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=60)
    )
    return token

@pytest.fixture
async def robot_token(db_session, test_robot):
    """Create robot token"""
    security = SecurityManager()
    token = security.create_access_token(
        data={"sub": test_robot.robot_id, "is_robot": True},
        expires_delta=timedelta(minutes=60)
    )
    return token

@pytest.fixture
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def robot_headers(robot_token):
    """Return headers with robot token"""
    return {"Authorization": f"Bearer {robot_token}"}