from fastapi import APIRouter

router = APIRouter()

from .routes import router as routes_router
router.include_router(routes_router)