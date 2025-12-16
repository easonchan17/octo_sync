import re
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional

def wildcard_to_regex(pattern: str) -> str:
    pattern = re.escape(pattern)

    pattern = pattern.replace(r'\*', '.*')
    pattern = pattern.replace(r'\?', '.')

    if not pattern.startswith('^'):
        pattern = '^' + pattern
    if not pattern.endswith('$'):
        pattern = pattern + '$'

    return pattern

def wildcard_to_compiled_regex(pattern: str) -> re.Pattern:
    regex_pattern = wildcard_to_regex(pattern)

    try:
        compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern {pattern}: {str(e)}")

    return compiled_regex

def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False

    try:
        parsed_url = urlparse(url)
        return bool(parsed_url.scheme and parsed_url.netloc)
    except Exception:
        return False

def normalize_url(url: str) -> str:
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

def clean_nul(value: str) -> str:
    if not value:
        return None

    return value.replace("\x00", "")

def parse_utc_time(utc_time_str: Optional[str]) -> Optional[datetime]:
    if not utc_time_str:
        return None
    try:
        return datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
    except ValueError:
        return None
