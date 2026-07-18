import re
from typing import Optional, Tuple

CURRENCY_PATTERNS = {
    'ton': re.compile(r'^(\d+\.?\d*)\s*(?:t|ton|TON)$', re.IGNORECASE),
    'usdt': re.compile(r'^(\d+\.?\d*)\s*(?:usdt|USDT)$', re.IGNORECASE),
    'usd': re.compile(r'^(\d+\.?\d*)\s*(?:usd|USD)$', re.IGNORECASE),
    'inr': re.compile(r'^(\d+\.?\d*)\s*(?:inr|INR)$', re.IGNORECASE),
    'rub': re.compile(r'^(\d+\.?\d*)\s*(?:rub|RUB)$', re.IGNORECASE),
    'eur': re.compile(r'^(\d+\.?\d*)\s*(?:eur|EUR)$', re.IGNORECASE),
    'star': re.compile(r'^(\d+\.?\d*)\s*(?:star|stars|STAR|STARS)$', re.IGNORECASE),
}

TON_SHORT = re.compile(r'^(\d+\.?\d*)\s*t$', re.IGNORECASE)

def parse_currency_message(text: str) -> Optional[Tuple[str, float]]:
    if not text:
        return None
    text = text.strip()
    for currency, pattern in CURRENCY_PATTERNS.items():
        match = pattern.match(text)
        if match:
            return currency, float(match.group(1))
    match = TON_SHORT.match(text)
    if match:
        return 'ton', float(match.group(1))
    return None

def is_valid_currency_message(text: str) -> bool:
    return parse_currency_message(text) is not None