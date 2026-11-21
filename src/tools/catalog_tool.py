"""
BrandMind — Tool 1: search_products
Searches the structured product catalog using exact filters and keywords.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.schemas import ProductItem


class CatalogTool:
    def __init__(self, products_csv: str = "data/structured/products.csv"):
        self.products_csv = Path(products_csv)
        self._df: Optional[pd.DataFrame] = None
        self._load()

    def _load(self):
        if self.products_csv.exists():
            self._df = pd.read_csv(self.products_csv)
        else:
            self._df = pd.DataFrame()

    def search_products(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        max_price: Optional[float] = None,
        brand_id: str = "rlvnt",
    ) -> List[ProductItem]:
        """Searches products with verified brand isolation and filters."""
        if self._df.empty:
            return []

        df = self._df[self._df["brand_id"] == brand_id]

        if category:
            df = df[df["category"].str.contains(category, case=False, na=False)]

        if color:
            df = df[df["colors"].str.contains(color, case=False, na=False)]

        if size:
            df = df[df["sizes"].str.contains(size, case=False, na=False)]

        if max_price:
            df = df[df["price"] <= max_price]

        if query:
            q_lower = query.lower()
            mask = (
                df["name"].str.lower().str.contains(q_lower, na=False)
                | df["description"].str.lower().str.contains(q_lower, na=False)
                | df["category"].str.lower().str.contains(q_lower, na=False)
            )
            df = df[mask]

        results: List[ProductItem] = []
        for _, row in df.iterrows():
            sizes_list = [s.strip() for s in str(row["sizes"]).split(",") if s.strip()]
            colors_list = [c.strip() for c in str(row["colors"]).split(",") if c.strip()]
            results.append(
                ProductItem(
                    product_id=row["product_id"],
                    brand_id=row["brand_id"],
                    name=row["name"],
                    category=row["category"],
                    price=float(row["price"]),
                    currency=row.get("currency", "EGP"),
                    sizes=sizes_list,
                    colors=colors_list,
                    description=row["description"],
                    stock=int(row.get("stock", 0)),
                    returnable=bool(row.get("returnable", True)),
                )
            )

        return results

    def get_product(self, product_id: str, brand_id: str = "rlvnt") -> Optional[ProductItem]:
        """Fetches single product by ID."""
        items = self.search_products(brand_id=brand_id)
        for item in items:
            if item.product_id.lower() == product_id.lower():
                return item
        return None
