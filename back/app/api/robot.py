from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from app.services.robot_service import RobotService
from app.core.container import Container

router = APIRouter(prefix="/robots", tags=["Robots"])

@router.post("/data")
@inject
async def upload_data(
    payload: dict,
    service: RobotService = Depends(Provide[Container.robot_service]),
):
    return await service.process_robot_data(payload)