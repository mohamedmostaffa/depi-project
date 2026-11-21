"""
BrandMind — Policy Consistency & Data Integrity Validator
Enforces zero contradictions between YAML profiles, CSV tables, and raw source documents.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import yaml

from src.ingestion.pdf_extractor import PDFExtractor


class PolicyIntegrityValidator:
    def __init__(
        self,
        brand_id: str = "rlvnt",
        config_path: str = "config/rlvnt.yaml",
        policies_csv: str = "data/structured/policies.csv",
        products_csv: str = "data/structured/products.csv",
        orders_csv: str = "data/structured/orders.csv",
    ):
        self.brand_id = brand_id
        self.config_path = Path(config_path)
        self.policies_csv = Path(policies_csv)
        self.products_csv = Path(products_csv)
        self.orders_csv = Path(orders_csv)

    def validate_all(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        # 1. Load config
        if not self.config_path.exists():
            errors.append(f"Config file missing: {self.config_path}")
            return False, errors

        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # 2. Load CSVs
        if not self.policies_csv.exists():
            errors.append(f"Policies CSV missing: {self.policies_csv}")
        if not self.products_csv.exists():
            errors.append(f"Products CSV missing: {self.products_csv}")
        if not self.orders_csv.exists():
            errors.append(f"Orders CSV missing: {self.orders_csv}")

        if errors:
            return False, errors

        df_policies = pd.read_csv(self.policies_csv)
        df_products = pd.read_csv(self.products_csv)
        df_orders = pd.read_csv(self.orders_csv)

        # 3. Check Brand Isolation
        for name, df in [("policies", df_policies), ("products", df_products), ("orders", df_orders)]:
            bad_brands = df[df["brand_id"] != self.brand_id]
            if not bad_brands.empty:
                errors.append(f"Data leakage detected in {name}.csv: contains brands {bad_brands['brand_id'].unique()}")

        # 4. Check Policy Parameters consistency between YAML and CSV
        yaml_ret_window = cfg.get("policies", {}).get("return_exchange_window_days")
        csv_ret_row = df_policies[df_policies["policy_type"] == "return"]
        if csv_ret_row.empty:
            errors.append("Return policy missing from policies.csv")
        else:
            csv_ret_window = int(csv_ret_row.iloc[0]["allowed_days"])
            if yaml_ret_window != csv_ret_window:
                errors.append(
                    f"Return window contradiction: YAML ({yaml_ret_window}) != CSV ({csv_ret_window})"
                )

        # 5. Check Product references in Orders
        valid_product_ids = set(df_products["product_id"])
        order_prod_ids = set(df_orders["product_id"])
        unknown_prods = order_prod_ids - valid_product_ids
        if unknown_prods:
            errors.append(f"Orders reference non-existent product IDs: {unknown_prods}")

        # 6. Check Order date logic (delivery >= order)
        delivered_orders = df_orders[df_orders["status"] == "DELIVERED"].dropna(subset=["delivery_date"])
        for _, row in delivered_orders.iterrows():
            if row["delivery_date"] < row["order_date"]:
                errors.append(f"Order {row['order_id']} delivery_date precedes order_date")

        # 7. Check Raw PDF Source Alignment
        extractor = PDFExtractor(brand_id=self.brand_id)
        docs = extractor.extract_all()
        policy_doc = docs.get("rlvntbrandidentityandpolicies.pdf", [])
        if not policy_doc:
            errors.append("Authoritative policy PDF (rlvntbrandidentityandpolicies.pdf) missing or unextracted")
        else:
            # Confirm presence of key operational clauses
            full_text = " ".join(p.text for p in policy_doc)
            if "unworn" not in full_text.lower():
                errors.append("Expected condition 'unworn' not found in raw policy manual")
            if "tags attached" not in full_text.lower():
                errors.append("Expected condition 'tags attached' not found in raw policy manual")

        is_valid = len(errors) == 0
        return is_valid, errors


if __name__ == "__main__":
    validator = PolicyIntegrityValidator()
    valid, errs = validator.validate_all()
    if valid:
        print("PASS: Zero policy contradictions or integrity violations detected.")
    else:
        print(f"FAIL: Detected {len(errs)} validation errors:")
        for e in errs:
            print(f"  - {e}")
        exit(1)
