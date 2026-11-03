"""Generate the synthetic retail dataset behind the pack's demo report.

The company, its products and its customers are invented. Nothing here is drawn from a real business.

Usage:
    python demo/generate_data.py [--seed N] [--out DIR]

The same seed always produces byte-identical CSVs. The script never reads the wall clock: every date is
derived from the fixed WINDOW_START / WINDOW_END below. The planted defects are documented, with their
counts, in demo/README.md, and tests/test_demo_data.py fails if those counts drift.
"""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

COMPANY = "Quillmere Goods"  # invented; used only in the README and the report title
DEFAULT_SEED = 20230101
WINDOW_START = date(2023, 1, 1)
WINDOW_END = date(2025, 12, 31)
SIGNUP_START = date(2021, 1, 1)

N_PRODUCTS = 300
N_CUSTOMERS = 5000
N_ORDERS = 20000
LINES_PER_ORDER = ([1, 2, 3, 4, 5], [0.25, 0.30, 0.22, 0.14, 0.09])
DISCOUNTS = ([0.00, 0.05, 0.10, 0.15, 0.20], [0.60, 0.15, 0.12, 0.08, 0.05])
YEARLY_PRICE_INCREASE = 0.03
YEARLY_VOLUME_GROWTH = 0.18

STATUSES = ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"]
SHIPPED_STATUSES = {"Delivered", "Shipped", "Returned"}

REGIONS = (["North", "South", "East", "West", "Central"], [0.22, 0.24, 0.20, 0.21, 0.13])
SEGMENTS = (["Consumer", "Small Business", "Corporate"], [0.70, 0.20, 0.10])

# category -> subcategory -> (min list price, max list price, product nouns)
CATALOG = {
    "Kitchen": {
        "Cookware": (18, 140, ["Skillet", "Saucepan", "Stockpot", "Wok", "Dutch Oven"]),
        "Tableware": (6, 60, ["Dinner Plate Set", "Bowl Set", "Mug", "Serving Platter", "Tumbler Set"]),
        "Small Appliances": (25, 220, ["Kettle", "Blender", "Toaster", "Hand Mixer", "Coffee Grinder"]),
        "Storage": (5, 45, ["Canister Set", "Lunch Box", "Spice Rack", "Bread Bin", "Food Container Set"]),
    },
    "Home": {
        "Bedding": (20, 160, ["Duvet Cover", "Pillow Pair", "Throw Blanket", "Sheet Set", "Quilt"]),
        "Lighting": (15, 180, ["Table Lamp", "Floor Lamp", "Pendant Shade", "Desk Lamp", "String Lights"]),
        "Decor": (8, 90, ["Vase", "Wall Mirror", "Picture Frame", "Candle Holder", "Planter"]),
        "Bath": (6, 70, ["Towel Set", "Bath Mat", "Soap Dispenser", "Shower Caddy", "Bath Robe"]),
    },
    "Outdoor": {
        "Garden": (7, 110, ["Pruning Shears", "Hose Reel", "Watering Can", "Raised Bed Kit", "Trowel Set"]),
        "Camping": (12, 260, ["Tent", "Sleeping Bag", "Camp Stove", "Lantern", "Folding Chair"]),
        "Patio": (30, 320, ["Bistro Set", "Parasol", "Lounger", "Fire Bowl", "Outdoor Rug"]),
    },
    "Office": {
        "Stationery": (3, 35, ["Notebook", "Pen Set", "Planner", "Sticky Note Pack", "Desk Pad"]),
        "Desk Accessories": (8, 75, ["Monitor Stand", "Cable Tray", "Desk Organizer", "Document Tray", "Laptop Riser"]),
        "Office Furniture": (60, 480, ["Task Chair", "Standing Desk", "Bookcase", "Filing Cabinet", "Footrest"]),
    },
    "Fitness": {
        "Yoga": (10, 90, ["Yoga Mat", "Yoga Block Pair", "Strap", "Meditation Cushion", "Mat Bag"]),
        "Strength": (15, 260, ["Dumbbell Pair", "Kettlebell", "Resistance Band Set", "Weight Bench", "Pull-Up Bar"]),
        "Cardio Accessories": (8, 120, ["Jump Rope", "Step Platform", "Heart Rate Strap", "Exercise Mat", "Agility Ladder"]),
    },
    "Kids": {
        "Toys": (6, 85, ["Building Blocks", "Plush Bear", "Puzzle", "Train Set", "Play Kitchen"]),
        "Learning": (8, 70, ["Flash Card Set", "Globe", "Science Kit", "Abacus", "Picture Book Set"]),
        "Nursery": (15, 240, ["Crib Mobile", "Changing Mat", "Night Light", "Storage Basket", "Rocking Chair"]),
    },
}
ADJECTIVES = ["Classic", "Compact", "Everyday", "Heritage", "Linen", "Modern", "Nordic", "Oak",
              "Pebble", "Slate", "Studio", "Terra", "Urban", "Willow"]

