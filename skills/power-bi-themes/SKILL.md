---
name: power-bi-themes
description: >
  Manages Power BI report themes, custom color palettes, report-wide visual styling defaults, and design
  system reference visuals (z_* tables), including instantiating a new project from a
  pbi-starter/templates/ template and rebranding a report from its assets/ folder with
  apply_brand.py. Invoke whenever theme.json, brand or accent colors, a client brand manual or
  brand guide, logos, dataColors, a categorical/sequential/diverging palette, fonts, visual-level
  styling baselines, assets/brand.json, or choosing a starter template is requested.
---

# Power BI Themes Skill

> **Authoring Policy (see `power-bi-dev`).** Edit theme JSON files directly. Do not use CLI `set-theme` commands as they can write invalid references into `report.json`.

---

## Design System & `z_*` Tables Policy

- **Reference Style Only:** `z_*` tables and reference visuals provide design system styles (fonts, hex palettes, border radius, padding).
- **Stage 5 Usage:** Copy styling configurations from reference visuals onto actual report visuals during Stage 5.
- **Cleanup:** Remove `z_*` reference tables and visuals ONLY after Stage 5 is completed and approved by the user. Never delete `z_*` tables during initial project setup.

---

## Default Visual-Level Styling (see CLAUDE.md Hard Rule #14)

Titles, header icons, and group backgrounds are **OFF by default** for every visual — set once as report-wide baselines in `theme.json`'s `visualStyles`, never hand-toggled per visual. Add this block to the project's theme file (merge into the existing `visualStyles` key if one is already present):

```json
{
  "visualStyles": {
    "*": {
      "*": {
        "title": [{ "show": false }],
        "visualHeader": [
          {
            "show": false,
            "showFilterRestatementButton": false,
            "showOptionsMenu": false,
            "showSeeDataLayoutToggleButton": false,
            "showPinButton": false,
            "showDrillDownExpandButton": false,
            "showDrillDownLevelButton": false,
            "showDrillToggleButton": false,
            "showDrillUpButton": false,
            "showDrillRoleSelector": false,
            "showVisualErrorButton": false,
            "showVisualWarningButton": false,
            "showVisualInformationButton": false
          }
        ]
      }
    },
    "tableEx": { "*": { "visualHeader": [{ "show": true }] } },
    "pivotTable": { "*": { "visualHeader": [{ "show": true }] } },
    "clusteredColumnChart": { "*": { "visualHeader": [{ "show": true }] } },
    "lineStackedColumnComboChart": { "*": { "visualHeader": [{ "show": true }] } },
    "...every other chart type...": { "*": { "visualHeader": [{ "show": true }] } },
    "<GanttCustomVisualName>": { "*": { "visualHeader": [{ "show": true }] } },
    "group": { "*": { "background": [{ "show": false }] } }
  }
}
```

- **Why tables, matrices and charts stay ON:** `tableEx` (table) and `pivotTable` (matrix) header icons expose sort/filter/"see data" affordances users actually need on dense tabular visuals; chart header icons carry focus mode, drill and "see data"; the Gantt and `comboMatrixVisual` custom visuals' header icons are similarly functional (drill/expand), not decorative. The full chart list lives in `scripts/theme.base.json` and `HEADER_ON` in `scripts/apply_brand.py` — use the tool rather than retyping it.
- **`<GanttCustomVisualName>`:** replace with the imported Gantt custom visual's actual registered `visualType` string (visible in its `visual.json` `"visual".."visualType"` once placed on a page, or in the `.pbiviz` `pbiviz.json`/`capabilities.json` — see `power-bi-custom-visuals`). Do not invent a placeholder value in a real project's theme file.
- **`group`** is the visual-container-group type (Selection Pane folders, see `power-bi-visuals`) — this is what turns off the background behind a folder of grouped visuals, independent of any individual visual's own background.
- **Verification is mandatory, not optional:** theme `visualStyles` cascades to every visual that doesn't carry its own conflicting `visualContainerObjects` override — but Power BI Desktop is known to hardcode a per-visual override the moment a user touches a property in the Format pane (existing `tableEx`/`pivotTable` visuals often already carry explicit `title`/`background` blocks). Per Hard Rule #18 (Validation Gate), open the theme in Desktop and confirm the defaults actually rendered before committing; if a specific visual still shows its header/title/background, copy the `show: false` block from a sibling visual's `visualContainerObjects` onto it directly, same as any other reference-visual styling copy.
- **User-requested exceptions** (e.g. a title the user explicitly wants visible on one card) are set via that one visual's own `visualContainerObjects.title`, never by carving a new exception into the theme's `*` catch-all.

