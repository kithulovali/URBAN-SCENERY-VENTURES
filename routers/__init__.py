from .auth import router as auth_router
from .users import router as users_router
from .products import router as products_router
from .orders import router as orders_router
from .payments import router as payments_router
from .ai import router as ai_router
from .agents import router as agents_router

__all__ = ["auth_router", "users_router", "products_router", "orders_router", "payments_router", "ai_router", "agents_router"]
