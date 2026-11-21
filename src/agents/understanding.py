"""
BrandMind — Understanding & NLP Layer
Classifies language, dialect, intent, entities, sentiment, and hard safety triggers.
"""

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.schemas import (
    ConversationTurn,
    Dialect,
    ExtractedEntities,
    Intent,
    Language,
    Sentiment,
    UnderstandingResult,
)


class UnderstandingService:
    """Provides intent classification, entity extraction, dialect detection, and safety checks."""

    # Eastern Arabic-Indic to Western ASCII digits map
    ARABIC_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

    # Hard safety & human escalation keywords (English, Arabic, Franco)
    ESCALATION_KEYWORDS = [
        "human", "agent", "representative", "manager", "support team", "person",
        "خدمة العملاء", "بني ادم", "بني آدم", "حد يكلمني", "مش روبوت", "مسؤول", "إنسان",
        "lawyer", "legal", "sue", "police", "court", "محامي", "محكمة", "حماية المستهلك", "بلاغ",
        "rash", "allergy", "irritation", "medical", "doctor", "مستشفى", "حساسية", "التهاب",
        "fraud", "scam", "stole", "chargeback", "سرقة", "نصب", "احتيال",
    ]

    # Dialect markers for Egyptian Colloquial Arabic
    EGYPTIAN_MARKERS = [
        "عايز", "عاوز", "مش", "علشان", "عشان", "دلوقتي", "إزاي", "ازاي", "كده", "فين",
        "بكام", "مقاسه", "التيشيرت", "الهودي", "ايه", "إيه", "ياريت", "ينفع", "مفيش",
        "خالص", "طب", "حاجة", "شوية", "شغال", "أبدله", "أرجعه", "أوردر"
    ]

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Converts Arabic-Indic digits to ASCII and cleans whitespace."""
        text = text.translate(cls.ARABIC_DIGIT_MAP)
        return " ".join(text.strip().split())

    @classmethod
    def detect_language_and_dialect(cls, text: str) -> Tuple[Language, Dialect]:
        """Detects language (English vs Arabic) and distinguishes Egyptian from MSA and Franco."""
        # Check for Franco-Arabic (Latin script mixed with numbers like 2, 3, 5, 7)
        if re.search(r'\b[a-zA-Z]+[2357][a-zA-Z]*\b', text) or re.search(r'\b(3ayez|msh|feen|ezay|keda|3shan)\b', text.lower()):
            return Language.AR, Dialect.FRANCO

        # Check for Arabic script characters
        has_arabic = bool(re.search(r'[\u0600-\u06FF]', text))
        if not has_arabic:
            return Language.EN, Dialect.EN

        # Differentiate Egyptian Arabic vs MSA using marker tokens
        text_lower = text.lower()
        if any(marker in text_lower for marker in cls.EGYPTIAN_MARKERS):
            return Language.AR, Dialect.EGYPTIAN

        return Language.AR, Dialect.MSA

    @classmethod
    def check_hard_safety_triggers(cls, text: str) -> Tuple[bool, Optional[str]]:
        """Checks for explicit human escalation, dispute, medical, or legal triggers."""
        text_lower = text.lower()
        for kw in cls.ESCALATION_KEYWORDS:
            if kw in text_lower:
                return True, f"Matched critical escalation trigger: '{kw}'"
        return False, None

    @classmethod
    def resolve_relative_dates(cls, text: str, today: date) -> Tuple[Optional[date], Optional[str]]:
        """Resolves expressions like '10 days ago', 'من 10 أيام', 'yesterday' to explicit ISO dates."""
        norm = cls.normalize_text(text.lower())

        # English: 'N days ago'
        match_en = re.search(r'(\d+)\s+days?\s+ago', norm)
        if match_en:
            days = int(match_en.group(1))
            return today - timedelta(days=days), match_en.group(0)

        # Arabic: 'من N أيام' or 'من N يوم'
        match_ar = re.search(r'من\s+(\d+)\s+(?:أيام|ايام|يوم)', norm)
        if match_ar:
            days = int(match_ar.group(1))
            return today - timedelta(days=days), match_ar.group(0)

        # 'من أسبوعين' (2 weeks)
        if "من أسبوعين" in norm or "2 weeks ago" in norm:
            return today - timedelta(days=14), "2 weeks ago"

        # 'من أسبوع' (1 week)
        if "من أسبوع" in norm or "من اسبوع" in norm or "1 week ago" in norm or "a week ago" in norm:
            return today - timedelta(days=7), "1 week ago"

        # 'yesterday' / 'إمبارح'
        if "yesterday" in norm or "امبارح" in norm or "إمبارح" in norm:
            return today - timedelta(days=1), "yesterday"

        return None, None

    @classmethod
    def classify_intent_rules(cls, text: str) -> Intent:
        """Rule-based intent classifier baseline (robust offline fallback)."""
        t = text.lower()

        if any(w in t for w in ["human", "agent", "representative", "person", "whatsapp", "telephone", "phone", "كلمني حد", "خدمة العملاء", "بني ادم", "بني آدم", "حد يكلمني", "مش روبوت", "تليفون", "واتساب"]):
            return Intent.HUMAN_SUPPORT
        if any(w in t for w in ["track", "where is my order", "order status", "status of", "delivery status", "check the delivery status", "فين الأوردر", "وصل فين", "حالة الطلب", "حالة الأوردر", "شوفلي الأوردر"]):
            return Intent.ORDER_STATUS
        if any(w in t for w in ["damaged", "broken", "defect", "stain", "tear", "torn", "باظ", "مقطوع", "عيب", "غير اللي طلبته", "سوستة", "سرقة", "نصب", "حساسية", "التهاب", "قضية", "محضر"]):
            return Intent.COMPLAINT
        if any(w in t for w in ["exchange", "swap size", "تبديل", "أبدل", "ابدل", "استبدال", "تغيير مقاس"]):
            return Intent.EXCHANGE
        if any(w in t for w in ["return", "ارجاع", "إرجاع", "أرجع", "ارجع", "ترجيع", "استرجاع", "فلوسي كاش", "أرجعه", "ارجعه"]):
            return Intent.RETURNS
        if any(w in t for w in ["payment", "pay", "visa", "mastercard", "cash on delivery", "cod", "دفع", "كاش", "فيزا", "طرق الدفع"]):
            return Intent.PAYMENT
        if any(w in t for w in ["refund", "money back", "فلوس", "استرداد", "المبلغ"]):
            return Intent.REFUND
        if any(w in t for w in ["shipping", "deliver", "delivery", "dispatch", "cancel", "shipping fee", "شحن", "الشحن", "توصيل", "يوصل إمتى", "ألغي الأوردر", "إلغاء الأوردر"]):
            return Intent.SHIPPING
        if any(w in t for w in ["available", "in stock", "have in", "colors", "متاح", "متوفر", "في منه", "ألوان"]):
            return Intent.AVAILABILITY
        if any(w in t for w in ["price", "cost", "how much", "material", "cotton", "wash", "care", "fabric", "gsm", "سعر", "بكام", "خامة", "قطن", "غسيل", "مقاسات", "أوفر سايز", "فروع"]):
            return Intent.PRODUCT_INFO

        return Intent.PRODUCT_INFO

        return Intent.PRODUCT_INFO

    @classmethod
    def extract_entities(cls, text: str, today: date) -> ExtractedEntities:
        """Extracts structured entities from customer inquiry."""
        norm = cls.normalize_text(text)
        entities = ExtractedEntities()

        # 1. Order ID pattern (e.g. RLVNT-1001)
        match_order = re.search(r'\b(RLVNT-\d{4})\b', norm, re.IGNORECASE)
        if match_order:
            entities.order_id = match_order.group(1).upper()

        # 2. Sizes (S, M, L, XL, XXL, 30, 32, 34, 36)
        match_size = re.search(r'\b(xxl|xl|l|m|s|30|32|34|36)\b', norm, re.IGNORECASE)
        if match_size:
            entities.size = match_size.group(1).upper()

        # 3. Colors
        colors_en = ["black", "white", "crimson", "brown", "grey", "blue"]
        colors_ar = ["أسود", "اسود", "أبيض", "ابيض", "أحمر", "احمر", "بني", "رمادي", "كحلي", "أزرق"]
        for c in colors_en:
            if c in norm.lower():
                entities.color = c.capitalize()
                break
        if not entities.color:
            for c in colors_ar:
                if c in norm:
                    entities.color = c
                    break

        # 4. Products mentioned
        product_keywords = [
            ("San Andreas", "San Andreas Graphic Crewneck"),
            ("Michael Jackson", "Michael Jackson Tribute Crewneck"),
            ("Mbappe", "Kylian Mbappé World Cup Crewneck"),
            ("Mbappé", "Kylian Mbappé World Cup Crewneck"),
            ("مبابي", "Kylian Mbappé World Cup Crewneck"),
            ("Maradona", "Diego Maradona D.N.I. Crewneck"),
            ("مارادونا", "Diego Maradona D.N.I. Crewneck"),
            ("Dogs Gotta Eat", "DOGS GOTTA EAT Statement Crewneck"),
            ("Bellingham", "Jude Bellingham Bellingoal Crewneck"),
            ("بيلينجهام", "Jude Bellingham Bellingoal Crewneck"),
            ("Fight Club", "Fight Club Tyler Durden Crewneck"),
            ("فا fight club", "Fight Club Tyler Durden Crewneck"),
            ("Tony Montana", "Tony Montana Scarface Crewneck"),
            ("Scarface", "Tony Montana Scarface Crewneck"),
            ("Dream Big", "Dream Big Signature Star Crewneck"),
            ("Messi", "Lionel Messi 100% Cotton Signature Hoodie"),
            ("ميسي", "Lionel Messi 100% Cotton Signature Hoodie"),
            ("Neymar", "Neymar Jr Brown Gothic Hoodie"),
            ("نيمار", "Neymar Jr Brown Gothic Hoodie"),
            ("Milan", "AC Milan 1990s Lotto Retro Jersey"),
            ("ميلان", "AC Milan 1990s Lotto Retro Jersey"),
            ("Germany", "Germany 1990 Heritage Track Jacket"),
            ("ألمانيا", "Germany 1990 Heritage Track Jacket"),
            ("Ronaldo", "Cristiano Ronaldo CR7 Manchester Crewneck"),
            ("رونالدو", "Cristiano Ronaldo CR7 Manchester Crewneck"),
            ("Polo", "Polo Ralph Lauren Half-Zip Fleece Pullover"),
            ("بولو", "Polo Ralph Lauren Half-Zip Fleece Pullover"),
            ("Real Madrid", "Real Madrid Los Blancos Statement Crewneck"),
            ("ريال مدريد", "Real Madrid Los Blancos Statement Crewneck"),
            ("No Fear", "NO FEAR Gothic Lions Crewneck"),
            ("Denim", "Vintage Washed Wide-Leg Denim Jeans"),
            ("جينز", "Vintage Washed Wide-Leg Denim Jeans"),
            ("Sweatpants", "Relaxed Streetwear Sweatpants Black"),
            ("سويت بانتس", "Relaxed Streetwear Sweatpants Black"),
            ("هودي", "Hoodie"),
            ("كرو نيك", "Crewneck"),
        ]
        for kw, prod_name in product_keywords:
            if kw.lower() in norm.lower():
                entities.product = prod_name
                break

        # 5. Condition
        norm_l = norm.lower()
        words = set(re.findall(r'\b\w+\b', norm_l))

        has_unworn = (
            "unworn" in words
            or "مش ملبوس" in norm_l
            or "مش مغسول" in norm_l
            or "new" in words
            or ("tags" in words and "attached" in words)
            or "بالتيكت" in norm_l
            or "بالتكت" in norm_l
            or ("تيكت" in norm_l and "سليم" in norm_l)
            or "brand new" in norm_l
        )
        has_worn = (
            ("worn" in words and not has_unworn)
            or ("wore" in words and not has_unworn)
            or ("ملبوس" in norm_l and "مش ملبوس" not in norm_l)
            or "اتلبس" in norm_l
            or "لبسته" in norm_l
            or "خروجة" in norm_l
            or ("cut" in words and "tags" in words)
            or "شيلت التيكت" in norm_l
        )
        has_washed = (
            ("washed" in words and "unwashed" not in words)
            or ("مغسول" in norm_l and "مش مغسول" not in norm_l)
            or "اتغسل" in norm_l
            or "غسلته" in norm_l
        )

        if has_worn or has_washed:
            entities.condition = "washed or worn"
        elif has_unworn:
            entities.condition = "unworn, tags attached"

        # 6. Dates
        resolved_date, raw_text = cls.resolve_relative_dates(text, today)
        if resolved_date:
            entities.purchase_date = resolved_date
            entities.purchase_date_text = raw_text

        # 7. Reason & Category
        reasons = [
            ("too big", "too big"),
            ("too small", "too small"),
            ("واسع", "size too large"),
            ("ضيق", "size too small"),
            ("defect", "defective item"),
            ("damaged", "transit damage"),
            ("wrong item", "wrong item sent"),
            ("torn", "defective item"),
            ("broken", "defective item"),
            ("عيب", "defective item"),
            ("مكسورة", "defective item"),
            ("مقطوع", "defective item"),
            ("غير اللي طلبته", "wrong item sent"),
            ("clearance", "clearance"),
            ("final sale", "clearance"),
            ("تصفية", "clearance"),
            ("تصفيات", "clearance"),
            ("archive tee", "clearance"),
        ]
        for trigger, r_text in reasons:
            if trigger in norm.lower():
                entities.reason = r_text
                break

        return entities

    @classmethod
    def analyze(
        cls, text: str, today: date, history: Optional[List[ConversationTurn]] = None
    ) -> UnderstandingResult:
        """Processes message into structured understanding output with Pydantic validation."""
        norm_text = cls.normalize_text(text)
        lang, dialect = cls.detect_language_and_dialect(norm_text)
        requires_human, safety_reason = cls.check_hard_safety_triggers(norm_text)

        intent = cls.classify_intent_rules(norm_text)
        entities = cls.extract_entities(norm_text, today)

        # Sentiment estimation
        sentiment = Sentiment.NEUTRAL
        if any(w in norm_text.lower() for w in ["angry", "furious", "unacceptable", "scam", "زفت", "سيء جدا", "خدمة سيئة", "حرام"]):
            sentiment = Sentiment.ANGRY
        elif any(w in norm_text.lower() for w in ["slow", "waiting", "delay", "frustrated", "اتأخرتوا", "فينكم", "تأخير"]):
            sentiment = Sentiment.FRUSTRATED

        return UnderstandingResult(
            language=lang,
            dialect=dialect,
            intent=intent,
            entities=entities,
            sentiment=sentiment,
            confidence=0.95,
            requires_human=requires_human,
        )
