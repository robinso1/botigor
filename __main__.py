from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def health(request):
    return web.Response(text='OK')

async def create_app():
    app = web.Application()
    app.router.add_get('/health', health)
    return app

def create_app_sync():
    import asyncio
    return asyncio.get_event_loop().run_until_complete(create_app())

if __name__ == "__main__":
    app = create_app_sync()
    web.run_app(app, port=8000) 