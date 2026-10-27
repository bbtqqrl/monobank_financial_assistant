import re
import unicodedata
from difflib import SequenceMatcher
from enum import StrEnum

from app.schemas.place import PlaceResponse

NAME_MATCH_RATIO = 0.8
MIN_WORD_LENGTH = 3

CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z",
    "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ь": "", "ю": "iu", "я": "ia", "ы": "y", "э": "e", "ё": "e", "ъ": "",
}
SPELLING_VARIANTS = [
    ("shch", "sh"), ("ph", "f"), ("kh", "h"), ("ck", "k"), ("c", "k"), ("q", "k"), ("w", "v"), ("x", "ks"),
    ("z", "s"), ("y", "i"), ("j", "i"),
]
STOP_WORDS = {
    "tov", "fop", "pp", "llc", "ltd", "inc", "sp", "zoo", "the", "and", "magazin", "market", "shop", "store",
    "kafe", "cafe", "restoran", "restaurant", "bar", "apteka", "pharmacy", "kaviarnia", "coffee", "ukraina",
}


class PlaceMethod(StrEnum):
    LINK = "link"
    SINGLE = "single"
    NAME_MATCH = "name_match"
    NEAREST = "nearest"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"


CONFIDENT_PLACE_METHODS = {PlaceMethod.LINK, PlaceMethod.SINGLE, PlaceMethod.NAME_MATCH}


def to_latin(text: str) -> str:
    latin = "".join(CYRILLIC_TO_LATIN.get(char, char) for char in text.lower())
    latin = "".join(char for char in unicodedata.normalize("NFKD", latin) if not unicodedata.combining(char))
    for spelling, variant in SPELLING_VARIANTS:
        latin = latin.replace(spelling, variant)
    return re.sub(r"(.)\1+", r"\1", latin)


_STOP_WORDS = {to_latin(word) for word in STOP_WORDS}


def name_words(name: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", to_latin(name.replace("'", "").replace("’", "")))
    return {word for word in words if len(word) >= MIN_WORD_LENGTH and word not in _STOP_WORDS}


def names_match(merchant: str, place_name: str) -> bool:
    place_words = name_words(place_name)
    return any(
        SequenceMatcher(None, word, other).ratio() >= NAME_MATCH_RATIO
        for word in name_words(merchant)
        for other in place_words
    )


def choose_place(candidates: list[PlaceResponse], merchant: str) -> tuple[PlaceResponse | None, PlaceMethod]:
    if not candidates:
        return None, PlaceMethod.NOT_FOUND
    if len(candidates) == 1:
        return candidates[0], PlaceMethod.SINGLE
    matched = [candidate for candidate in candidates if names_match(merchant, candidate.name)]
    if len(matched) == 1:
        return matched[0], PlaceMethod.NAME_MATCH
    return min(candidates, key=lambda candidate: candidate.distance_m), PlaceMethod.NEAREST
