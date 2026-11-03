# Demo dataset — Quillmere Goods

Synthetic sales data for **Quillmere Goods**, an invented online retailer of home, kitchen, outdoor, office,
fitness and kids' products. The company, the product catalog and the customers are made up: product names
come from word lists in `generate_data.py`, and customer names and cities come from
[Faker](https://faker.readthedocs.io/) (`en_US`). Nothing here describes a real business or a real person.

The data feeds the pack's demo report. It arrives already shaped as a star, so the ETL exercise is about
**cleaning**, not reshaping, and it carries a fixed set of [planted defects](#planted-defects) that the
pack's Power Query rules exist to handle.

## Files

All files are UTF-8 CSV with LF line endings and a header row. Dates are ISO `yyyy-mm-dd`.

| File | Grain | Rows | Columns |
|---|---|---|---|
| `data/orders.csv` | one row per order line | 45,000–55,000 (this seed: 50,557 lines, 20,000 orders) | `order_id`, `line_no`, `order_date`, `ship_date`, `customer_id`, `product_id`, `quantity`, `unit_price`, `discount`, `status` |
| `data/customers.csv` | one row per customer | 5,000 | `customer_id`, `customer_name`, `city`, `region`, `segment`, `signup_date` |
| `data/products.csv` | one row per product | 300 | `product_id`, `product_name`, `category`, `subcategory`, `list_price`, `unit_cost` |
| `data/targets.csv` | month × category | 216 (36 months × 6 categories) | `month` (first day of the month), `category`, `revenue_target` |

Keys: `customer_id` and `product_id` are the dimension keys; an order line is identified by
`(order_id, line_no)`; a target by `(month, category)`.

What the numbers mean:

- **Window:** orders from 2023-01-01 to 2025-12-31, with yearly volume growth, a November–December peak
  and category seasonality (Outdoor peaks in early summer, Fitness in January, Kids in December).
- **Prices:** `products.list_price` is the 2023 list price. `orders.unit_price` is that price plus 3% per
  year after 2023. `discount` is a fraction (`0.10` = 10%), so line revenue is
  `quantity × unit_price × (1 − discount)` and line cost is `quantity × unit_cost`.
- **Status:** `Delivered`, `Shipped`, `Processing`, `Cancelled` or `Returned`. Orders in the last ten
  days of the window are still `Shipped` or `Processing`.
- **`ship_date` is blank on purpose for `Processing` and `Cancelled` lines** (1,881 lines in this seed):
  those orders never shipped. Only a blank on a `Delivered`, `Shipped` or `Returned` line is a defect.
- **Customers** only place orders after their `signup_date`. Some customers never order.
- **Revenue** is defined for the demo as `quantity × unit_price × (1 − discount)` over every line except
  `Cancelled` and `Returned` ones: cancelled orders never billed, and returned ones were refunded.
  The demo model's Revenue measure uses the same rule.
- **Targets** are each month's Revenue per category, as defined above, scaled by seeded noise between
  0.93 and 1.15 and rounded to 500, so a variance page shows both misses and beats. They are computed from
  the clean values before any defect is planted, so the lines whose number columns the ETL scrubs to null
  (600 of them, about 1.2%) make actual Revenue run slightly below what the targets were built from.

## Planted defects

Each defect sits on its own order line (no line carries two of them), and the orphan orders carry none of
the line-level defects, so every count below is exact. `tests/test_demo_data.py` checks each one and fails
if a defect *disappears* as well as if one grows.

| Defect | Where | Count | What the ETL should do |
|---|---|---|---|
| Junk tokens `"n/a"`, `"-"`, `"#N/A"`, `""` | `orders.quantity`, `orders.unit_price`, `orders.discount` | 50 of each token in each column: 200 cells per column, 600 in all (~0.4% of lines per column) | Scrub to `null` before the type cast (Hard Rule 6b) |
| Same junk tokens | `orders.ship_date`, on `Delivered` / `Shipped` / `Returned` lines only | 50 of each token: 200 cells | Scrub to `null` before the type cast |
| `ship_date` earlier than `order_date` | `orders`, shipped-status lines | 12 lines, 1–5 days early | Flag and route to `_DataQualityIssues` (Hard Rule 9) |
| Inconsistent status spelling | `orders.status` | 400 lines: 100 lowercase (`delivered`), 100 uppercase (`DELIVERED`), 100 with one trailing space (`Delivered `), 100 lowercase with two trailing spaces (`delivered  `) | `Text.Trim` and `Text.Proper` to the five canonical values |
| Orphan `customer_id` | `orders.customer_id` | 5 distinct ids (`C05001`–`C05005`) on 9 orders, 22 lines | Map to an "Unknown" customer member |

Everything else is clean on purpose: `order_date`, `product_id`, every column in `customers.csv`,
`products.csv` and `targets.csv`. There are no orphan `product_id`s and no unknown categories in the targets.

## Opening the demo report

The demo template at `pbi-starter/templates/demo/Template-DEMO.pbip` opens with its data already loaded:
the model's saved data (`Template-DEMO.SemanticModel/.pbi/cache.abf`) is committed, so the report shows
numbers wherever the repo was cloned, with no refresh.

A refresh reads these CSVs through one text parameter, `DataFolder`. Power Query's file connectors accept only
absolute paths, and a query has no way to ask where its own `.pbip` lives, so the parameter holds the
**absolute** path of this folder's `data\`. It defaults to `C:\src\pbi-pack\demo\data\`, the clone path the
main README suggests, so a clone there refreshes as is. Anywhere else:

1. Open `Template-DEMO.pbip` in Power BI Desktop.
2. **Home → Transform data → Edit parameters**, set `DataFolder` to the full path of this folder's `data\`
   on your machine (the trailing backslash is optional).
3. **Apply changes**, then **Refresh**.

Until then a refresh stops with a message naming `DataFolder`, and the saved data stays loaded.

**The saved data must match the model.** Desktop drops it when the model definition changes, the parameter
included, and the report then opens empty. So after any edit under `Template-DEMO.SemanticModel/definition/`:
refresh in Desktop, save, and update the two hashes in `tests/test_demo_template.py`, which fails until you do.
Committing a different `DataFolder` value has the same effect, so don't commit a local path.

The ETL handles each [planted defect](#planted-defects) the way the table above says. A refresh also stops
with a named error if a structural invariant breaks (a value that is neither a junk token nor valid for its
column type, a blank or junk key, order date, product category, unit cost or revenue target, a duplicate
key, a blank status or one outside the five canonical ones, an order line whose product is missing from the
products, a target month that isn't the first of a month, a target category missing from the products). The
non-loaded query `_DataQualityIssues` lists every defect the ETL scrubbed, mapped or flagged, one row per
cell, with its original value: 834 rows for this seed (600 number junk, 200 missing ship dates, 12 early
shipments, 22 orphan-customer lines). Junk in `products.list_price` or `customers.signup_date` would be
listed there too; this seed has none.

The report has three pages: **Executive Overview**, **Product Breakdown** and **Target Variance**. It opens
on 2025, the Year slicer stays in sync across pages, and the Revenue YoY % card needs a single year selected.
Target Variance filters only by year and category, because targets exist only per month and category. Every
yearly category total misses its target, so the page's month × category grid is where the beats show.

## Regenerating

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r demo/requirements.txt   # Windows
# .venv/bin/python -m pip install -r demo/requirements.txt      # macOS / Linux
.venv/Scripts/python demo/generate_data.py                      # writes demo/data/
.venv/Scripts/python -m pytest -q                               # from the repo root
```

`generate_data.py` takes `--seed` (default `20230101`) and `--out` (default `demo/data/`). The same seed
always produces byte-identical files: the script never reads the clock, and every random draw comes from
seeded numpy and Faker streams. That only holds for the exact versions pinned in `requirements.txt`, since
Faker's providers and numpy's distributions can change between releases. The pins were verified on
Python 3.14; older Pythons may not have a wheel for the pinned numpy.

A different seed gives different data with the same structure and the same defect counts, except for the
row count of `orders.csv` and the orphan line count, which depend on the draw. The tests check the
committed files, so after a regeneration that changes them, update the counts here and in
`tests/test_demo_data.py` together.

The CSVs are stored with LF endings regardless of `core.autocrlf` (see `.gitattributes`), because the
determinism test compares them byte-for-byte.
