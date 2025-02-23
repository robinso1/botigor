from aiohttp import web
import asyncio

async def handle(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get("/", handle)

if __name__ == "__main__":
    web.run_app(app, port=8080) 