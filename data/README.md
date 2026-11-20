# SYNTHETIC DATA — NOT REAL CUSTOMERS OR ORDERS

All demonstration data contained within this directory (`data/`)—including mock customer records, order numbers, transaction histories, shipping addresses, phone numbers, and synthetic customer inquiries—is completely artificial and generated solely for the evaluation, benchmarking, and demonstration of the **BrandMind** system.

## Data Inventory

- `data/raw/rlvnt/`: Authoritative raw brand guidelines and product lookbook PDFs provided by the brand.
- `data/processed/rlvnt/`: Cleaned text corpora and segmented markdown files tagged with metadata.
- `data/structured/`:
  - `products.csv`: Structured product catalog (IDs, categories, names, prices, sizes, colors, stock).
  - `orders.csv`: Synthetic customer order history used to validate order-status inquiries.
  - `policies.csv`: Normalized business policy parameters consumed by the deterministic policy engine.
- `data/evaluation/`:
  - `test_intents.csv`: Stratified intent classification utterances across 9 classes.
  - `test_end_to_end.json`: Curated evaluation scenarios covering easy, medium, hard, and adversarial queries.