---

## Color Palette Construction (built-in `dataviz`)

Before choosing or extending a theme's `dataColors`, `good`/`bad`/`neutral`, or any sequential/diverging scale, load the built-in **`dataviz`** skill. It carries a validated palette formula plus a runnable contrast check, and its `references/palette.md` values transfer directly into `theme.json`.

**What transfers here:** the categorical-palette construction method, sequential and diverging scale construction, and the contrast/accessibility validator. The same skill's *form* heuristic — which mark actually fits the question being asked — is owned by `power-bi-visuals`, not repeated here.

**What does not:** `dataviz` assumes *you* render the chart — inline SVG, matplotlib, Recharts. Power BI renders its own visuals, so its mark specs, tooltip/interaction rules, and DOM-level guidance have no target here. Take the color science and the form heuristic; ignore the rendering half.

**Where it lands:** the palette becomes `dataColors` in the project `theme.json`, and the good/bad/neutral triad drives conditional formatting rules — which per CLAUDE.md Hard Rule #11 are GUI work: author them in Desktop, and where JSON is unavoidable mirror a working sibling visual's CF block rather than inventing one (`power-bi-visuals`' catalog has `features/cf-gradient.json`, `cf-rules.json` and `cf-measure-color.json`).

---

## Template Selection & Instantiation (see `power-bi-dev` §1.C)

When a new project starts from a `pbi-starter/templates/<name>/` design-system template, instantiate it by **moving and renaming**, not by re-authoring content — and never leave it looking like a template afterward:

1. **Ask which template** (`AskUserQuestion`, per `power-bi-dev` §1.C) — or "None — start from scratch."
2. **Ask the project's name directly** (plain question, not `AskUserQuestion` — this is free text, not a fixed choice list): *"What should this project be called?"* (e.g. `ClientX_Vendas`). Everything below uses that answer as `<ProjectName>` — never leave the project called `Template-<NAME>`.
3. **If a template was chosen, move it out of `templates/` to the project root** (the same level as `CLAUDE.md`/`CHANGELOG.md`, not nested under `templates/` anymore), renaming each of the three top-level items in the same move:
   - `templates/<name>/Template-<NAME>.pbip` → `<ProjectName>.pbip`
   - `templates/<name>/Template-<NAME>.Report/` → `<ProjectName>.Report/`
   - `templates/<name>/Template-<NAME>.SemanticModel/` → `<ProjectName>.SemanticModel/`
4. **Edit exactly these 4 files** to point at the new names — a narrow, mechanical exception to Hard Rule #3 (never invent wrapper files): this is renaming an already Desktop-generated template, not authoring new wrapper content.
   - `<ProjectName>.pbip` → `artifacts[0].report.path` = `"<ProjectName>.Report"`
   - `<ProjectName>.Report/definition.pbir` → `datasetReference.byPath.path` = `"../<ProjectName>.SemanticModel"`
   - `<ProjectName>.Report/.platform` → `metadata.displayName` = `"<ProjectName>"`
   - `<ProjectName>.SemanticModel/.platform` → `metadata.displayName` = `"<ProjectName>"`
