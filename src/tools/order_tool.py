"""
BrandMind — Tool 2: get_order_status
Retrieves order delivery status from the verified synthetic order database.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from src.schemas import OrderItem


class OrderTool:
    def __init__(self, orders_csv: str = "data/structured/orders.csv"):
        self.orders_csv = Path(orders_csv)
        self._df: Optional[pd.DataFrame] = None
        self._load()

    def _load(self):
        if self.orders_csv.exists():
            self._df = pd.read_csv(self.orders_csv)
        else:
            self._df = pd.DataFrame()

    def get_order_status(self, order_id: str, brand_id: str = "rlvnt") -> Optional[OrderItem]:
        """Retrieves and validates an order matching order_id and brand_id."""
        if self._df.empty or not order_id:
            return None

        # Case-insensitive match on order_id
        matched = self._df[
            (self._df["order_id"].str.lower() == order_id.lower())
            & (self._df["brand_id"] == brand_id)
        ]

        if matched.empty:
            return None

        row = matched.iloc[0]
        delivery_date = None
        if pd.notnull(row["delivery_date"]):
            from datetime import date
            delivery_date = date.fromisoformat(str(row["delivery_date"]))

        from datetime import date
        order_date = date.fromisoformat(str(row["order_date"]))

        return OrderItem(
            order_id=row["order_id"],
            brand_id=row["brand_id"],
            customer_id=row["customer_id"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            order_date=order_date,
            delivery_date=delivery_date,
            status=row["status"],
            delivery_status=row["delivery_status"],
            total_amount=float(row["total_amount"]),
            currency=row.get("currency", "EGP"),
        )
