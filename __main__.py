from aiohttp import web
import os

async def health(request):
    return web.Response(text='OK')

app = web.Application()
app.router.add_get('/health', health)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    web.run_app(app, host='0.0.0.0', port=port) 