"""
Regular expression patterns for parsing currency messages.
"""

import re
from typing import Optional, Tuple

# Currency patterns with various formats
CURRENCY_PATTERNS = {
    'ton': re.compile(r'^(\d+\.?\d*)\s*(?:t|ton|TON)$', re.IGNORECASE),
    'usdt': re.compile(r'^(\d+\.?\d*)\s*(?:usdt|USDT)$', re.IGNORECASE),
    'usd': re.compile(r'^(\d+\.?\d*)\s*(?:usd|USD)$', re.IGNORECASE),
    'inr': re.compile(r'^(\d+\.?\d*)\s*(?:inr|INR)$', re.IGNORECASE),
    'rub': re.compile(r'^(\d+\.?\d*)\s*(?:rub|RUB)$', re.IGNORECASE),
    'eur': re.compile(r'^(\d+\.?\d*)\s*(?:eur|EUR)$', re.IGNORECASE),
    'star': re.compile(r'^(\d+\.?\d*)\s*(?:star|stars|STAR)$', re.IGNORECASE),
}

# Special pattern for standalone TON (e.g., "1t", "2.5t")
TON_SHORT_PATTERN = re.compile(r'^(\d+\.?\d*)\s*t$', re.IGNORECASE)

def parse_currency_message(text: str) -> Optional[Tuple[str, float]]:
    """
    Parse a message to extract currency and amount.
    
    Args:
        text: Message text to parse
        
    Returns:
        Tuple of (currency, amount) or None if no match
    """
    if not text:
        return None
    
    # Clean the text - remove extra spaces and trim
    text = text.strip()
    
    # Try to match against each currency pattern
    for currency, pattern in CURRENCY_PATTERNS.items():
        match = pattern.match(text)
        if match:
            amount = float(match.group(1))
            return currency, amount
    
    # Check for standalone TON (e.g., "1t", "2.5t")
    match = TON_SHORT_PATTERN.match(text)
    if match:
        amount = float(match.group(1))
        return 'ton', amount
    
    return None

def is_valid_currency_message(text: str) -> bool:
    """
    Check if a message contains valid currency format.
    
    Args:
        text: Message text to validate
        
    Returns:
        True if valid currency format, False otherwise
    """
    return parse_currency_message(text) is not None