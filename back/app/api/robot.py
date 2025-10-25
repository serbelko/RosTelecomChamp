from fastapi import APIRouter, Depends, status
from dependency_injector.wiring import inject, Provide
from app.services.robot import RobotService
from app.core.container import Container
from app.schemas.robot import RobotCreate, RobotUpdate

router = APIRouter(prefix="/robots", tags=["robot"])

@router.post("/data", response_model=dict, status_code=status.HTTP_200_OK)
async def upload_robot_data(
    payload: RobotUpdate,
    service: RobotService):
    return await service.process_robot_data(payload)