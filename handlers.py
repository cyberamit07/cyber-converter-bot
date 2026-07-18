import time
import logging
from typing import Dict

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters

from config import settings
from regex import parse_currency_message
from rates import RateFetcher

logger = logging.getLogger(__name__)

router = Router()
_user_last_message: Dict[int, float] = {}

def is_rate_limited(user_id: int) -> bool:
    current = time.time()
    last = _user_last_message.get(user_id, 0)
    if current - last < settings.rate_limit_seconds:
        return True
    _user_last_message[user_id] = current
    return False

def format_conversion(currency: str, amount: float, conversions: Dict[str, float]) -> str:
    emojis = {
        'ton': '💎', 'usdt': '💵', 'usd': '🇺🇸',
        'inr': '🇮🇳', 'rub': '🇷🇺', 'eur': '🇪🇺', 'star': '⭐'
    }
    names = {
        'ton': 'TON', 'usdt': 'USDT', 'usd': 'USD',
        'inr': 'INR', 'rub': 'RUB', 'eur': 'EUR', 'star': 'STAR'
    }
    
    lines = []
    for target in ['ton', 'usdt', 'usd', 'inr', 'rub', 'eur', 'star']:
        if target in conversions:
            value = conversions[target]
            lines.append(f"{emojis.get(target, '💱')} {names.get(target, target.upper())} : {value:.4f}")
    
    lines.append("\n@cyber_amit")
    return "\n".join(lines)

@router.message(Command("start"))
async def start_command(message: Message) -> None:
    text = (
        "🤖 *Welcome to Currency Converter Bot!*\n\n"
        "I automatically detect and convert currency messages.\n\n"
        "*How to use:*\n"
        "Send any supported currency:\n"
        "• `1t` or `1 ton`\n"
        "• `100 usdt`\n"
        "• `500 inr`\n"
        "• `10 stars`\n\n"
        "*Commands:*\n"
        "/start - Welcome\n"
        "/help - Help\n"
        "/rate - Exchange rates\n"
        "/ping - Latency\n\n"
        "@cyber_amit"
    )
    await message.reply(text, parse_mode="Markdown")

@router.message(Command("help"))
async def help_command(message: Message) -> None:
    text = (
        "📚 *Help & Documentation*\n\n"
        "*Supported Currencies:*\n"
        "• TON (Toncoin)\n"
        "• USDT (Tether)\n"
        "• USD (US Dollar)\n"
        "• INR (Indian Rupee)\n"
        "• RUB (Russian Ruble)\n"
        "• EUR (Euro)\n"
        "• STAR (Telegram Stars)\n\n"
        "*Formats:*\n"
        "• `1t` or `1 ton`\n"
        "• `2.5T`\n"
        "• `100 usdt`\n"
        "• `500INR`\n"
        "• `10 stars`\n\n"
        "@cyber_amit"
    )
    await message.reply(text, parse_mode="Markdown")

@router.message(Command("rate"))
async def rate_command(message: Message, rate_fetcher: RateFetcher) -> None:
    try:
        rates = await rate_fetcher.get_rates(force_refresh=True)
        if not rates:
            await message.reply("⚠️ Unable to fetch exchange rates. Please try again.")
            return
        
        text = (
            "📊 *Current Exchange Rates*\n\n"
            f"💎 TON : ${rates.get('ton', 0):.4f}\n"
            f"💵 USDT : ${rates.get('usdt', 0):.4f}\n"
            f"🇺🇸 USD : ${rates.get('usd', 0):.4f}\n"
            f"🇮🇳 INR : ₹{rates.get('inr', 0):.2f}\n"
            f"🇷🇺 RUB : ₽{rates.get('rub', 0):.2f}\n"
            f"🇪🇺 EUR : €{rates.get('eur', 0):.2f}\n"
            f"⭐ STAR : ${rates.get('star', 0):.4f}\n\n"
            "@cyber_amit"
        )
        await message.reply(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Rate command error: {e}")
        await message.reply("⚠️ Unable to fetch exchange rates. Please try again.")

@router.message(Command("ping"))
async def ping_command(message: Message) -> None:
    start = time.time()
    await message.answer_chat_action("typing")
    latency = (time.time() - start) * 1000
    await message.reply(
        f"🏓 *Pong!*\n\n"
        f"⏱️ *Latency:* {latency:.0f}ms\n"
        f"🟢 *Status:* Online\n\n"
        "@cyber_amit",
        parse_mode="Markdown"
    )

@router.message()
async def handle_currency(message: Message, rate_fetcher: RateFetcher) -> None:
    if not message.text:
        return
    
    if message.chat.type not in ["group", "supergroup"]:
        return
    
    if is_rate_limited(message.from_user.id):
        return
    
    parsed = parse_currency_message(message.text.strip())
    if not parsed:
        return
    
    currency, amount = parsed
    logger.info(f"💰 Currency detected: {currency} {amount} from {message.from_user.id}")
    
    try:
        conversions = await rate_fetcher.get_conversion(currency, amount)
        if not conversions:
            await message.reply(
                "⚠️ Unable to fetch exchange rates. Please try again.",
                reply_parameters=ReplyParameters(message_id=message.message_id)
            )
            return
        
        response = format_conversion(currency, amount, conversions)
        await message.reply(
            response,
            reply_parameters=ReplyParameters(message_id=message.message_id)
        )
    except Exception as e:
        logger.error(f"Currency processing error: {e}")
        await message.reply(
            "⚠️ Unable to process your request. Please try again.",
            reply_parameters=ReplyParameters(message_id=message.message_id)
        )