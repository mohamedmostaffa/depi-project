"""
BrandMind — Small-talk detector.

A message that is ONLY a greeting / thanks / goodbye ("السلام عليكم", "hi", "شكرا", "bye")
is not a question about the brand. It must not go through retrieval (which always returns the
4 nearest brand chunks, relevant or not) and must not be classified as product_info.
Anything that contains more than greeting words ("hi, where is my order?") is NOT small talk.
"""
import re

_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")  # tashkeel + tatweel
_LETTER_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})


def _norm(text: str) -> str:
    t = _DIACRITICS.sub("", (text or "").lower()).translate(_LETTER_MAP)
    t = re.sub(r"[^\w\s]", " ", t)          # punctuation and emojis
    t = re.sub(r"(.)\1{2,}", r"\1", t)      # "hiiii" -> "hi", "هاااي" -> "هاي"
    return " ".join(t.split())


_GREETING_PHRASES = [
    # Arabic (normalised: no diacritics, alef/ya/ta-marbuta unified)
    "السلام عليكم", "سلام عليكم", "وعليكم السلام", "و عليكم السلام", "ورحمه الله", "وبركاته", "سلام",
    "اهلا وسهلا", "اهلا", "مرحبا", "مرحبتين", "هاي", "هلو", "هلا", "صباح الخير", "صباح النور",
    "مساء الخير", "مساء النور", "ازيك", "ازيكم", "عامل ايه", "عاملين ايه", "ايه الاخبار",
    "شكرا جزيلا", "شكرا", "متشكر", "مشكور", "تسلم", "تسلموا", "ميرسي",
    "مع السلامه", "في امان الله", "باي",
    # English / Franco
    "good morning", "good afternoon", "good evening", "how are you", "what s up", "whats up",
    "thank you", "thanks", "thx", "goodbye", "bye", "see you", "hello", "hiya", "hey", "hi", "yo",
    "assalamu alaikum", "assalamualaikum", "salam alaykum", "wa alaykum assalam", "salam", "ahlan", "marhaba",
]
_FILLERS = {
    "يا", "باشا", "بيك", "بيكم", "ليك", "ليكم", "لك", "جدا", "كتير", "اوي", "فندم", "ريس", "معلم", "برنس",
    "كلكم", "بخير", "الحمد", "لله", "كويس", "انت", "انتو", "rlvnt",
    "there", "team", "everyone", "all", "so", "much", "very", "a", "lot", "you", "your", "the", "for",
    "help", "bro", "man", "dude", "guys",
}

_PATTERN = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(_norm(p)) for p in sorted(_GREETING_PHRASES, key=len, reverse=True)) + r")(?!\w)"
)


def is_small_talk(message: str) -> bool:
    """True only if the whole message consists of greeting / thanks / goodbye words."""
    t = _norm(message)
    if not t or len(t.split()) > 12 or not _PATTERN.search(t):
        return False
    leftover = _PATTERN.sub(" ", t).split()
    return all(tok in _FILLERS for tok in leftover)
