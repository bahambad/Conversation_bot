__all__ = ("router", )

from aiogram import Router

from .commands import router as commands_router
from .callback_handlers import router as callback_router
from .not_processing import router as not_processing_router
from .audio_processing import router as audio_processing_router
from .video_processing import router as video_processing_router

router = Router(name=__name__)

router.include_routers(
    callback_router,
    commands_router,
    audio_processing_router,
    video_processing_router,
    )

# Always last!
router.include_router(not_processing_router)