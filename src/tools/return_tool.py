"""
BrandMind — Tool 3: check_return_eligibility
Binds customer facts and brand policy to the deterministic PolicyEngine.
"""

from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from src.policies.engine import PolicyEngine
from src.schemas import Decision, EligibilityResult


class ReturnTool:
    def __init__(
        self,
        policies_csv: str = "data/structured/policies.csv",
        products_csv: str = "data/structured/products.csv",
        orders_csv: str = "data/structured/orders.csv",
    ):
        self.policies_csv = Path(policies_csv)
        self.products_csv = Path(products_csv)
        self.orders_csv = Path(orders_csv)
        self._load()

    def _load(self):
        self.policies: Dict[str, Dict[str, Any]] = {}
        if self.policies_csv.exists():
            df_p = pd.read_csv(self.policies_csv)
            for _, row in df_p.iterrows():
                key = f"{row['brand_id']}_{row['policy_type']}"
                self.policies[key] = row.to_dict()

        self.catalog_map: Dict[str, Dict[str, Any]] = {}
        if self.products_csv.exists():
            df_prod = pd.read_csv(self.products_csv)
            for _, row in df_prod.iterrows():
                self.catalog_map[row["product_id"]] = row.to_dict()

        self.orders_map: Dict[str, Dict[str, Any]] = {}
        if self.orders_csv.exists():
            df_ord = pd.read_csv(self.orders_csv)
            for _, row in df_ord.iterrows():
                self.orders_map[row["order_id"]] = row.to_dict()

    def check_eligibility(
        self,
        facts: Dict[str, Any],
        brand_id: str = "rlvnt",
        today: Optional[date] = None,
    ) -> EligibilityResult:
        """Determines return/exchange eligibility via deterministic policy engine."""
        curr_date = today or date.today()
        req_type = facts.get("request_type", "return").lower()
        policy_key = f"{brand_id}_{req_type}"

        policy_dict = self.policies.get(policy_key) or self.policies.get(f"{brand_id}_return")
        if not policy_dict:
            return EligibilityResult(
                decision=Decision.NEEDS_INFO,
                reason_code="POLICY_NOT_FOUND",
                reason_text=f"No verified return/exchange policy configured for brand '{brand_id}'.",
                missing_fields=[],
                rule_trace=["Error: Brand policy record missing"],
            )

        return PolicyEngine.evaluate(
            facts=facts,
            policy=policy_dict,
            today=curr_date,
            catalog_products=self.catalog_map,
            mock_orders=self.orders_map,
        )
