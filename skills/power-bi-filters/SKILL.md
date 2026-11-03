---
name: power-bi-filters
description: >
  Manages report-, page-, and visual-level filters in PBIR reports. Invoke whenever a filter,
  slicer, TopN filter ("top 10 customers"), relative-date or date-range filter, categorical
  filter, or a filter scoped to one page or one visual is requested.
---

# Power BI Filters Skill

> **Authoring Policy (see `power-bi-dev`).** Author filters by editing filter arrays in PBIR `page.json` or `visual.json` files directly.

---

## Filter Types & Usage

- **Page-Level Filters:** Applied in `page.json` under `filterConfig.filters[]`. Affects all visuals on that page.
- **Visual-Level Filters:** Applied in `visual.json` under `filterConfig.filters[]` (same shape as page level).
- **TopN Filters:** Use explicit measure references and limit integer counts. The demo's "Top 10 products" chart has a working one: `pbi-starter/templates/demo/Template-DEMO.Report/definition/pages/402b9457eebbd62af1e8/visuals/606fd81726f23e44960b/visual.json`.
- **Date Filters:** Prefer filtering against `dCalendar[Date]` columns.

---

## Filter JSON — Mirror a Sibling, Never Invent (CLAUDE.md Hard Rule 11)

Filter JSON is the same silent-failure territory as conditional formatting: a malformed `Where` clause renders as "no filter", not as an error. Copy the block from a working `page.json`/`visual.json` in **this** repo and change only entity, property and literal. The shape below is a *not-equals* filter in the form Desktop writes, and page and visual levels share it. The demo template's Region chart carries this one (`dim_customer[Region] <> "Unknown"`), in `pbi-starter/templates/demo/Template-DEMO.Report/definition/pages/0dfafc4f7a616cc017e4/visuals/58d5148c8ce1510df57e/visual.json`:

```json
"filterConfig": {
  "filters": [
    {
      "name": "<20-hex-id>",
      "field": { "Column": { "Expression": { "SourceRef": { "Entity": "dim_customer" } }, "Property": "Region" } },
      "type": "Advanced",
      "filter": {
        "Version": 2,
        "From": [ { "Name": "d", "Entity": "dim_customer", "Type": 0 } ],
        "Where": [ { "Condition": { "Not": { "Expression": { "Comparison": {
          "ComparisonKind": 0,
          "Left":  { "Column": { "Expression": { "SourceRef": { "Source": "d" } }, "Property": "Region" } },
          "Right": { "Literal": { "Value": "'Unknown'" } }
        } } } } } ]
      },
      "howCreated": "User"
    }
  ]
}
```

- `ComparisonKind` 0 is equality; wrap in `Not` for not-equals. Other kinds (greater/less) are best copied from a Desktop-authored filter of that kind rather than guessed.
- String literals carry their own single quotes inside the JSON string (`"'Unknown'"`); numbers and dates do not.
- `"type": "Categorical"` filters (multi-select `In`) have a different `Where` shape — again, copy one Desktop wrote. `power-bi-visuals`' catalog has one in `references/visual-catalog/features/filter-categorical.json`, and a page-level one in `features/page-interactions.json`.
- After editing, `pbi report validate` proves the JSON parses, not that the filter applies: confirm in Desktop (Hard Rule 18) by checking the filter pane shows the expected condition.
