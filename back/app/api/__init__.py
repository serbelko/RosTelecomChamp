# НИЧЕГО лишнего. Только явный экспорт.
from .health import router as health_router
from .user import router as user_router
from .inventory import router as inventory_router

__all__ = ["health_router", "user_router"]
