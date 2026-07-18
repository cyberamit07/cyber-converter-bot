"""
Telegram message handlers for the Currency Converter Bot.
Handles both commands and currency detection in messages.
"""

import time
import logging
from typing import Dict, Set
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters

from config import settings
from regex import parse_currency_message, is_valid_currency_message
from rates import RateFetcher

logger = logging.getLogger(__name__)

# Router instance
router = Router()

# Rate limiting: track user message timestamps
_user_last_message: Dict[int, float] = {}

def is_rate_limited(user_id: int) -> bool:
    """
    Check if a user is rate limited.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if rate limited, False otherwise
    """
    current_time = time.time()
    last_message = _user_last_message.get(user_id, 0)
    
    if current_time - last_message < settings.rate_limit_seconds:
        return True
    
    _user_last_message[user_id] = current_time
    return False

def format_conversion(currency: str, amount: float, conversions: Dict[str, float]) -> str:
    """
    Format conversion results with emojis.
    
    Args:
        currency: Source currency
        amount: Source amount
        conversions: Dictionary of conversions
        
    Returns:
        Formatted message string
    """
    # Currency emoji mapping
    emojis = {
        'ton': '💎',
        'usdt': '💵',
        'usd': '🇺🇸',
        'inr': '🇮🇳',
        'rub': '🇷🇺',
        'eur': '🇪🇺',
        'star': '⭐'
    }
    
    # Currency display names
    names = {
        'ton': 'TON',
        'usdt': 'USDT',
        'usd': 'USD',
        'inr': 'INR',
        'rub': 'RUB',
        'eur': 'EUR',
        'star': 'STAR'
    }
    
    lines = []
    for target_currency in ['ton', 'usdt', 'usd', 'inr', 'rub', 'eur', 'star']:
        if target_currency in conversions:
            value = conversions[target_currency]
            emoji = emojis.get(target_currency, '💱')
            name = names.get(target_currency, target_currency.upper())
            lines.append(f"{emoji} {name} : {value:.4f}")
    
    # Add footer with @cyber_amit
    lines.append("\n@cyber_amit")
    
    return "\n".join(lines)

@router.message(Command("start"))
async def start_command(message: Message) -> None:
    """
    Handle /start command.
    """
    welcome_text = (
        "🤖 *Welcome to Currency Converter Bot!*\n\n"
        "I automatically detect currency messages and convert them.\n\n"
        "*How to use:*\n"
        "Just send any supported currency and amount:\n"
        "• `1t` or `1 ton`\n"
        "• `100 usdt`\n"
        "• `500 inr`\n"
        "• `10 stars`\n\n"
        "*Commands:*\n"
        "/start - Show this message\n"
        "/help - Show help\n"
        "/rate - Show current exchange rates\n"
        "/ping - Check bot latency\n\n"
        "Made with ❤️ by @cyber_amit"
    )
    
    await message.reply(welcome_text, parse_mode="Markdown")

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """
    Handle /help command.
    """
    help_text = (
        "📚 *Help & Documentation*\n\n"
        "*Supported Currencies:*\n"
        "• TON (Toncoin)\n"
        "• USDT (Tether)\n"
        "• USD (US Dollar)\n"
        "• INR (Indian Rupee)\n"
        "• RUB (Russian Ruble)\n"
        "• EUR (Euro)\n"
        "• STAR (Telegram Stars)\n\n"
        "*Supported Formats:*\n"
        "• `1t` or `1 ton`\n"
        "• `2.5T`\n"
        "• `100 usdt`\n"
        "• `500INR`\n"
        "• `10 stars`\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - This help message\n"
        "/rate - Current exchange rates\n"
        "/ping - Bot latency\n\n"
        "@cyber_amit"
    )
    
    await message.reply(help_text, parse_mode="Markdown")

@router.message(Command("rate"))
async def rate_command(message: Message, rate_fetcher: RateFetcher) -> None:
    """
    Handle /rate command.
    """
    try:
        rates = await rate_fetcher.get_rates(force_refresh=True)
        if not rates:
            await message.reply(
                "⚠️ Unable to fetch exchange rates.\n"
                "Please try again in a few seconds."
            )
            return
        
        # Format rates
        lines = ["📊 *Current Exchange Rates*", ""]
        lines.append(f"💎 TON : ${rates.get('ton', 0):.4f}")
        lines.append(f"💵 USDT : ${rates.get('usdt', 0):.4f}")
        lines.append(f"🇺🇸 USD : ${rates.get('usd', 0):.4f}")
        lines.append(f"🇮🇳 INR : ₹{rates.get('inr', 0):.2f}")
        lines.append(f"🇷🇺 RUB : ₽{rates.get('rub', 0):.2f}")
        lines.append(f"🇪🇺 EUR : €{rates.get('eur', 0):.2f}")
        lines.append(f"⭐ STAR : ${rates.get('star', 0):.4f}")
        lines.append("\n@cyber_amit")
        
        await message.reply("\n".join(lines), parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in /rate command: {e}")
        await message.reply(
            "⚠️ Unable to fetch exchange rates.\n"
            "Please try again in a few seconds."
        )

@router.message(Command("ping"))
async def ping_command(message: Message) -> None:
    """
    Handle /ping command with latency measurement.
    """
    start_time = time.time()
    
    # Send typing action to measure real response time
    await message.answer_chat_action("typing")
    
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to milliseconds
    
    await message.reply(
        f"🏓 *Pong!*\n\n"
        f"⏱️ *Latency:* {latency:.0f}ms\n"
        f"🟢 *Status:* Online\n"
        f"🤖 *Bot:* Active\n\n"
        "@cyber_amit",
        parse_mode="Markdown"
    )

@router.message()
async def handle_currency_message(message: Message, rate_fetcher: RateFetcher) -> None:
    """
    Handle currency detection in messages.
    """
    # Ignore messages without text
    if not message.text:
        return
    
    # Only process in groups/channels
    if message.chat.type not in ["group", "supergroup", "channel"]:
        return
    
    # Rate limiting per user
    if is_rate_limited(message.from_user.id):
        logger.debug(f"Rate limited user: {message.from_user.id}")
        return
    
    # Parse the message
    parsed = parse_currency_message(message.text.strip())
    if not parsed:
        return
    
    currency, amount = parsed
    logger.info(f"Detected currency: {currency}, amount: {amount} from user: {message.from_user.id}")
    
    try:
        # Get conversion rates
        conversions = await rate_fetcher.get_conversion(currency, amount)
        if not conversions:
            await message.reply(
                "⚠️ Unable to fetch exchange rates.\n"
                "Please try again in a few seconds.",
                reply_parameters=ReplyParameters(message_id=message.message_id)
            )
            return
        
        # Format and send response
        response = format_conversion(currency, amount, conversions)
        await message.reply(
            response,
            reply_parameters=ReplyParameters(message_id=message.message_id)
        )
        
    except Exception as e:
        logger.error(f"Error processing currency message: {e}")
        await message.reply(
            "⚠️ Unable to process your request.\n"
            "Please try again in a few seconds.",
            reply_parameters=ReplyParameters(message_id=message.message_id)
        )