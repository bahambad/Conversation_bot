from aiogram import Router

from .yt_dlp_keyboard_choosing_handlers import router as choosing_router
from .video_processing_keyboard_choosing_handlers import router as video_proc_router

router = Router(name=__name__)

router.include_routers(
    choosing_router,
    video_proc_router,
)