# Seasonality: order volume by month, and each category's extra lift by month (Jan..Dec).
MONTH_VOLUME = [0.85, 0.80, 0.90, 0.95, 1.00, 0.95, 0.95, 1.00, 1.00, 1.05, 1.35, 1.60]
WEEKDAY_VOLUME = [1.00, 1.00, 1.00, 1.00, 1.05, 1.10, 1.00]
CATEGORY_SEASON = {
    "Outdoor": [0.5, 0.6, 0.9, 1.3, 1.7, 1.8, 1.7, 1.4, 1.0, 0.7, 0.5, 0.5],
    "Kids": [0.8, 0.8, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0, 1.0, 1.1, 1.5, 2.0],
    "Fitness": [1.8, 1.4, 1.1, 1.0, 1.0, 0.9, 0.9, 0.9, 1.1, 1.0, 0.9, 0.8],
}

# Planted defects. Change a number here and the README and the tests must change with it.
ORPHAN_CUSTOMER_IDS = ["C05001", "C05002", "C05003", "C05004", "C05005"]
ORPHAN_ORDERS = 9                   # whole orders reassigned to the orphan ids, cycling through them
JUNK_TOKENS = ["n/a", "-", "#N/A", ""]
JUNK_PER_TOKEN_PER_COLUMN = 50      # each token in each junk column, one junk cell per line
JUNK_NUMBER_COLUMNS = ["quantity", "unit_price", "discount"]
JUNK_DATE_COLUMN = "ship_date"      # only on shipped-status lines, where a blank is never legitimate
SHIP_BEFORE_ORDER_LINES = 12
STATUS_VARIANTS = {                 # variant name -> (transform, lines)
    "lowercase": (str.lower, 100),
    "uppercase": (str.upper, 100),
    "trailing_space": (lambda s: s + " ", 100),
    "lowercase_trailing_spaces": (lambda s: s.lower() + "  ", 100),
}

ORDER_COLUMNS = ["order_id", "line_no", "order_date", "ship_date", "customer_id", "product_id",
                 "quantity", "unit_price", "discount", "status"]


def daterange(start, end):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def make_products(rng):
    subcats = [(c, s, spec) for c, subs in CATALOG.items() for s, spec in subs.items()]
    base, extra = divmod(N_PRODUCTS, len(subcats))  # the first `extra` subcategories get one more
    rows = []
    for j, (category, subcategory, (lo, hi, nouns)) in enumerate(subcats):
        for i in range(base + (j < extra)):
            adjective = ADJECTIVES[int(rng.integers(len(ADJECTIVES)))]
            list_price = round(float(np.exp(rng.uniform(np.log(lo), np.log(hi))))) - 0.01
            rows.append({
                "product_id": f"P{len(rows) + 1:04d}",
                # the trailing model number keeps names unique when adjective and noun repeat
                "product_name": f"{adjective} {nouns[i % len(nouns)]} {len(rows) + 1:03d}",
                "category": category,
                "subcategory": subcategory,
                "list_price": list_price,
                "unit_cost": list_price * float(rng.uniform(0.45, 0.70)),
            })
    return rows


