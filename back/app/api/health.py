from fastapi import APIRouter

router = APIRouter(
    tags=["health"],
    redirect_slashes=False
)

@router.get("/health", summary="Liveness probe")
async def ping():
    return {"status": "ok"}