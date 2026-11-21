"""
Synthetic Order Generator for BrandMind × RLVNT
Generates 50 realistic mock orders with deterministic seed for testing and evaluation.
"""

from datetime import date, timedelta
import random
import pandas as pd


def generate_mock_orders(output_path: str = "data/structured/orders.csv"):
    random.seed(42)

    # Reference today as 2026-11-20
    base_today = date(2026, 11, 20)

    products = [
        ("RLVNT-HD-01", "Lionel Messi 100% Cotton Signature Hoodie", 1650.0),
        ("RLVNT-HD-02", "Neymar Jr Brown Gothic Hoodie", 1600.0),
        ("RLVNT-CRW-01", "San Andreas Graphic Crewneck", 1250.0),
        ("RLVNT-CRW-02", "Michael Jackson Tribute Crewneck", 1300.0),
        ("RLVNT-CRW-03", "Kylian Mbappé World Cup Crewneck", 1250.0),
        ("RLVNT-CRW-05", "DOGS GOTTA EAT Statement Crewneck", 1200.0),
        ("RLVNT-CRW-06", "Jude Bellingham Bellingoal Crewneck", 1300.0),
        ("RLVNT-CRW-07", "Fight Club Tyler Durden Crewneck", 1350.0),
        ("RLVNT-JSY-01", "AC Milan 1990s Lotto Retro Jersey", 1450.0),
        ("RLVNT-JKT-01", "Germany 1990 Heritage Track Jacket", 1850.0),
        ("RLVNT-BTM-01", "Vintage Washed Wide-Leg Denim Jeans", 1400.0),
        ("RLVNT-BTM-02", "Relaxed Streetwear Sweatpants Black", 1100.0),
        ("RLVNT-CLR-01", "Summer Archive Graphic Tee (Final Sale)", 650.0),
    ]

    orders = []

    # Specifically craft landmark test orders
    # Order 1: Exactly 10 days ago (eligible)
    orders.append({
        "order_id": "RLVNT-1001",
        "brand_id": "rlvnt",
        "customer_id": "CUST-001",
        "customer_name": "Omar Khaled",
        "product_id": "RLVNT-HD-01",
        "product_name": "Lionel Messi 100% Cotton Signature Hoodie",
        "order_date": (base_today - timedelta(days=12)).isoformat(),
        "delivery_date": (base_today - timedelta(days=10)).isoformat(),
        "status": "DELIVERED",
        "delivery_status": "DELIVERED",
        "total_amount": 1650.0,
        "currency": "EGP",
        "shipping_address": "Nasr City, Cairo, Egypt",
    })

    # Order 2: Exactly 14 days ago (boundary: eligible)
    orders.append({
        "order_id": "RLVNT-1002",
        "brand_id": "rlvnt",
        "customer_id": "CUST-002",
        "customer_name": "Youssef Hassan",
        "product_id": "RLVNT-CRW-01",
        "product_name": "San Andreas Graphic Crewneck",
        "order_date": (base_today - timedelta(days=16)).isoformat(),
        "delivery_date": (base_today - timedelta(days=14)).isoformat(),
        "status": "DELIVERED",
        "delivery_status": "DELIVERED",
        "total_amount": 1250.0,
        "currency": "EGP",
        "shipping_address": "Maadi, Cairo, Egypt",
    })

    # Order 3: Exactly 15 days ago (boundary: NOT eligible)
    orders.append({
        "order_id": "RLVNT-1003",
        "brand_id": "rlvnt",
        "customer_id": "CUST-003",
        "customer_name": "Ahmed Mansour",
        "product_id": "RLVNT-CRW-05",
        "product_name": "DOGS GOTTA EAT Statement Crewneck",
        "order_date": (base_today - timedelta(days=17)).isoformat(),
        "delivery_date": (base_today - timedelta(days=15)).isoformat(),
        "status": "DELIVERED",
        "delivery_status": "DELIVERED",
        "total_amount": 1200.0,
        "currency": "EGP",
        "shipping_address": "Giza, Egypt",
    })

    # Order 4: Clearance item (non-returnable category)
    orders.append({
        "order_id": "RLVNT-1004",
        "brand_id": "rlvnt",
        "customer_id": "CUST-004",
        "customer_name": "Nour Ibrahim",
        "product_id": "RLVNT-CLR-01",
        "product_name": "Summer Archive Graphic Tee (Final Sale)",
        "order_date": (base_today - timedelta(days=5)).isoformat(),
        "delivery_date": (base_today - timedelta(days=3)).isoformat(),
        "status": "DELIVERED",
        "delivery_status": "DELIVERED",
        "total_amount": 650.0,
        "currency": "EGP",
        "shipping_address": "Alexandria, Egypt",
    })

    # Order 5: In transit (status inquiry)
    orders.append({
        "order_id": "RLVNT-1005",
        "brand_id": "rlvnt",
        "customer_id": "CUST-005",
        "customer_name": "Mariam Ali",
        "product_id": "RLVNT-JKT-01",
        "product_name": "Germany 1990 Heritage Track Jacket",
        "order_date": (base_today - timedelta(days=2)).isoformat(),
        "delivery_date": None,
        "status": "SHIPPED",
        "delivery_status": "IN_TRANSIT",
        "total_amount": 1850.0,
        "currency": "EGP",
        "shipping_address": "New Cairo, Egypt",
    })

    # Generate remaining 45 orders up to RLVNT-1050
    cities = ["Cairo", "Giza", "Alexandria", "Mansoura", "Tanta", "Zagazig", "Assiut", "Ismailia"]
    names = [
        "Karim Zaki", "Salma Adel", "Tarek Farouk", "Heba Mostafa", "Ziad Nabil",
        "Dina Magdy", "Mahmoud Samy", "Rana Wael", "Sherif Ezzat", "Layla Kamel",
        "Hazem Shaker", "Mona Gamal", "Hossam Helmy", "Aya Samir", "Amr Fouad",
    ]

    for i in range(6, 51):
        order_num = f"RLVNT-{1000 + i}"
        cust_id = f"CUST-{100 + i}"
        cust_name = random.choice(names)
        prod = random.choice(products)
        days_ago = random.randint(1, 40)
        ord_date = base_today - timedelta(days=days_ago)

        if days_ago <= 2:
            status = "PROCESSING"
            deliv_status = "PENDING_DISPATCH"
            deliv_date = None
        elif days_ago <= 4:
            status = "SHIPPED"
            deliv_status = random.choice(["IN_TRANSIT", "OUT_FOR_DELIVERY"])
            deliv_date = None
        else:
            status = "DELIVERED"
            deliv_status = "DELIVERED"
            deliv_date = (ord_date + timedelta(days=random.randint(1, 3))).isoformat()

        orders.append({
            "order_id": order_num,
            "brand_id": "rlvnt",
            "customer_id": cust_id,
            "customer_name": cust_name,
            "product_id": prod[0],
            "product_name": prod[1],
            "order_date": ord_date.isoformat(),
            "delivery_date": deliv_date,
            "status": status,
            "delivery_status": deliv_status,
            "total_amount": prod[2],
            "currency": "EGP",
            "shipping_address": f"{random.choice(cities)}, Egypt",
        })

    df = pd.DataFrame(orders)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} synthetic orders at {output_path}")


if __name__ == "__main__":
    generate_mock_orders()
