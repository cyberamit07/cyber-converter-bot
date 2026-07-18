"""
Main entry point for the Currency Converter Bot.
Initializes and runs the bot with proper error handling.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

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

# Setup logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Global session and rate fetcher
session: aiohttp.ClientSession = None
rate_fetcher: RateFetcher = None

async def setup_commands(bot: Bot) -> None:
    """
    Set bot commands for menu.
    
    Args:
        bot: Bot instance
    """
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="rate", description="Show exchange rates"),
        BotCommand(command="ping", description="Check bot latency"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands set")

async def on_startup(bot: Bot) -> None:
    """
    Callback when bot starts.
    
    Args:
        bot: Bot instance
    """
    global session, rate_fetcher
    
    logger.info("Starting Currency Converter Bot...")
    
    # Initialize HTTP session
    if not session or session.closed:
        session = aiohttp.ClientSession()
    
    # Initialize rate fetcher
    rate_fetcher = RateFetcher(session)
    
    # Setup commands
    await setup_commands(bot)
    
    # Pre-fetch rates
    try:
        await rate_fetcher.get_rates(force_refresh=True)
        logger.info("Initial rates fetched successfully")
    except Exception as e:
        logger.error(f"Failed to fetch initial rates: {e}")
    
    logger.info(f"Bot started successfully! Bot ID: {bot.id}")
    logger.info(f"Supported currencies: {settings.supported_currencies}")
    logger.info(f"Cache TTL: {settings.cache_ttl}s")

async def on_shutdown(bot: Bot) -> None:
    """
    Callback when bot shuts down.
    
    Args:
        bot: Bot instance
    """
    global session
    
    logger.info("Shutting down Currency Converter Bot...")
    
    # Close HTTP session
    if session and not session.closed:
        await session.close()
        logger.info("HTTP session closed")
    
    # Clear cache
    await cache.clear()
    logger.info("Cache cleared")
    
    # Close bot
    await bot.session.close()
    logger.info("Bot session closed")
    
    logger.info("Bot shutdown complete")

@asynccontextmanager
async def lifespan():
    """
    Lifespan context manager for the bot.
    """
    # Startup
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    try:
        await on_startup(bot)
        yield bot
    finally:
        await on_shutdown(bot)

async def main():
    """
    Main function to run the bot.
    """
    try:
        # Create bot instance
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        # Create dispatcher
        dp = Dispatcher()
        dp.include_router(router)
        
        # Register startup and shutdown handlers
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Make rate_fetcher available to handlers
        dp.workflow_data["rate_fetcher"] = rate_fetcher
        
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=types.AllowedUpdates.MESSAGE,
            skip_updates=True  # Skip old updates
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())