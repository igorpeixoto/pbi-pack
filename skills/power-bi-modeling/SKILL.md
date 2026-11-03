---
name: power-bi-modeling
description: >
  Creates and manages semantic model structures in Power BI using TMDL files — tables, columns,
  measures, relationships, hierarchies, calculation groups, and date/calendar tables. Invoke
  whenever a star schema, table or column definition, relationship or cardinality, displayFolder
  taxonomy, object naming convention (f*/d*/_Measures), or a dCalendar date table is being created
  or changed.
---

# Power BI Modeling Skill

> **CLI Policy (see `power-bi-dev`).** All modeling is authored **directly in TMDL files** in `*.SemanticModel/definition/` (`tables/*.tmdl`, `relationships.tmdl`, `model.tmdl`). The CLI is used **only for reading and validation**:
> - `dax execute --file` — test measures and check query results;
> - `pbi table list` / `pbi measure list` / `pbi relationship list` (with `--json`) — inspect model structure;
> - `pbi database export-tmdl ./model/` — inspect TMDL syntax of existing objects when needed.

> **Standard Flow (see `power-bi-dev`).** Executes **Stage 4 — Modeling & DAX**. Assumes **Stage 3 (ETL)** delivered a star schema in Power Query (M). Do not build row-level transformation logic here — resolve it in M.

> **Design System (`z_*` tables).** Ignore `z_*` tables during modeling. Do not relate, measure, or model `z_*` tables.

---

## Prerequisites (see `power-bi-dev` §4)

Run `pbi --version` before this session's first CLI call and install **only if it fails** — `power-bi-dev` §4 holds the single guarded check, the install sequence, and the PATH-failure notice. Never run a blind `pipx install`. Once the CLI answers, `pbi connect` to the model open in Desktop.

---

## Object Naming Conventions

Apply these prefixes/naming standards when creating model objects:

| Object Type | Prefix / Name Standard | Example |
|-------------|------------------------|---------|
| Fact Table | `fact_` or `f` | `fact_Sales`, `fSales` |
| Dimension Table | `dim_` or `d` | `dim_Customer`, `dCustomer`, `dCalendar` |
| Measures Table (no data, measures only) | `_Measures` | `_Measures` |
| Visual Helper Table | `v` | `vRankingTop10`, `vParameters` |
| Calculation Group | `cg` | `cgTimeIntelligence` |

- **Calendar Table:** Single date dimension named `dCalendar` (or `dim_Date`), with its date column named `Date`.
- **No DAX Auto-Date/Time:** Disable Power BI auto-date/time. Time intelligence uses `dCalendar[Date]`.
- **Measures Table:** All measures live in a dedicated measures table (`_Measures`).
- **Names follow the Project Artifact Language.** The prefixes above are fixed; the words after them, the `displayFolder` names below and the visual-group names in `power-bi-visuals` are written in the language chosen at Stage 1. English is shown throughout; a Portuguese project, for example, uses `fVendas`, `dCalendario[Data]`, `Medidas` and `02 - Período`.

---

## Tables (TMDL Authoring)

Each table is a `tables/<TableName>.tmdl` file referenced in `model.tmdl`.

> Every table has a triple-slash description (`/// ...`) above the `table` declaration explaining its purpose, in the **Project Artifact Language** selected during Stage 1 alignment. Desktop shows it as the table's Fields-pane tooltip.

```tmdl
/// Sales fact table: one row per line item sold.
table fSales
	lineageTag: <unique-guid>

	partition fSales = m
		mode: import
		source = ...   // see power-bi-partitions
```

---

## Columns (TMDL Authoring)

> Every column has a description (`/// ...`) explaining its meaning, for the same tooltip reason.

```tmdl
/// Gross invoiced revenue in local currency.
column Revenue
	dataType: double
	summarizeBy: sum
	sourceColumn: Revenue
	lineageTag: <unique-guid>

/// Gross profit = Revenue - Cost. (Calculated column — only if unable to resolve in M ETL)
column Profit = [Revenue] - [Cost]
	dataType: double
	summarizeBy: sum
	lineageTag: <unique-guid>
```

