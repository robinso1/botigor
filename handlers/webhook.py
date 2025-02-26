from aiohttp import web
from bot.services.payment import PaymentService
from bot.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

async def handle_yookassa_webhook(request: web.Request) -> web.Response:
    """Handle YooKassa webhook."""
    try:
        # Проверяем подпись запроса
        signature = request.headers.get("X-YooKassa-Signature")
        if not signature:
            logger.warning("Missing YooKassa signature")
            return web.Response(status=400)
        
        # Получаем данные запроса
        data = await request.json()
        logger.info(f"Received YooKassa webhook: {json.dumps(data)}")
        
        # Создаем сессию и сервис
        async with request.app["session_maker"]() as session:
            payment_service = PaymentService(session)
            
            # Обрабатываем уведомление
            if await payment_service.process_webhook(data):
                return web.Response(status=200)
            else:
                return web.Response(status=400)
                
    except Exception as e:
        logger.error(f"Error processing YooKassa webhook: {str(e)}", exc_info=True)
        return web.Response(status=500)

def setup_webhook_routes(app: web.Application) -> None:
    """Setup webhook routes."""
    app.router.add_post("/webhook/yookassa", handle_yookassa_webhook) 