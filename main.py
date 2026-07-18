import asyncio
import logging
import sys

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import settings
from handlers import router
from rates import RateFetcher
from cache import cache
from utils import setup_logging

setup_logging("INFO")
logger = logging.getLogger(__name__)

session: aiohttp.ClientSession = None
rate_fetcher: RateFetcher = None

async def setup_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="rate", description="Show exchange rates"),
        BotCommand(command="ping", description="Check bot latency"),
    ]
    await bot.set_my_commands(commands)

async def on_startup(bot: Bot) -> None:
    global session, rate_fetcher
    logger.info("🚀 Starting Currency Converter Bot...")
    
    if not session or session.closed:
        session = aiohttp.ClientSession()
    
    rate_fetcher = RateFetcher(session)
    await setup_commands(bot)
    
    try:
        await rate_fetcher.get_rates(force_refresh=True)
        logger.info("✅ Initial rates fetched")
    except Exception as e:
        logger.error(f"❌ Failed to fetch initial rates: {e}")
    
    logger.info(f"✅ Bot started! ID: {bot.id}")

async def on_shutdown(bot: Bot) -> None:
    global session
    logger.info("🛑 Shutting down...")
    
    if session and not session.closed:
        await session.close()
    await cache.clear()
    await bot.session.close()
    logger.info("✅ Shutdown complete")

async def main():
    try:
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        dp = Dispatcher()
        dp.include_router(router)
        
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        dp.workflow_data["rate_fetcher"] = rate_fetcher
        
        logger.info("⏳ Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=types.AllowedUpdates.MESSAGE,
            skip_updates=True
        )
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())