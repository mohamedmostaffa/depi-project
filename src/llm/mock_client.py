"""
BrandMind — Offline Deterministic LLM Mock Client
Generates grounded, brand-consistent replies without requiring live API network requests.
"""

from typing import Any, Dict, Optional
from src.schemas import Decision, Dialect, Intent, Language


class MockLLMClient:
    """Offline generator implementing grounded brand personality responses."""

    def __init__(self, brand_id: str = "rlvnt"):
        self.brand_id = brand_id

    def generate_response(
        self,
        intent: Intent,
        language: Language,
        dialect: Dialect,
        context_text: str,
        tool_results: Optional[str] = None,
        decision: Optional[Dict[str, Any]] = None,
        customer_message: str = "",
        is_first_turn: bool = False,
    ) -> str:
        is_eg = dialect == Dialect.EGYPTIAN or language == Language.AR

        # 1. Greeting prefix if initial turn
        greeting = ""
        if is_first_turn:
            greeting = (
                "أهلاً بيك في RLVNT! ⚡ أنا المساعد الذكي الخاص بالبراند. "
                if is_eg
                else "Hey! Welcome to RLVNT. I'm your AI customer assistant. "
            )

        # 2. Return / Exchange Policy Decision
        if decision:
            dec = decision.get("decision")
            reason_text = decision.get("reason_text", "")
            if dec == "eligible":
                if is_eg:
                    return f"{greeting}طلبك مؤهل للاستبدال/الاسترجاع! {reason_text} تحب نجهزلك خطوات استلام المندوب؟"
                else:
                    return f"{greeting}Great news! Your request is eligible. {reason_text} Would you like to proceed with courier pickup?"
            elif dec == "not_eligible":
                if is_eg:
                    return f"{greeting}للأسف القطعة غير مؤهلة للاسترجاع. {reason_text} لو عندك استفسار تاني بخصوص المقاسات أو الكولكشن أنا معاك."
                else:
                    return f"{greeting}Unfortunately, this item is not eligible for return. {reason_text} Let us know if you need help exploring other pieces."
            else:
                missing = decision.get("missing_fields", [])
                if is_eg:
                    return f"{greeting}محتاجين شوية تفاصيل إضافية عشان نساعدك ({', '.join(missing)}). ياريت توضحلنا حالة القطعة وتاريخ الاستلام."
                else:
                    return f"{greeting}We need a few more details to check eligibility ({', '.join(missing)}). Could you provide your order number or delivery date?"

        # 3. Order Status
        if intent == Intent.ORDER_STATUS and tool_results:
            if is_eg:
                return f"{greeting}حالة الأوردر بتاعك حالياً: {tool_results}. المندوب هيتواصل معاك للتسليم أول ما يوصل محافظتك!"
            else:
                return f"{greeting}Here is your order update: {tool_results}. You will receive courier delivery updates via SMS/WhatsApp."

        # 4. Catalog & Products
        if intent in [Intent.PRODUCT_INFO, Intent.AVAILABILITY]:
            if "messi" in customer_message.lower() or "ميسي" in customer_message:
                if is_eg:
                    return f"{greeting}هودي ميسي مصنوع من قطن 100% ثقيل وفاخر، بكتابة جولد LIONEL MESSI وقصة أوفرسايز مريحة جداً. سعره 1650 جنيه ومتاح بمقاسات من S لـ XXL."
                else:
                    return f"{greeting}The Lionel Messi Signature Hoodie is crafted from 100% heavyweight cotton with gold metallic chest print and relaxed streetwear fit. Price is 1,650 EGP, available in S through XXL."
            elif "san andreas" in customer_message.lower() or "سان أندرياس" in customer_message:
                if is_eg:
                    return f"{greeting}كرو-نيك سان أندرياس من كولكشن الشتا باللون الأسود بجرافيك CJ الشهير. سعره 1250 جنيه وخامته قطن ثقيل ومريح."
                else:
                    return f"{greeting}The San Andreas Graphic Crewneck is a heavyweight black top featuring the iconic CJ graphic. Price is 1,250 EGP with relaxed streetwear proportions."
            else:
                if is_eg:
                    return f"{greeting}جميع قطع RLVNT مصممة بقصات أوفرسايز مريحة وخامات قطنية ثقيلة للشتا. تقدر تشوف جدول المقاسات لتحديد أنسب مقاس ليك."
                else:
                    return f"{greeting}All RLVNT pieces feature signature heavyweight cotton and relaxed streetwear silhouettes. Check our size chart for the perfect fit!"

        # 5. Shipping Policy
        if intent == Intent.SHIPPING:
            if is_eg:
                return f"{greeting}الأوردرات بتتجهز وتتشحن خلال 1-2 يوم عمل في تغليف آمن لحماية الطباعة. مدة التوصيل بتعتمد على محافظتك وبيوصلك كود التتبع فور خروج الشحنة."
            else:
                return f"{greeting}Orders are packed and dispatched within 1-2 business days in protective garment packaging. Delivery timeframe depends on your governorate."

        # 6. Returns Policy General Inquiry
        if intent == Intent.RETURNS:
            if is_eg:
                return f"{greeting}سياسة الاسترجاع والاستبدال خلال 14 يوم من تاريخ الاستلام، بشرط تكون القطعة مش ملبوسة ومش مغسولة وبالتيكت الأصلي. مصاريف شحن الاستبدال على العميل، والعيوب الصناعية بتتحملها RLVNT بنسبة 100%."
            else:
                return f"{greeting}Returns and exchanges are accepted within 14 days of delivery for unworn garments with original tags attached. Exchange shipping is covered by the customer, while defective items are 100% covered by RLVNT."

        # Default fallback
        if is_eg:
            return f"{greeting}شكراً لتواصلك مع RLVNT! إزاي أقدر أساعدك النهاردة في اختيار المقاس أو متابعة أوردرك؟"
        else:
            return f"{greeting}Thank you for contacting RLVNT! How can I assist you with your fit or order today?"