def make_customers(rng, fake):
    signup_days = daterange(SIGNUP_START, WINDOW_END - timedelta(days=30))
    picks = np.sort(rng.integers(len(signup_days), size=N_CUSTOMERS))
    regions = rng.choice(REGIONS[0], size=N_CUSTOMERS, p=REGIONS[1])
    segments = rng.choice(SEGMENTS[0], size=N_CUSTOMERS, p=SEGMENTS[1])
    rows = []
    for n in range(N_CUSTOMERS):
        rows.append({
            "customer_id": f"C{n + 1:05d}",
            "customer_name": fake.name(),
            "city": fake.city(),
            "region": str(regions[n]),
            "segment": str(segments[n]),
            "signup_date": signup_days[int(picks[n])],
        })
    return rows


def make_orders(rng, products, customers):
    days = daterange(WINDOW_START, WINDOW_END)
    weights = np.array([
        (1 + YEARLY_VOLUME_GROWTH) ** ((d - WINDOW_START).days / 365.25)
        * MONTH_VOLUME[d.month - 1] * WEEKDAY_VOLUME[d.weekday()]
        for d in days
    ])
    order_days = np.sort(rng.choice(len(days), size=N_ORDERS, p=weights / weights.sum()))

    popularity = rng.gamma(0.8, size=len(products))
    month_p = []
    for m in range(12):
        w = np.array([popularity[i] * CATEGORY_SEASON.get(p["category"], [1.0] * 12)[m]
                      for i, p in enumerate(products)])
        month_p.append(w / w.sum())

    signups = np.array([(c["signup_date"] - SIGNUP_START).days for c in customers])

    lines = []
    for n, day_index in enumerate(order_days):
        order_date = days[int(day_index)]
        # only customers who had signed up by the order date can order
        eligible = int(np.searchsorted(signups, (order_date - SIGNUP_START).days, side="right"))
        customer_id = customers[int(rng.integers(eligible))]["customer_id"]

        to_end = (WINDOW_END - order_date).days
        if to_end < 3:
            status = "Processing"
        elif to_end < 10:
            status = "Shipped"
        else:
            status = str(rng.choice(["Delivered", "Cancelled", "Returned"], p=[0.92, 0.03, 0.05]))
        if status in SHIPPED_STATUSES:
            ship_date = order_date + timedelta(days=int(rng.integers(1, min(6, to_end) + 1)))
        else:
            ship_date = None

        n_lines = int(rng.choice(LINES_PER_ORDER[0], p=LINES_PER_ORDER[1]))
        picks = rng.choice(len(products), size=n_lines, replace=False, p=month_p[order_date.month - 1])
        price_factor = (1 + YEARLY_PRICE_INCREASE) ** (order_date.year - WINDOW_START.year)
        for line_no, pi in enumerate(picks, start=1):
            product = products[int(pi)]
            lines.append({
                "order_id": 100001 + n,
                "line_no": line_no,
                "order_date": order_date,
                "ship_date": ship_date,
                "customer_id": customer_id,
                "product_id": product["product_id"],
                "category": product["category"],
                "quantity": 1 + int(rng.poisson(0.7)),
                "unit_price": round(product["list_price"] * price_factor, 2),
                "discount": float(rng.choice(DISCOUNTS[0], p=DISCOUNTS[1])),
                "status": status,
            })
    return lines


def make_targets(rng, lines):
    """Monthly revenue targets per category: the realized net revenue times seeded noise, rounded.

    Net revenue here is the demo model's Revenue definition: quantity x unit_price x (1 - discount) on
    every line except Cancelled and Returned ones. Keep the two in step, or Target Variance shows a gap
    the data doesn't have.
    """
    actual = {}
    for ln in lines:
        if ln["status"] in ("Cancelled", "Returned"):
            continue
        key = (date(ln["order_date"].year, ln["order_date"].month, 1), ln["category"])
        actual[key] = actual.get(key, 0.0) + ln["quantity"] * ln["unit_price"] * (1 - ln["discount"])
    rows = []
    for month in [d for d in daterange(WINDOW_START, WINDOW_END) if d.day == 1]:
        for category in CATALOG:
            target = actual.get((month, category), 0.0) * float(rng.uniform(0.93, 1.15))
            rows.append({"month": month, "category": category, "revenue_target": round(target / 500) * 500})
    return rows


