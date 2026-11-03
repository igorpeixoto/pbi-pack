---
name: power-bi-visuals
description: >
  Adds, binds, positions, and manages visuals in Power BI PBIR report pages, including organizing
  them into named Selection-pane visual groups. Invoke whenever a chart, card, KPI, table, matrix,
  slicer, textbox, or button is added or edited; a field or measure is bound to a visual; visuals
  are moved, resized, or aligned to a grid; or visuals are grouped by functional zone.
---

# Power BI Visuals Skill

> **Authoring Policy (see `power-bi-dev`).** Edit `visual.json` files directly in `pages/<pageId>/visuals/<visualId>/visual.json`.

> **Layout Selection:** Ask the user (`AskUserQuestion`) before positioning visuals on a page, selecting a standard layout template ("Top Navigation Bar" or "Sidebar Navigation").

---

## Visual File Structure (`visual.json`)

```json
{
  "$schema": "<copy verbatim from a sibling visual.json in this report — Hard Rule #10>",
  "name": "Visual_KPI_TotalSales",
  "position": {
    "x": 20,
    "y": 100,
    "z": 0,
    "width": 300,
    "height": 150
  },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "_Measures" } },
                  "Property": "Total Sales"
                }
              },
              "queryRef": "_Measures.Total Sales"
            }
          ]
        }
      }
    }
  }
}
```

---

## Visual Groups (Selection Pane Organization)

> **Mandatory (see `power-bi-dev` Stage 5 exit criteria).** Every page's visuals are organized into named groups — never left as a flat list. Groups are the folders visible in the Desktop **Selection pane** (View ➔ Selection).

A group is itself a `visual.json` with **no** `"visual"` key — it carries a `"visualGroup"` object instead. Regular visuals, and nested sub-groups, point at it via a `"parentGroupName"` field holding the group's `name`.

**Group container** (`pages/<pageId>/visuals/<groupId>/visual.json`) — note the `$schema` version must match whatever the rest of the project's visual.json files use (per Hard Rule #10, never hand-type it; copy it from a sibling file):
```json
{
  "$schema": "<copy verbatim from a sibling visual.json in this report — Hard Rule #10>",
  "name": "<groupId>",
  "position": { "x": 0, "y": 0, "z": 2000, "width": 1876, "height": 70, "tabOrder": 5008 },
  "visualGroup": {
    "displayName": "FILTERS",
    "groupMode": "ScaleMode"
  },
  "parentGroupName": "<optional-parent-group-id>"
}
```

**Child visual pointing at the group** (one extra field on the ordinary visual.json):
```json
{
  "name": "<visualId>",
  "parentGroupName": "<groupId>",
  "position": { "x": 20, "y": 20, "z": 0, "width": 200, "height": 40 },
  "visual": { "visualType": "slicer", "...": "..." }
}
```

**Child coordinates are relative to the group origin, not the canvas** — see CLAUDE.md Hard Rule #23. Author them as `absolute − group origin`, and convert back before checking overlap or page bounds. Writing absolute values renders the visual at origin+position, usually off-page, with no error and a passing `pbi report validate`.

**Nesting:** a group can be a child of another group — give the nested group's own `visual.json` a `parentGroupName` pointing at the parent group's `name`. Real-world example: `FILTERS` (top-level) ➔ `EXTRA FILTERS` (nested inside it) ➔ `FILTER CHARTS` (nested inside that).

