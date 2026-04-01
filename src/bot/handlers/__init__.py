from aiogram import Router

from src.bot.handlers import admin, booking, callbacks, start


def setup_routers() -> Router:
    router = Router()
    router.include_router(admin.router)
    router.include_router(callbacks.router)
    router.include_router(booking.router)
    # start.router must be last — it has the catch-all message handler
    router.include_router(start.router)
    return router
