"""Generate a small, deterministic, intentionally imperfect Retail 360 sample dataset.

The output mimics what the ingestion layer receives from the ERP (CSV extracts landed by
Azure Data Factory) and from the POS event stream (JSON lines captured by Event Hubs).
It deliberately contains duplicates, null keys, malformed e-mails and non-positive
quantities so that the Silver data-quality rules have something to catch.

Usage:
    python scripts/generate_sample_data.py --out data/sample
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
COUNTRIES = [
    ("DE", "Berlin"),
    ("FR", "Paris"),
    ("GB", "London"),
    ("IN", "Mumbai"),
    ("US", "Austin"),
]
CATEGORIES = {
    "Apparel": ["T-Shirts", "Jeans", "Jackets"],
    "Footwear": ["Sneakers", "Boots"],
    "Home": ["Kitchen", "Decor"],
    "Electronics": ["Audio", "Wearables"],
}
TIERS = ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
CHANNELS = ["STORE", "ONLINE", "MOBILE"]
STATUSES = ["COMPLETED"] * 8 + ["CANCELLED", "RETURNED"]
START = datetime(2026, 9, 1)


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def build(out: Path) -> None:
    rng = random.Random(SEED)

    # ---- stores -----------------------------------------------------------------------
    stores = []
    for i in range(1, 7):
        country, city = COUNTRIES[(i - 1) % len(COUNTRIES)]
        stores.append(
            [
                f"S{i:03d}",
                f"Retail360 {city}",
                "EMEA" if country in ("DE", "FR", "GB") else "ROW",
                country,
                city,
                "FLAGSHIP" if i % 3 == 1 else "STANDARD",
                "2019-03-01",
            ]
        )
    write_csv(
        out / "erp/stores/stores_20260901.csv",
        ["store_id", "store_name", "region", "country", "city", "store_type", "open_date"],
        stores,
    )

    # ---- products ---------------------------------------------------------------------
    products = []
    pid = 1
    for category, subs in CATEGORIES.items():
        for sub in subs:
            for _ in range(3):
                price = round(rng.uniform(9, 240), 2)
                products.append(
                    [
                        f"P{pid:04d}",
                        f"SKU-{pid:05d}",
                        f"{sub} item {pid}",
                        category,
                        sub,
                        rng.choice(["Nordic", "Aurora", "Pinnacle", "Verve"]),
                        price,
                        round(price * rng.uniform(0.4, 0.7), 2),
                        "Y" if rng.random() > 0.05 else "N",
                        ts(START - timedelta(days=rng.randint(30, 400))),
                    ]
                )
                pid += 1
    products.append(list(products[0][:-1]) + [ts(START - timedelta(days=500))])  # stale duplicate
    write_csv(
        out / "erp/products/products_20260901.csv",
        [
            "product_id",
            "sku",
            "product_name",
            "category",
            "subcategory",
            "brand",
            "unit_price",
            "cost_price",
            "active_flag",
            "updated_at",
        ],
        products,
    )

    # ---- customers --------------------------------------------------------------------
    customers = []
    first = ["Ava", "Liam", "Noah", "Mia", "Zoe", "Arjun", "Priya", "Lena", "Hugo", "Emma"]
    last = ["Schmidt", "Dubois", "Smith", "Patel", "Garcia", "Khan", "Muller", "Brown"]
    for i in range(1, 61):
        country, city = COUNTRIES[i % len(COUNTRIES)]
        fn, ln = rng.choice(first), rng.choice(last)
        customers.append(
            [
                f"C{i:05d}",
                fn,
                ln,
                f"{fn}.{ln}{i}@example.com".lower(),
                f"+{rng.randint(10, 99)}{rng.randint(100000000, 999999999)}",
                f"{rng.randint(1960, 2005)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                country,
                city,
                f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                rng.choice(TIERS),
                ts(START - timedelta(days=rng.randint(1, 120))),
            ]
        )
    # dirty rows: older duplicate versions, null keys, malformed e-mails
    for i in (3, 7, 11, 19, 23):
        old = list(customers[i])
        old[-1] = ts(START - timedelta(days=400))
        old[9] = "BRONZE"
        customers.append(old)
    customers.append(
        [
            "",
            "No",
            "Key",
            "nokey@example.com",
            "+10000000000",
            "1990-01-01",
            "US",
            "Austin",
            "2025-01-01",
            "GOLD",
            ts(START),
        ]
    )
    customers.append(
        [
            None,
            "Null",
            "Key",
            "nullkey@example.com",
            "+10000000001",
            "1991-01-01",
            "US",
            "Austin",
            "2025-01-02",
            "GOLD",
            ts(START),
        ]
    )
    for i in (5, 6, 8):
        customers[i][3] = "not-an-email"
    write_csv(
        out / "erp/customers/customers_20260901.csv",
        [
            "customer_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "birth_date",
            "country",
            "city",
            "signup_date",
            "loyalty_tier",
            "updated_at",
        ],
        customers,
    )

    # ---- orders and order items -------------------------------------------------------
    orders, items = [], []
    for o in range(1, 241):
        order_ts = START + timedelta(
            days=rng.randint(0, 29), hours=rng.randint(8, 21), minutes=rng.randint(0, 59)
        )
        channel = rng.choice(CHANNELS)
        store = f"S{rng.randint(1, 6):03d}" if channel == "STORE" else "S001"
        orders.append(
            [
                f"O{o:06d}",
                f"C{rng.randint(1, 60):05d}",
                store,
                channel,
                ts(order_ts),
                rng.choice(STATUSES),
                "EUR",
                ts(order_ts + timedelta(minutes=5)),
            ]
        )
        for line in range(1, rng.randint(2, 4) + 1):
            p = rng.choice(products[:-1])
            items.append(
                [f"O{o:06d}", line, p[0], rng.randint(1, 4), p[6], rng.choice([0, 0, 0, 5, 10, 15])]
            )
    orders.append(list(orders[0]))  # exact duplicate
    orders.append(["O900001", None, "S001", "ONLINE", ts(START), "COMPLETED", "EUR", ts(START)])
    for idx in (4, 40, 80):
        items[idx][3] = 0 if idx == 4 else -1  # non-positive quantities
    write_csv(
        out / "erp/orders/orders_20260901.csv",
        [
            "order_id",
            "customer_id",
            "store_id",
            "channel",
            "order_ts",
            "status",
            "currency",
            "updated_at",
        ],
        orders,
    )
    write_csv(
        out / "erp/order_items/order_items_20260901.csv",
        ["order_id", "line_no", "product_id", "quantity", "unit_price", "discount_pct"],
        items,
    )

    # ---- POS events (JSON lines) ------------------------------------------------------
    events = []
    for e in range(1, 401):
        when = START + timedelta(
            days=rng.randint(0, 29),
            hours=rng.randint(8, 21),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )
        events.append(
            {
                "event_id": f"E{e:07d}",
                "store_id": f"S{rng.randint(1, 6):03d}",
                "sku": rng.choice(products[:-1])[1],
                "event_type": rng.choice(["SALE", "SALE", "RETURN"]),
                "quantity": rng.randint(1, 3),
                "event_ts": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    events += events[:10]  # at-least-once delivery duplicates
    path = out / "streaming/pos_events/pos_events_20260901.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/sample"))
    args = parser.parse_args()
    build(args.out)
    print(f"Sample data written to {args.out}")