def plant_defects(rng, lines):
    """Mutate the clean lines in place. Every defect lands on its own line, so each count is exact."""
    order_ids = sorted({ln["order_id"] for ln in lines})
    orphan_orders = rng.choice(order_ids, size=ORPHAN_ORDERS, replace=False)
    for k, order_id in enumerate(sorted(int(o) for o in orphan_orders)):
        for ln in lines:
            if ln["order_id"] == order_id:
                ln["customer_id"] = ORPHAN_CUSTOMER_IDS[k % len(ORPHAN_CUSTOMER_IDS)]
    orphan_set = {int(o) for o in orphan_orders}

    candidates = [i for i, ln in enumerate(lines) if ln["order_id"] not in orphan_set]
    shipped = [i for i in candidates if lines[i]["status"] in SHIPPED_STATUSES]
    shipped = [int(i) for i in rng.permutation(shipped)]

    n_date_junk = JUNK_PER_TOKEN_PER_COLUMN * len(JUNK_TOKENS)
    for k, i in enumerate(shipped[:n_date_junk]):
        lines[i][JUNK_DATE_COLUMN] = JUNK_TOKENS[k % len(JUNK_TOKENS)]
    for i in shipped[n_date_junk:n_date_junk + SHIP_BEFORE_ORDER_LINES]:
        lines[i]["ship_date"] = lines[i]["order_date"] - timedelta(days=int(rng.integers(1, 6)))
    used = set(shipped[:n_date_junk + SHIP_BEFORE_ORDER_LINES])

    rest = [int(i) for i in rng.permutation([i for i in candidates if i not in used])]
    pos = 0
    for column in JUNK_NUMBER_COLUMNS:
        for k in range(JUNK_PER_TOKEN_PER_COLUMN * len(JUNK_TOKENS)):
            lines[rest[pos]][column] = JUNK_TOKENS[k % len(JUNK_TOKENS)]
            pos += 1
    for transform, count in STATUS_VARIANTS.values():
        for _ in range(count):
            lines[rest[pos]]["status"] = transform(lines[rest[pos]]["status"])
            pos += 1


def fmt(value, decimals=None):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if decimals is not None:
        return f"{value:.{decimals}f}"
    return str(value)


def write_csv(path, columns, rows, decimals=None):
    decimals = decimals or {}
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([fmt(row[c], decimals.get(c)) for c in columns])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"default {DEFAULT_SEED}")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()

    # one independent stream per table, so changing one table's logic leaves the others' bytes alone
    rng_products, rng_customers, rng_orders, rng_targets, rng_defects = (
        np.random.default_rng(s) for s in np.random.SeedSequence(args.seed).spawn(5))
    fake = Faker("en_US")
    fake.seed_instance(args.seed)

    products = make_products(rng_products)
    customers = make_customers(rng_customers, fake)
    lines = make_orders(rng_orders, products, customers)
    targets = make_targets(rng_targets, lines)  # from clean lines, before any defect is planted
    plant_defects(rng_defects, lines)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "products.csv",
              ["product_id", "product_name", "category", "subcategory", "list_price", "unit_cost"],
              products, {"list_price": 2, "unit_cost": 2})
    write_csv(args.out / "customers.csv",
              ["customer_id", "customer_name", "city", "region", "segment", "signup_date"], customers)
    write_csv(args.out / "orders.csv", ORDER_COLUMNS, lines, {"unit_price": 2, "discount": 2})
    write_csv(args.out / "targets.csv", ["month", "category", "revenue_target"], targets)
    print(f"wrote {len(products)} products, {len(customers)} customers, {len(lines)} order lines, "
          f"{len(targets)} targets to {args.out}")


if __name__ == "__main__":
    main()
