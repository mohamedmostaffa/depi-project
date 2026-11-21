"""
Unit Tests for RLVNT Data Engineering & Policy Validation
Phase 2 Quality Gate Tests
"""

import pandas as pd
import pytest

from src.ingestion.pdf_extractor import PDFExtractor
from src.ingestion.validate_policies import PolicyIntegrityValidator


def test_pdf_extractor_loads_all_pages():
    """Verify that all three authoritative PDFs load and extract accurately."""
    extractor = PDFExtractor(brand_id="rlvnt")
    docs = extractor.extract_all()

    assert "rlvntbrandidentityandpolicies.pdf" in docs
    assert "rlvnt_winter_collection.pdf" in docs
    assert "rlvnt_outfits_collection.pdf" in docs

    assert len(docs["rlvntbrandidentityandpolicies.pdf"]) == 7
    assert len(docs["rlvnt_outfits_collection.pdf"]) == 8
    assert len(docs["rlvnt_winter_collection.pdf"]) == 9


def test_product_catalog_integrity():
    """Verify products.csv structure, non-empty fields, and valid prices."""
    df = pd.read_csv("data/structured/products.csv")
    assert len(df) >= 20, "Should contain at least 20 verified catalog products"

    required_cols = [
        "product_id", "brand_id", "name", "category", "price",
        "currency", "sizes", "colors", "stock", "returnable"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    assert (df["brand_id"] == "rlvnt").all(), "All products must belong to brand 'rlvnt'"
    assert (df["price"] > 0).all(), "All products must have positive prices"
    assert (df["currency"] == "EGP").all(), "All product prices must be in EGP"
    assert not df["name"].isnull().any(), "No product name may be null"


def test_order_data_integrity():
    """Verify orders.csv contains 50 valid synthetic orders linked to catalog products."""
    df_orders = pd.read_csv("data/structured/orders.csv")
    df_products = pd.read_csv("data/structured/products.csv")

    assert len(df_orders) == 50, "Should contain exactly 50 synthetic orders"
    valid_pids = set(df_products["product_id"])

    for _, row in df_orders.iterrows():
        assert row["brand_id"] == "rlvnt"
        assert row["product_id"] in valid_pids
        assert row["total_amount"] > 0
        assert row["currency"] == "EGP"

        if pd.notnull(row["delivery_date"]):
            assert row["delivery_date"] >= row["order_date"], "Delivery date cannot precede order date"


def test_policy_consistency_zero_contradictions():
    """Verify that PolicyIntegrityValidator discovers zero policy contradictions."""
    validator = PolicyIntegrityValidator()
    is_valid, errors = validator.validate_all()
    assert is_valid is True, f"Policy validation failed with errors: {errors}"
    assert len(errors) == 0
