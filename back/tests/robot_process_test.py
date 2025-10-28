from dependency_injector.providers import Factory
from app.core.container import Container
from app.services.robot import RobotService

class FakeDB:
    async def commit(self): pass

async def test_process_robot_data():
    container = Container()
    container.robot_service.override(Factory(RobotService, db=FakeDB()))

    service = container.robot_service()
    await service.process_robot_data({"robot_id": "RB-001", "battery_level": 90})