5. **Replace the `<PROJECT_NAME>` placeholder in `CHANGELOG.md`'s header** with the same `<ProjectName>` — same stale-placeholder problem, same fix, while the name is fresh in hand.
6. **If the chosen template has an `assets/` folder, move it to the project root as `assets/`** (same move as step 3, before step 7 deletes `templates/`). It is the brand input for `apply_brand.py` — see **Brand Assets & `apply_brand.py`** below — and it never publishes (`pbi-publish` builds from an allowlist that does not include it).
7. **Delete the `templates/` folder entirely** — whether a template was chosen or not, its scaffolding job is done; a real project has no business shipping unused `Template-*` folders (or an empty selection folder) alongside the real one.
8. **Leave everything else untouched** — `logicalId`s, `lineageTag`s, TMDL/PBIR content, table/measure names. This is a rename, not new authoring; the user opens the renamed `.pbip` in Desktop next to confirm it loads.
9. **Full-report templates** are a complete working report, not a design-system reference: there are no `z_*` tables, and Stages 2–4 of `power-bi-dev` reduce to setting the template's parameters and a green refresh (the demo's only parameter is `DataFolder`, set as `demo/README.md` explains; `apply_brand.py` sets `Project_PK` and `Schema` from `parameters` in `assets/brand.json` for a template that has them). Fill `assets/brand.json` (below), run `apply_brand.py`, then validate in Desktop.
10. For design-system templates, the template's `z_*` tables, pages, and theme become this project's design-system reference under the policy above (ignore during Stages 2–4, use in Stage 5, remove only after Stage 5 approval).

---

## Brand Assets & `apply_brand.py`

Every project built from a full-report template carries an `assets/` folder at its root — the brand **input**, read by `scripts/apply_brand.py` (one canonical copy here; never copy it into a project). Nothing in `assets/` publishes: the report's own copies live in `StaticResources/RegisteredResources/`.

```
assets/
  brand.json           what the report SHOULD look like — edit this
  brand.applied.json   what the report CURRENTLY contains — written by the tool, never by hand
                       (except once, to bootstrap a project that predates the tool)
  logos/client_logo.*  header logo — the light/"reverse" version: the header bar is a brand color.
                       No all-white variant and the user wants one: scripts/png_mono.py (records
                       the modification in source.logo_note — brand guides usually forbid it)
  logos/partner_logo.* the consultancy/partner logo
  plant.*              optional: background image for a diagram page (e.g. a process flow)
  theme.override.json  optional: a Power BI theme the client supplied, used verbatim
  theme.base.json      optional: project-specific tokenized base (default: scripts/theme.base.json)
  README.md            the command cheat sheet (PowerShell + Git Bash) - keep it in every project
  reference/           optional: notes, screenshots, downloaded logo variants
```

**Run:** `python ~/.claude/skills/power-bi-themes/scripts/apply_brand.py <project-root> [--dry-run] [--preview]` — Desktop closed. It rebuilds and registers the theme (Hard Rule 14 baselines always enforced), swaps logos by slot and repoints every visual (image scaling set to *Fit*), swaps the hard-coded literal colors (values only — conditional-formatting structure is never touched, Hard Rule 11), replaces the header title, sets `Project_PK`/`Schema`, and warns on fill/text pairs below WCAG AA. Then `pbi report validate`, the Desktop Validation Gate (Hard Rule 18), and a changelog line.

### Previewing without Desktop — `preview_brand.py`

`--preview` (or `python .../scripts/preview_brand.py <project-root>` on its own) writes `assets/preview.html`: a static page, no server, git-ignored and never published. Open it in the browser or VS Code's Simple Browser / Live Preview (which reloads on every rewrite). It only reads files, so it is safe while Desktop is open.

- **Drawn faithfully:** every page at its canvas size, shapes / buttons / nav / header / dividers in the resolved theme colors (ThemeDataColor ids + tint/shade), logos and images, header title and button text, textboxes, slicer headers, visual-group offsets (Hard Rule 23), hidden visuals, layer order, any SVG progress bars from `_Brand_*`, the palette by role and the contrast table. `#page=<n>` in the URL picks a page. A report with a hidden `EXTRA FILTERS` overlay group also gets an **Extra filters open** toggle (or `#extras`) that shows it open.
- **Not drawn:** data, charts, slicer values, conditional formatting, exact font metrics — charts and tables are outlined boxes with their type and series colors.
- **Use it for the brand loop** (edit `brand.json` → run → look), then do the Desktop Validation Gate once (Hard Rule 18). It replaces the round-trips, not the gate.

