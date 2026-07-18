
## 14. Additional File: webhook.py (Optional)

```python
"""
Webhook support for the Currency Converter Bot.
"""

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.webhook import aiohttp_server
from aiohttp import web

from config import settings
from handlers import router
from main import on_startup, on_shutdown

logger = logging.getLogger(__name__)

async def webhook_handler(request):
    """Handle incoming webhook requests."""
    bot = request.app["bot"]
    dp = request.app["dp"]
    
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def setup_webhook():
    """Setup webhook for the bot."""
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Store bot and dp in app
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp
    
    # Add webhook route
    app.router.add_post("/webhook", webhook_handler)
    
    # Setup webhook URL (replace with your server URL)
    webhook_url = "https://your-domain.com/webhook"
    await bot.set_webhook(webhook_url)
    
    # Setup commands
    from main import setup_commands
    await setup_commands(bot)
    
    # Run webhook server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    
    logger.info(f"Webhook server started on port 8080")
    logger.info(f"Webhook URL set to: {webhook_url}")
    
    return app

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_webhook())