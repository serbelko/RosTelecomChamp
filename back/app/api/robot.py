from fastapi import APIRouter, Depends, status
from dependency_injector.wiring import inject, Provide
from app.services.robot import RobotService
from app.core.container import Container
from app.schemas.robot import RobotBase

router = APIRouter(prefix="/robots", tags=["robot"])

@router.post("/data", status_code=status.HTTP_200_OK)
@inject
async def upload_robot_data(
    payload: RobotBase,
    service: RobotService = Depends(Provide[Container.robot_service]),
):
    await service.process_robot_data(payload)
    return {"detail": "Robot data processed successfully"}