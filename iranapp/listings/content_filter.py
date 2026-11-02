import re
import unicodedata


_LEET = str.maketrans(
    {
        "@": "a",
        "$": "s",
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
    }
)

_TERMS = {
    "profanity": (
        "fuck",
        "fck",
        "fuk",
        "shit",
        "bitch",
        "asshole",
        "bastard",
        "dick",
        "pussy",
        "cunt",
        "motherfucker",
    ),
    "harassment": (
        "kill yourself",
        "kys",
        "go die",
        "i will kill you",
    ),
    "hate": (
        "nigger",
        "nigga",
        "faggot",
        "kike",
        "spic",
        "chink",
        "wetback",
    ),
    "spam": (
        "click here",
        "free money",
        "crypto giveaway",
        "work from home",
        "buy followers",
    ),
    "prohibited": (
        "buy cocaine",
        "sell cocaine",
        "buy weed",
        "fake id",
        "stolen cards",
        "card dump",
    ),
}


def _term_pattern(term):
    parts = []
    for word in term.split():
        letters = r"[^a-z0-9]{0,2}".join(re.escape(character) for character in word)
        parts.append(letters)
    body = r"[^a-z0-9]{1,3}".join(parts)
    return re.compile(
        rf"(?<![a-z0-9]){body}(?:ing|ers|er|ed|es|s)?(?![a-z0-9])"
    )


_PATTERNS = tuple(
    (category, _term_pattern(term))
    for category, terms in _TERMS.items()
    for term in terms
)
_LINK = re.compile(r"https?://|www\.", re.IGNORECASE)


def _normalize(text):
    normalized = unicodedata.normalize("NFKC", text or "").casefold().translate(_LEET)
    return re.sub(r"(.)\1{2,}", r"\1", normalized)


def find_review_violation(text):
    """Return a moderation category when review text must not be public."""
    if len(_LINK.findall(text or "")) >= 2:
        return "spam"
    normalized = _normalize(text)
    for category, pattern in _PATTERNS:
        if pattern.search(normalized):
            return category
    return None
