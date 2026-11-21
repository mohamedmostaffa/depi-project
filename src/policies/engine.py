"""
BrandMind — Deterministic Policy Engine (Pure Python)
Enforces 100% deterministic, side-effect-free return and exchange eligibility decisions.
"""

import re
from datetime import date
from typing import Any, Dict, List, Optional, Set

from src.schemas import Decision, EligibilityResult


class PolicyEngine:
    """Pure, side-effect-free business rules engine for e-commerce return & exchange eligibility."""

    @staticmethod
    def evaluate(
        facts: Dict[str, Any],
        policy: Dict[str, Any],
        today: date,
        catalog_products: Optional[Dict[str, Dict[str, Any]]] = None,
        mock_orders: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> EligibilityResult:
        """
        Evaluates eligibility deterministically in a fixed, auditable rule order.
        
        Args:
            facts: Extracted customer facts (product_id, order_id, purchase_date, condition, reason, is_defective).
            policy: Brand policy parameters (allowed_days, non_returnable_categories, etc.).
            today: Injected current date (for deterministic testing).
            catalog_products: Optional dictionary of product_id -> product details.
            mock_orders: Optional dictionary of order_id -> order details.
        """
        rule_trace: List[str] = []
        request_type = str(facts.get("request_type", "return")).lower()
        order_id = facts.get("order_id")
        product_id = facts.get("product_id")
        condition = facts.get("condition")
        reason = str(facts.get("reason", "") or "")
        is_defective = bool(facts.get("is_defective", False)) or any(
            w in reason.lower() for w in ["defect", "damaged", "wrong item", "faulty", "عيب"]
        )

        # Step 1: Check Required Identifiers and Information
        missing_fields: List[str] = []
        if not product_id and not order_id:
            missing_fields.append("product_or_order_id")
        if not condition and not is_defective:
            missing_fields.append("item_condition")

        # Resolve order and product details if store is supplied
        order_record = None
        if order_id and mock_orders:
            order_record = mock_orders.get(order_id)
            if not order_record:
                rule_trace.append(f"Rule 1 [Order Lookup]: Order '{order_id}' not found in records")
                return EligibilityResult(
                    decision=Decision.NEEDS_INFO,
                    reason_code="ORDER_NOT_FOUND",
                    reason_text=f"We could not locate order '{order_id}'. Please verify your order number.",
                    missing_fields=["valid_order_id"],
                    rule_trace=rule_trace,
                )
            # Verify brand matching
            if order_record.get("brand_id") != policy.get("brand_id"):
                rule_trace.append(f"Rule 1 [Brand Check]: Order brand '{order_record.get('brand_id')}' != policy brand '{policy.get('brand_id')}'")
                return EligibilityResult(
                    decision=Decision.NOT_ELIGIBLE,
                    reason_code="WRONG_BRAND",
                    reason_text="This order does not belong to RLVNT.",
                    rule_trace=rule_trace,
                )
            if not product_id:
                product_id = order_record.get("product_id")
            rule_trace.append(f"Rule 1 [Order Lookup]: Verified order '{order_id}'")

        if missing_fields:
            rule_trace.append(f"Rule 1 [Completeness]: Missing required facts: {missing_fields}")
            return EligibilityResult(
                decision=Decision.NEEDS_INFO,
                reason_code="INCOMPLETE_FACTS",
                reason_text="We need additional details to process your request.",
                missing_fields=missing_fields,
                rule_trace=rule_trace,
            )

        # Step 2: Category Exclusions Check
        category = facts.get("category")
        if not category and product_id and catalog_products:
            prod_info = catalog_products.get(product_id)
            if prod_info:
                category = prod_info.get("category")

        non_returnable_cats = policy.get("non_returnable_categories", [])
        if isinstance(non_returnable_cats, str):
            non_returnable_cats = [c.strip() for c in non_returnable_cats.split(";") if c.strip()]

        if category and any(cat.lower() in category.lower() for cat in non_returnable_cats):
            rule_trace.append(f"Rule 2 [Exclusion]: Category '{category}' is non-returnable")
            return EligibilityResult(
                decision=Decision.NOT_ELIGIBLE,
                reason_code="EXCLUDED_CATEGORY",
                reason_text=f"Items in the '{category}' category are final sale and not eligible for return or exchange.",
                rule_trace=rule_trace,
            )
        rule_trace.append("Rule 2 [Exclusion]: Item category is eligible")

        # Step 3: Defective or Wrong Item Priority Override
        if is_defective:
            rule_trace.append("Rule 3 [Exception]: Defective or wrong item exception applies (100% brand covered)")
            return EligibilityResult(
                decision=Decision.ELIGIBLE,
                reason_code="DEFECTIVE_OR_WRONG_ITEM",
                reason_text=(
                    "Eligible for priority replacement or full refund under RLVNT craftsmanship guarantee. "
                    "All shipping costs are 100% covered by RLVNT upon photo verification."
                ),
                rule_trace=rule_trace,
            )

        # Step 4: Date & Time Boundary Evaluation
        purchase_date = facts.get("purchase_date")
        if not purchase_date and order_record:
            delivery_date_str = order_record.get("delivery_date")
            order_date_str = order_record.get("order_date")
            effective_date_str = delivery_date_str or order_date_str
            if effective_date_str:
                if isinstance(effective_date_str, date):
                    purchase_date = effective_date_str
                else:
                    purchase_date = date.fromisoformat(effective_date_str)

        if not purchase_date:
            rule_trace.append("Rule 4 [Date]: Missing purchase or delivery date")
            return EligibilityResult(
                decision=Decision.NEEDS_INFO,
                reason_code="MISSING_PURCHASE_DATE",
                reason_text="Please provide the delivery date or order date of your item.",
                missing_fields=["purchase_date"],
                rule_trace=rule_trace,
            )

        # Future date guard
        if purchase_date > today:
            rule_trace.append(f"Rule 4 [Date]: Purchase date {purchase_date} is in the future relative to {today}")
            return EligibilityResult(
                decision=Decision.NOT_ELIGIBLE,
                reason_code="INVALID_PURCHASE_DATE",
                reason_text="The provided purchase date is in the future.",
                rule_trace=rule_trace,
            )

        allowed_days = int(policy.get("allowed_days", 14))
        elapsed_days = (today - purchase_date).days

        if elapsed_days > allowed_days:
            rule_trace.append(f"Rule 4 [Date]: Elapsed {elapsed_days} days exceeds allowed {allowed_days} days")
            return EligibilityResult(
                decision=Decision.NOT_ELIGIBLE,
                reason_code="OUTSIDE_WINDOW",
                reason_text=(
                    f"Return window exceeded. Your order was delivered {elapsed_days} days ago, "
                    f"which is outside our {allowed_days}-day policy window."
                ),
                rule_trace=rule_trace,
            )
        rule_trace.append(f"Rule 4 [Date]: Elapsed {elapsed_days} days is within {allowed_days} days window")

        # Step 5: Garment Condition Evaluation
        if condition:
            cond_str = condition.lower()
            tokens = set(re.findall(r'\b\w+\b', cond_str))

            # Detect positive condition phrases
            has_unworn = "unworn" in tokens or "مش ملبوس" in cond_str
            has_unwashed = "unwashed" in tokens or "مش مغسول" in cond_str
            has_tags = "tags" in tokens or "تيكت" in cond_str or "tag" in tokens

            # Detect negative condition indicators
            # "worn" is bad ONLY if not "unworn"
            is_worn = ("worn" in tokens and not has_unworn) or ("used" in tokens) or ("ملبوس" in cond_str and not has_unworn)
            is_washed = ("washed" in tokens and not has_unwashed) or ("مغسول" in cond_str and not has_unwashed)
            is_stained = "stained" in tokens or "stain" in tokens or "بقع" in cond_str
            has_perfume = "perfume" in tokens or "برفان" in cond_str or "عطر" in cond_str
            is_altered = "altered" in tokens or "معدل" in cond_str
            missing_tags = "missing tag" in cond_str or "no tag" in cond_str or "من غير تيكت" in cond_str

            if is_worn or is_washed or is_stained or has_perfume or is_altered or missing_tags:
                rule_trace.append(f"Rule 5 [Condition]: Condition '{condition}' violates return policy standards")
                return EligibilityResult(
                    decision=Decision.NOT_ELIGIBLE,
                    reason_code="BAD_CONDITION",
                    reason_text=(
                        "Items must be unworn, unwashed, free of perfume or stains, and returned in original packaging with all tags attached."
                    ),
                    rule_trace=rule_trace,
                )
        rule_trace.append("Rule 5 [Condition]: Item condition meets return standards")

        # Step 6: Final Outcome Assembly (Eligible)
        if request_type == "exchange":
            return EligibilityResult(
                decision=Decision.ELIGIBLE,
                reason_code="ELIGIBLE_EXCHANGE",
                reason_text=(
                    "Your item is eligible for size or style exchange within the 14-day window. "
                    "Customer is responsible for the standard exchange return courier fee."
                ),
                rule_trace=rule_trace,
            )
        else:
            return EligibilityResult(
                decision=Decision.ELIGIBLE,
                reason_code="ELIGIBLE_RETURN",
                reason_text=(
                    "Your item is eligible for return within the 14-day window. "
                    "A refund will be issued to your original payment method after warehouse inspection."
                ),
                rule_trace=rule_trace,
            )