### Filling `brand.json` — pick the route by what the client gave you

Always set `source.kind` and `source.ref`; the next session relies on it to know how firm the palette is.

| Client gave you | `source.kind` | How to fill it |
|---|---|---|
| A brand manual (web page / PDF) | `manual` | Read it (`WebFetch` — load it via `ToolSearch` first), take colors by role, fonts, and the reverse logo. Store the URL, not the manual. |
| A Power BI theme file | `client theme` | Save it as `assets/theme.override.json`; `colors` still needs `primary`/`secondary`/`accent`/`text` for the contrast check and the nav roles. |
| Nothing | `improvised` | Derive from the client's website styles and logo (needs `pip install Pillow` for logo pixel sampling), validate with the built-in `dataviz` contrast check, and tell the user the palette is provisional. |

**Roles map to theme color positions** — visuals reference theme colors through `ThemeDataColor` ids, and Power BI numbers them **id 0 = theme `background`, id 1 = theme `foreground`, id n ≥ 2 = `dataColors[n − 2]`**. Place colors by role, not by taste:

| Theme slot (visual id) | Role (`colors.*`) | Where the demo template uses it |
|---|---|---|
| `background` (id 0) | `surface` | inactive nav tabs, cards, charts, tables, slicer boxes |
| `foreground` (id 1) | `text` | inactive nav tab text, labels, table text |
| `dataColors[0]` (id 2) | `primary` | current-page nav tab, first chart series, single-hue bars, card values, table total row |
| `dataColors[1]` (id 3) | `secondary` | second chart series (the gray Revenue PY and Target context lines) |
| `dataColors[2]` (id 4) | `accent` | not used; third series if a chart ever has one |
| `dataColors[3]` (id 5) | `neutral_dark` | not used; fourth series if a chart ever has one |
| `dataColors[5]` (id 7) | `header` | header bar; table and matrix column headers take the same color through `table_header` |
| `dataColors[7]` (id 9) | `neutral_mid` | not used |
| `dataColors[4]`, `[6]`, `[8]`, `[9]`, then 10+ | `series[]` | not used: no demo chart has more than two series (at least 4 are still required) |

Power BI assigns chart series by `dataColors` position, so a chart's third and fourth series get `accent` and `neutral_dark`. Validate the array in that order with the `dataviz` check before a chart goes past two series.

**DAX that draws its own colors** (an SVG progress bar on a card, for example; the demo has none) reads them from hidden text measures `_Brand_<role>` (display folder `_Brand`) — `_Brand_progress_start`, `_Brand_progress_end`, `_Brand_progress_track`, defaulting to a darker `secondary` → `secondary` over `accent`. The tool rewrites every `measure _Brand_<role> = "rgb(…)"` line from `colors.<role>`; to brand another DAX-drawn color, add a `_Brand_<role>` measure the same way and reference it instead of a literal.

Other roles (`page`, `row_alt`, `border`, `surface`, `on_dark`, `table_header`, `text_muted`, `good`, `bad`, …) have derived defaults — set them only when the brand specifies them. `fonts.report` must be a Power BI font (the tool lists them on error); keep the real brand font in `fonts.brand`. `literals` names the hex values typed directly into visuals — the template's `brand.applied.json` lists the known ones; add a slot there (current value) and in `brand.json` (new value) when a new one shows up. `header_icons_on` lists custom visual `visualType`s whose header icons stay ON.

**A project that predates the tool** (e.g. forked from an earlier report before the template existed): write `assets/brand.applied.json` by hand from the report's `report.json` (`themeCollection.customTheme.name`, the `RegisteredResources` image items per slot), the current literal values, and the current header title strings — then run the tool once in `--dry-run` and check every line before the real run. A report with no custom theme yet also needs an empty `RegisteredResources` package in `report.json` and an existing `StaticResources/RegisteredResources/` folder, or the tool stops; start `brand.applied.json` with `theme: null` and empty `logos`, `literals` and `titles`.
