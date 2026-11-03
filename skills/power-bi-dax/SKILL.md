---
name: power-bi-dax
description: >
  Writes DAX measures (authored in TMDL) and executes and optimizes DAX queries via pbi-cli for Power BI semantic models.
  Invoke whenever DAX, measure creation, EVALUATE, SUMMARIZECOLUMNS, CALCULATE, time
  intelligence, or querying/validating data in a Power BI model is needed. Contains critical guidance on multi-line DAX via CLI.
---

# Power BI DAX Skill

> **CLI Policy (see `power-bi-dev`).** The CLI is used **exclusively for data profiling and result validation** via **`pbi dax execute --file`** (always `--file` for UTF-8 stability; inline `-e` collapses line breaks). **Measures and columns are authored by editing TMDL files** (`_Measures` table and `tables/*.tmdl`), **never** via `pbi measure create`.

> **Standard Flow (see `power-bi-dev`).** Serves Stage 2 (Source Analysis / Profiling) and Stage 4 (Modeling & DAX Measures). Deterministic row-by-row logic (flags, casts, normalization) belongs in **M (Stage 3 / `power-bi-partitions`)**, not in DAX calculated columns.

---

## Prerequisites (see `power-bi-dev` §4)

Run `pbi --version` before this session's first CLI call and install **only if it fails** — `power-bi-dev` §4 holds the single guarded check, the install sequence, and the PATH-failure notice. Never run a blind `pipx install`. Once the CLI answers, `pbi connect` to the model open in Desktop.

---

## Executing DAX Queries (Profiling & Validation)

Use `EVALUATE` queries to profile raw data (Stage 2) and validate measure outputs (Stage 4). Always prefer `--file` with `.dax` files for reliable execution.

```bash
# Recommended: execute query from .dax file
pbi dax execute --file query.dax

# Inline query (single-line only, no accents)
pbi dax execute "EVALUATE TOPN(10, fSales)"

# Execution options
pbi dax execute --file query.dax --max-rows 100
pbi dax execute --file query.dax --timeout 300
pbi --json dax execute --file query.dax
```

### Unloaded Sources
Profiling via DAX requires the table to exist in the model. If a raw table is not yet loaded, create a minimal TMDL partition (source + navigation only, no ETL transformations), reopen the `.pbip`, connect, and profile the raw data as delivered.

---

## Multi-Line DAX Queries: Use `--file`

Inline `-e` collapses line breaks, breaking multi-line DAX queries containing `VAR`/`RETURN`. Write all multi-line queries into a `.dax` file and execute via `--file`:

```bash
echo 'EVALUATE
ROW(
    "Total Sales", VAR _s = SUM(fSales[Revenue]) RETURN _s
)' > query.dax
pbi dax execute --file query.dax
```

---

## Validating Queries & Clearing Cache

```bash
pbi dax validate --file query.dax
pbi dax clear-cache    # Clear Formula Engine cache before timing tests
```

---

## Authoring Measures in TMDL

Measures belong **always in the dedicated `_Measures` table** and are authored by editing TMDL files. Group measures in `displayFolder` following the suggested numbered taxonomy in `power-bi-modeling` (e.g. `02 - Period` for time intelligence, `03 - KPIs` for headline measures) so the Fields pane sorts in a deliberate order, not just alphabetically by business domain.

### Business Rule Documentation on Every Measure

Every measure documents the business logic behind its calculation in two places:

1. **Inline comment `//`** on the first line of the DAX expression (version-controlled in TMDL/git).
2. **Description `///`** above the `measure` declaration (appears as a tooltip in Power BI Desktop UI).

> Write the description in the **Project Artifact Language** selected during Stage 1 alignment (e.g., English or Portuguese).

```tmdl
table _Measures

	/// Gross revenue from all completed sales, excluding tax deductions.
	measure 'Total Sales' =
			// Gross revenue from all completed sales, excluding tax deductions.
			SUM ( fSales[Revenue] )
		formatString: "$ #,##0"
		displayFolder: 03 - KPIs
		lineageTag: <unique-guid>

	/// Gross Margin % = (Revenue - Cost) / Revenue.
	measure 'Margin %' =
			// Gross Margin % = (Revenue - Cost) / Revenue.
			VAR _revenue = SUM ( fSales[Revenue] )
			VAR _cost = SUM ( fSales[Cost] )
			RETURN
				DIVIDE ( _revenue - _cost, _revenue )
		formatString: "0.0%"
		displayFolder: 03 - KPIs\Margin
		lineageTag: <unique-guid>

	/// YoY Growth = (Current - Prior Year) / Prior Year.
	measure 'YoY Growth %' =
			// YoY Growth = (Current - Prior Year) / Prior Year.
			VAR _current = [Total Sales]
			VAR _priorYear = [Total Sales PY]
			RETURN
				DIVIDE ( _current - _priorYear, _priorYear )
		formatString: "0.0%"
		displayFolder: 02 - Period
		lineageTag: <unique-guid>
```

---

## Time Intelligence Standard Patterns

Calendar table convention: `dCalendar` (or `dim_Date`), date column `dCalendar[Date]`. Replace `[Total Sales]` with your base measure.

```tmdl
table _Measures

	/// Year-to-Date sum of [Total Sales] from Jan 1st to current context date.
	measure 'Total Sales YTD' =
			// Year-to-Date sum of [Total Sales] from Jan 1st to current context date.
			TOTALYTD ( [Total Sales], dCalendar[Date] )
		displayFolder: 02 - Period
		lineageTag: <unique-guid>

	/// Prior Year sum of [Total Sales] for the same period last year.
	measure 'Total Sales PY' =
			// Prior Year sum of [Total Sales] for the same period last year.
			CALCULATE ( [Total Sales], SAMEPERIODLASTYEAR ( dCalendar[Date] ) )
		displayFolder: 02 - Period
		lineageTag: <unique-guid>

	/// Prior Month sum of [Total Sales] shifted 1 month back.
	measure 'Total Sales PM' =
			// Prior Month sum of [Total Sales] shifted 1 month back.
			CALCULATE ( [Total Sales], DATEADD ( dCalendar[Date], -1, MONTH ) )
		displayFolder: 02 - Period
		lineageTag: <unique-guid>
```

---

## Performance Rules

- **Solve in ETL first:** Materialize flags, normalizations, and conditional columns in Power Query (M). Simple DAX measures run faster than complex iterative DAX.