> **Sort-By Columns are mandatory for any categorical with a natural order** (stage, status, month name, weekday, priority band). Without one, Power BI sorts alphabetically and every axis and slicer reads wrong. Materialize the sort key in M (Stage 3), then bind it in TMDL:
> ```tmdl
> /// Month name, sorted by MonthNum.
> column MonthName
> 	dataType: string
> 	sortByColumn: MonthNum
> 	sourceColumn: MonthName
> 	lineageTag: <unique-guid>
> ```
> The sort column must be at the same grain (one value per category value) or Desktop refuses the binding.

> **Map Location Columns:** Geographic columns for map visuals MUST include `dataCategory: Place` (or `City`, `StateOrProvince`, `Country`). Format location strings in Power Query (M) prior to loading.

---

## Measures (TMDL Authoring)

All measures MUST live in the dedicated measures table (`_Measures`), organized into `displayFolder` paths.

### `displayFolder` Taxonomy (Suggested Baseline)

Power BI sorts `displayFolder`s alphabetically in the Fields pane, not by creation order — prefix each top-level folder with a zero-padded number to control the order the user actually sees:

| Folder | Purpose |
|---|---|
| `00 - Selection` | Parameter / what-if / selected-value measures (field parameters, disconnected slicer helpers) |
| `01 - Base` | Foundational/atomic aggregations other measures build on — not bound directly to a visual |
| `02 - Period` | Time-intelligence measures (YTD, MTD, YoY, accumulated, trend) |
| `03 - KPIs` | Headline KPI measures bound directly to cards/visuals |
| `04 - Dates` | Date/calendar helper measures (current-period flags, period labels) |
| `05 - Text` | Dynamic text/label measures (titles, tooltips, dynamic legends) |
| `06 - Helpers` | Technical helper measures (rank, conditional-formatting flags, sort keys) — not meant for direct display |

These seven are the floor, not the ceiling — continue the numbering for domain-specific buckets the project needs (e.g. `07 - Schedule`, `08 - S-Curve` on a project-tracking dashboard). Nested subfolders still use `\` inside a numbered bucket (e.g. `03 - KPIs\Margin`). This is a suggested default, not a Hard Rule — adapt or skip it per project size (a 5-measure dashboard doesn't need 7 folders), but `displayFolder` itself remains mandatory (CLAUDE.md Hard Rule #4).

### Comment + Description on Every Measure

Every measure has an **inline comment `//`** on the first line of the DAX expression and a **description (`///`)** stating the same business rule. The comment travels with the code in git, and the description is the tooltip report authors see.

```tmdl
table _Measures

	/// Gross revenue from all completed sales.
	measure 'Total Sales' =
			// Gross revenue from all completed sales.
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
```

---

## Relationships (TMDL Authoring)

Relationships live in `relationships.tmdl`. Model in a **star schema**: `fromColumn` on the **many** side (fact), `toColumn` on the **one** side (dimension), **single** filter direction (dimension ➔ fact).

```tmdl
relationship <unique-guid>
	fromColumn: fSales.ProductKey
	toColumn: dProduct.ProductKey

relationship <unique-guid>
	fromColumn: fSales.Date
	toColumn: dCalendar.Date
```

> ⚠️ **CRITICAL TMDL RULE: Relationship Blocks Accept NO Comments or Descriptions.**
> Do NOT place `///` or `//` inside or above a `relationship` block. `///` above a relationship generates an invalid `description` property, causing `DataModelLoadFailed`. `//` inside a relationship block causes `InvalidLineType`.
> 
> To document a relationship in TMDL, use a descriptive identifier name instead of a random GUID: `relationship Rel_fSales_dCalendar`.

---

## Star Schema Best Practices

1. **Facts (`f*`) on many side, Dimensions (`d*`) on one side.** 1:N dimension ➔ fact.
2. **Single filter direction (dimension ➔ fact).** Avoid bidirectional (`bothDirections`) or many-to-many relationships unless explicitly justified.
3. **Avoid snowflakes:** Denormalize dimension hierarchies in Power Query (M) rather than chaining multiple dimension tables.
4. **Single date dimension:** `dCalendar` / `dim_Date` with a `Date` column.
5. **Sort-by columns** on every categorical with a natural order (see Columns above).
6. **Always validate:** Reopen `.pbip` in Desktop, refresh, and test via `dax execute --file`.
