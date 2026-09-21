from fastapi import APIRouter

from api.v1.telegram import router as telegram_router


router = APIRouter()

router.include_router(
    telegram_router,
)