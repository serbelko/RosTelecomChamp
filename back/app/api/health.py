from fastapi import APIRouter

router = APIRouter()


@router.get("/ping", tags=["Health"])
async def ping():
    """
    Health check endpoint.
    """
    return {"message": "pong"}
