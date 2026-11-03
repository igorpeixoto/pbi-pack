"""Data tests for the demo dataset in demo/data/.

Every expected number below is copied from demo/README.md on purpose, not imported from the generator:
if the generator stops planting a defect, these tests must fail rather than follow it.
"""

import csv
import hashlib
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "demo"
DATA = DEMO / "data"
FILES = ["customers.csv", "orders.csv", "products.csv", "targets.csv"]

# Documented in demo/README.md
ORDER_LINES_RANGE = (45_000, 55_000)
CUSTOMERS, PRODUCTS, TARGETS = 5_000, 300, 216
ORPHAN_IDS = {"C05001", "C05002", "C05003", "C05004", "C05005"}
ORPHAN_ORDERS, ORPHAN_LINES = 9, 22
JUNK_TOKENS = ["n/a", "-", "#N/A", ""]
JUNK_PER_TOKEN = 50
SHIP_BEFORE_ORDER = 12
STATUS_VARIANTS = {"lowercase": 100, "uppercase": 100, "trailing_space": 100, "lowercase_trailing_spaces": 100}
CANONICAL_STATUSES = {"Delivered", "Shipped", "Processing", "Cancelled", "Returned"}
SHIPPED_STATUSES = {"Delivered", "Shipped", "Returned"}


def load(name):
    with open(DATA / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def tables():
    return {name.removesuffix(".csv"): load(name) for name in FILES}


def canonical(status):
    return status.strip().capitalize()


def is_iso_date(value):
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def status_variant(status):
    """Classify a raw status as canonical or as one of the planted spellings."""
    if status in CANONICAL_STATUSES:
        return "canonical"
    core = status.rstrip(" ")
    trailing = len(status) - len(core)
    if trailing == 0 and core == core.lower():
        return "lowercase"
    if trailing == 0 and core == core.upper():
        return "uppercase"
    if trailing == 1 and core in CANONICAL_STATUSES:
        return "trailing_space"
    if trailing == 2 and core == core.lower():
        return "lowercase_trailing_spaces"
    return f"unexpected: {status!r}"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_default_seed_regenerates_byte_identical_files(tmp_path):
    """Protects against hidden nondeterminism (wall clock, set order, CRLF) and hand-edited CSVs."""
    subprocess.run([sys.executable, str(DEMO / "generate_data.py"), "--out", str(tmp_path)],
                   check=True, capture_output=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == FILES
    for name in FILES:
        assert sha256(tmp_path / name) == sha256(DATA / name), f"{name} differs from a fresh generation"


def test_row_counts_within_documented_ranges(tables):
    """Protects against a generator change silently shrinking or bloating a table."""
    assert ORDER_LINES_RANGE[0] <= len(tables["orders"]) <= ORDER_LINES_RANGE[1]
    assert len(tables["customers"]) == CUSTOMERS
    assert len(tables["products"]) == PRODUCTS
    assert len(tables["targets"]) == TARGETS


def test_primary_keys_are_unique(tables):
    """Protects the star schema: a duplicated dimension key would break a one-to-many relationship."""
    keys = {
        "customers": lambda r: r["customer_id"],
        "products": lambda r: r["product_id"],
        "orders": lambda r: (r["order_id"], r["line_no"]),
        "targets": lambda r: (r["month"], r["category"]),
    }
    for table, key in keys.items():
        dupes = [k for k, n in Counter(map(key, tables[table])).items() if n > 1]
        assert not dupes, f"{table}: duplicate keys {dupes[:5]}"


def test_only_planted_customer_orphans(tables):
    """Protects the Unknown-member exercise: exactly the documented orphans, no accidental ones."""
    customer_ids = {r["customer_id"] for r in tables["customers"]}
    orphans = [r for r in tables["orders"] if r["customer_id"] not in customer_ids]
    assert {r["customer_id"] for r in orphans} == ORPHAN_IDS
    assert len({r["order_id"] for r in orphans}) == ORPHAN_ORDERS
    assert len(orphans) == ORPHAN_LINES


def test_no_product_or_category_orphans(tables):
    """Protects against defects nobody documented: product and target keys always resolve."""
    product_ids = {r["product_id"] for r in tables["products"]}
    categories = {r["category"] for r in tables["products"]}
    assert {r["product_id"] for r in tables["orders"]} <= product_ids
    assert {r["category"] for r in tables["targets"]} == categories


@pytest.mark.parametrize("column", ["quantity", "unit_price", "discount"])
def test_junk_tokens_in_number_columns(tables, column):
    """Proves each number column carries exactly the planted junk tokens and nothing else unparseable."""
    values = [r[column] for r in tables["orders"]]
    for token in JUNK_TOKENS:
        assert values.count(token) == JUNK_PER_TOKEN, f"{column}: {token!r}"
    leftovers = [v for v in values if v not in JUNK_TOKENS and not is_number(v)]
    assert not leftovers, f"{column}: unplanned unparseable values {leftovers[:5]}"


def test_junk_tokens_in_ship_date(tables):
    """Proves the planted ship_date junk is exact; blanks on unshipped lines are legitimate, not junk."""
    shipped = [r["ship_date"] for r in tables["orders"] if canonical(r["status"]) in SHIPPED_STATUSES]
    for token in JUNK_TOKENS:
        assert shipped.count(token) == JUNK_PER_TOKEN, f"ship_date: {token!r}"
    unshipped = [r["ship_date"] for r in tables["orders"] if canonical(r["status"]) not in SHIPPED_STATUSES]
    assert set(unshipped) == {""}, "Processing and Cancelled lines must have no ship_date"
    leftovers = [v for v in shipped if v not in JUNK_TOKENS and not is_iso_date(v)]
    assert not leftovers, f"ship_date: unplanned unparseable values {leftovers[:5]}"


def test_clean_columns_stay_clean(tables):
    """Protects the columns the README calls clean, so the ETL exercise stays focused on the planted ones."""
    orders = tables["orders"]
    assert all(is_iso_date(r["order_date"]) for r in orders)
    assert all(is_iso_date(r["signup_date"]) for r in tables["customers"])
    assert all(is_number(r["list_price"]) and is_number(r["unit_cost"]) for r in tables["products"])
    assert all(is_iso_date(r["month"]) and is_number(r["revenue_target"]) for r in tables["targets"])


def test_ship_date_before_order_date(tables):
    """Proves the planted ship-before-order lines appear exactly at the documented count."""
    bad = [r for r in tables["orders"] if is_iso_date(r["ship_date"]) and r["ship_date"] < r["order_date"]]
    assert len(bad) == SHIP_BEFORE_ORDER


def test_status_spelling_variants(tables):
    """Proves the planted casing/whitespace variants are exact and all normalize to a canonical status."""
    counts = Counter(status_variant(r["status"]) for r in tables["orders"])
    del counts["canonical"]
    assert dict(counts) == STATUS_VARIANTS
    assert {canonical(r["status"]) for r in tables["orders"]} == CANONICAL_STATUSES