**Standard group taxonomy** (translate per the project's artifact language chosen in `power-bi-dev` Stage 1 — English shown here as the reference):

| Group | Purpose |
|---|---|
| `HEADER` | Title bar, logo, page background shapes |
| `NAVIGATION` | Page navigation buttons / tabs |
| `FILTERS` | Slicers, filter buttons |
| `CARDS` | KPI card visuals |
| `CHARTS` | Charts, tables, matrices |
| `FOOTER` | Footer text, source notes, page numbers |

These six are the floor, not the ceiling — add domain-specific groups beyond them as the page needs (e.g. `WORK ORDERS`, `BACKLOG` on a maintenance-tracking dashboard).

**Before hand-authoring any group or conditional-formatting JSON**, consult the advisor if it is on (CLAUDE.md §8) with the sibling JSON you intend to mirror and the absolute-vs-relative coordinate math worked out — these are the two PBIR edits that fail silently (Hard Rules 11 and 23). If the advisor is off or declines (after the CLAUDE.md §8 escalation ladder), show the user the intended coordinates as a checkpoint before writing the files.

**Workflow:**
1. Decide the page's functional zones — usually mirrors the layout template chosen in `power-bi-dev`'s Page Layout Selection step.
2. Create one group container `visual.json` per zone (and any nested sub-groups) before placing visuals into it.
3. When adding or moving a visual into a zone, set its `parentGroupName` to that zone's group `name`.
4. Size the group's own `position` block to bound its children's combined footprint — Desktop keeps this in sync automatically once opened in `ScaleMode`, but a hand-authored group must at least roughly enclose its children so the group behaves correctly before the user opens Desktop.

---

## Textbox Fit Check (see CLAUDE.md Hard Rule #15)

A textbox whose text doesn't fit its box renders with an internal scrollbar in Desktop — a defect, since a Power BI textbox never auto-grows or auto-shrinks its font to fit. Before finishing any `textbox` visual (or reviewing one an existing report already has), estimate whether the configured text will fit, using the box's own `position.width`/`position.height` and the run's font size from `visual.objects.general[0].properties.paragraphs[*].textRuns[*].textStyle.fontSize`:

1. **Usable width (px):** `position.width − left padding − right padding` (default padding is ~10px each side if the textbox has no explicit `padding` object).
2. **Characters per line:** `usableWidth / (fontSizePt × 1.333 × 0.55)` — `× 1.333` converts pt→px, `× 0.55` is the average glyph-width-to-font-size ratio for typical UI fonts (Segoe UI and similar). Treat this as a heuristic, not a pixel-exact measurement.
3. **Wrapped line count:** `ceil(characterCount / charactersPerLine)` per paragraph/run, plus one extra line per explicit line break in the text.
4. **Required height (px):** `wrappedLineCount × fontSizePt × 1.333 × 1.2` (the `× 1.2` is standard line-height) — sum across all paragraphs/runs in the textbox, plus top/bottom padding.
5. **Flag overflow** when required height exceeds `position.height` (or required single-line width exceeds `position.width` for text with `wordWrap` disabled). If flagged, do one of: grow `position.height`/`width`, reduce `fontSize`, or shorten the text — then re-run the estimate. Don't leave a flagged textbox for the user to discover the scrollbar in Desktop.
6. This is a heuristic pre-check, not a substitute for the Hard Rule #18 Validation Gate — actual text rendering (font substitution, kerning, DPI scaling) can still differ slightly; always eyeball textboxes in Desktop before commit, especially ones close to the threshold.

---

## Chart Form Selection (built-in `dataviz`)

Before deciding **which visual type** answers a question — and before laying out a KPI row or a card strip —
load the built-in **`dataviz`** skill and apply its form heuristic. `power-bi-themes` loads the same skill for
the *color* half (palettes, sequential/diverging scales, contrast validation); this is the *form* half for
report visuals. `power-bi-visual-dev` and the `pbiviz-starter` governance also load it, for custom visuals.

**What transfers:** the mark-vs-question heuristic (when a bar beats a line, when a single number beats a
chart, when a share-of-total genuinely warrants a pie), stat-tile and KPI-row composition, legend and axis
legibility rules, and the ordering/labelling conventions that make a page read as one system.

**What does not:** `dataviz` assumes *you* render the chart — inline SVG, matplotlib, Recharts. Power BI
renders its own visuals, so its mark specs, tooltip wiring, and DOM-level guidance have no target here. Take
the judgment about *which* form to use; ignore the how-to-draw-it half.

**Cost:** one file read, no fan-out — this is standing policy for Stage 5, not something to ration.

---

## Key Best Practices

- **Copy Sibling Visuals:** When creating a new visual JSON, mirror an existing working visual of the same type in the repository. `pbi-starter/templates/demo/Template-DEMO.Report/` has cards, line and bar charts, a scatter, a matrix, a table, dropdown slicers, a page navigator and visual groups; its Target Variance grid (`pages/753afd7a019ab4f99ec5/visuals/d4aeb9ce8536e7c38b3d/visual.json`) holds a Desktop-authored diverging conditional format.
- **No sibling of that type? Check the demo template, then the catalog.** The demo template's gallery pages (`pbi-starter/templates/demo/`) have a styled, working example of 41 built-in visual types on a star-schema model, with titles as textboxes and every visual in a group.
- **Still nothing? Use the catalog.** [`references/visual-catalog/README.md`](references/visual-catalog/README.md) indexes one working `visual.json` per visual type and per feature (conditional formats, button actions, small multiples, reference lines, visual calculations, field parameters, tooltip pages), taken from Microsoft's sample report. Read only the file you need, before writing that JSON, and change only entity, property, literal and position. Prefer a sibling in the same report when one exists, because it already carries that report's styling and `$schema`.
- **Reference Measures & Columns accurately:** Match exact table and measure names (e.g. `_Measures.Total Sales`).
- **Align Position Grids:** Keep X, Y, width, and height values aligned to grid intervals (e.g. 10px / 20px padding) for clean report visual layouts.
