from fastapi import FastAPI
import uvicorn
import logging
from app.api import health_router

app = FastAPI()
app.include_router(health_router)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Приложение запущено") 
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=2080)