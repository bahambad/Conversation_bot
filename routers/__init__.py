__all__ = ("router", )

from aiogram import Router

from .commands import router as commands_router
from .callback_handlers import router as callback_router
from .not_processing import router as not_processing_router
from .audio_processing import router as audio_processing_router
from .video_processing import router as video_processing_router
from .fragment_processing import router as fragment_processing_router
from .edit_processing import router as edit_processing_router
from .ban import router as ban_router

router = Router(name=__name__)

router.include_routers(
    ban_router,
    callback_router,
    commands_router,
    # В сессии монтажа файлы и текст забирает edit-роутер, поэтому он стоит перед остальными
    edit_processing_router,
    fragment_processing_router,
    audio_processing_router,
    video_processing_router,
    )

# Always last!
router.include_router(not_processing_router)