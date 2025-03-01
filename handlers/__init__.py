from aiogram import Router
from . import base, admin, settings, subscription

def setup_routers():
    """Setup all routers for the bot."""
    router = Router()
    
    # Include all routers
    router.include_router(base.router)
    router.include_router(admin.router)
    router.include_router(settings.router)
    router.include_router(subscription.router)
    
    return router
