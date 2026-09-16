import re

_NOISE_PATTERN = re.compile(r"[^a-zа-яіїєґ0-9\s]", re.IGNORECASE)
_DIGITS_PATTERN = re.compile(r"\d+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def build_merchant_key(description: str) -> str:
    text = description.strip().lower()
    text = _NOISE_PATTERN.sub(" ", text)
    text = _DIGITS_PATTERN.sub("", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text
