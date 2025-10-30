# app/api/robot.py

from fastapi import APIRouter, Depends, status, Request, HTTPException
from dependency_injector.wiring import inject, Provide
import structlog

from app.services.robot import RobotService
from app.core.container import Container
from app.schemas.robot import RobotBase, RobotRegisterRequest, RobotRegisterResponse
from app.schemas.request import RobotIngestResponse, RobotIngestResult

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/robots", tags=["robot"])


@router.post(
    "/data",
    status_code=status.HTTP_200_OK,
    response_model=RobotIngestResponse,
    summary="Загрузка телеметрии робота",
    description=(
        "Робот отправляет своё состояние и результаты сканирования полок. "
        "Запрос должен быть аутентифицирован через RobotAuthMiddleware "
        "(заголовок `Authorization: Bearer <robot_token>`)."
    ),
    responses={
        200: {
            "description": "Данные успешно записаны",
            "model": RobotIngestResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Robot data processed successfully",
                        "result": {
                            "robot": {
                                "robot_id": "RB-003",
                                "battery_level": 72.5,
                                "zone": "A",
                                "row": 10,
                                "shelf": 2,
                                "status": "active",
                                "last_update": "2025-10-29T01:32:11.123456+00:00"
                            },
                            "ingested_records": 3,
                            "created_new_robot": False
                        }
                    }
                }
            }
        },
        401: {
            "description": "Нет или некорректный токен робота",
            "content": {
                "application/json": {
                    "example": {"detail": "Robot not authenticated"}
                }
            },
        },
        403: {
            "description": "robot_id в токене не совпадает с robot_id в теле запроса",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Robot ID mismatch: token does not match payload"
                    }
                }
            },
        },
        500: {
            "description": "Ошибка сервера при обработке данных робота",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to process robot data"
                    }
                }
            },
        },
    },
)
@inject
async def upload_robot_data(
    request: Request,
    payload: RobotBase,
    service: RobotService = Depends(Provide[Container.robot_service]),
) -> RobotIngestResponse:
    """
    Этот докстринг не попадёт в Swagger (там уже есть summary/description),
    но он полезен для разработчиков, читающих код.
    """

    # 1. Проверяем, что мидлвара проставила роботский контекст
    robot_ctx = getattr(request.state, "current_robot", None)
    if not robot_ctx or "robot_id" not in robot_ctx:
        raise HTTPException(status_code=401, detail="Robot not authenticated")

    robot_id_from_token = robot_ctx["robot_id"]

    # 2. Проверяем, что робот не подменил свой ID в теле запроса
    if payload.robot_id != robot_id_from_token:
        logger.warning(
            "robot.id_mismatch",
            claimed=payload.robot_id,
            token=robot_id_from_token,
        )
        raise HTTPException(
            status_code=403,
            detail="Robot ID mismatch: token does not match payload",
        )

    # 3. Обрабатываем данные робота через доменную логику
    try:
        result_data = await service.process_robot_data(payload)
    except Exception as e:
        logger.exception("robot.upload_failed", robot_id=payload.robot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process robot data",
        )

    # 4. Возвращаем унифицированный ответ
    return RobotIngestResponse(
        detail="Robot data processed successfully",
        result=RobotIngestResult(**result_data),
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RobotRegisterResponse,
    summary="Зарегистрировать нового робота",
    description=(
        "Создаёт или обновляет запись о роботе и возвращает ему авторизационный токен. "
        "Этот токен потом используется роботом в заголовке Authorization: Bearer <token> "
        "при отправке телеметрии на /robots/data.\n\n"
        "Этот эндпоинт вызывается администратором/системой, не самим роботом."
    ),
)
@inject
async def register_robot(
    payload: RobotRegisterRequest,
    service: RobotService = Depends(Provide[Container.robot_service]),
) -> RobotRegisterResponse:
    try:
        result = await service.register_robot(payload)
        return result
    except Exception as e:
        logger.exception("robot.register_failed", robot_id=payload.robot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to register robot"
        )

