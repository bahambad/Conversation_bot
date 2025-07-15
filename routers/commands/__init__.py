__all__ = ("router", )

from aiogram import Router

from .base import router as base_router
from .avangard import router as avangard_router

router = Router()

router.include_routers(base_router,
                       avangard_router,

)