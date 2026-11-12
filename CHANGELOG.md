# Changelog — pbi-pack

One version heading per release, one line per change. Release steps in `RELEASING.md`.
Claude Code / Developer: when committing a change to `CLAUDE.md`, `skills/`, or the `pbi-starter/` / `pbiviz-starter/` kits, add a line under `[Unreleased]`.

This tracks the pack itself, not a Power BI project — `pbi-starter/CHANGELOG.md` and `pbiviz-starter/CHANGELOG.md` are the pristine per-repo templates new projects and new custom visuals get instead.

## [Unreleased]

- Added `skills/power-bi-dev/scripts/pbi_map.py`: generates `docs/model-map.md` (tables, columns, measures by `displayFolder` with line numbers, relationships, shared M expressions) and `docs/report-map.md` (pages ➔ groups ➔ visuals with absolute positions and bound fields, off-page visuals flagged per Hard Rule 23), so a session reads a few KB instead of the `definition/` folders. `CLAUDE.md` §3 makes the maps the first read, `pbi-starter/.gitignore` ignores them, and `tests/test_pbi_map.py` runs the generator on the demo template and on a group child written with absolute coordinates
- Added `docs/STATE.md` (template in `pbi-starter/docs/`) and `power-bi-dev` §6: stage, decisions and open checkpoints live in a file, each stage checkpoint updates it and recommends `/clear`. `CLAUDE.md` gained a *Compact instructions* section saying what a compaction must keep
- The `SessionStart` hook now also runs on `clear` and `compact`, where it prints only the project state (`docs/STATE.md`, whether the maps are current, and after a compaction what is uncommitted); `install-pbi-sync.sh` widens an existing `startup|resume` matcher
- `.claude/settings.json` (and its `pbi-starter/` copy) denies `Read` on `**/definition/cultures/**` and `**/.pbi/cache.abf`
- `sync-user-settings.sh` manages `env` variable by variable, like the permission lists, so a machine's own environment variables survive a sync of a `user/settings.json` you add
- `docs/using-the-pack.md`: a *Context & token discipline* section, with opt-in settings for a smaller auto-compact window (`autoCompactWindow`) and a default subagent model; the README's script table and layout follow

## [1.0.1] - 2026-11-03

- README: the delivery-time figure under Results now reads 60–100 hours to about 3 days
- README: Mermaid diagrams of the demo star schema and its Power Query staging flow, sections reordered so the optional Claude Code setup follows the quick start and Contact and License close the page, and the quick start says why Windows is required (Power BI Desktop runs only on Windows)

## [1.0.0] - 2026-11-03

- Governance for Power BI projects (`.pbip`) in `CLAUDE.md`: a canonical 5-stage flow (scope → source analysis → ETL → modeling → theme/pages/visuals), ETL to a star schema, direct TMDL/PBIR authoring, user checkpoints, and numbered Hard Rules with their rationale
- Sixteen `power-bi-*` Claude Code skills covering step zero, DAX, modeling, Power Query partitions, deployment, release, documentation, security, diagnostics, PBIR reports, visuals, pages, themes, filters and custom visuals
- `pbi-starter/`: a starter kit copied into each new report repo (governance copy, changelog and release templates, task template, `.gitattributes` forcing LF so Desktop's CRLF resaves don't pollute diffs, pre-approved read-only `pbi` CLI permissions)
- `pbiviz-starter/` and `power-bi-visual-dev`: separate governance for standalone custom visual repos, with its own 6-stage flow, Visual Validation Gate and consumer-facing Semver, plus a history-preserving procedure for extracting a visual out of a report project, and publisher defaults (author, support contact) that every scaffolded visual carries
- BI-adapted Semantic Versioning and a release protocol: `[Unreleased]` maintained per commit, version headings cut on release, annotated `vX.Y.Z` tags
- Theme tooling in `power-bi-themes`: `apply_brand.py` builds a report theme from a brand file with report-wide visual baselines, and `preview_brand.py` renders a local preview
- Governance freshness: a hash stamped on each governed `CLAUDE.md`, compared from inside every project by a `SessionStart` hook, so a project can tell when its copy is behind the pack
- Git hooks and sync scripts that keep `~/.claude/` (skills, the managed span of the user `CLAUDE.md`, managed settings keys) in step with the pack on every machine, guarded to `main`
- `pbi-sync`: a gated publish from a local working repo to a OneDrive deliverable folder (allowlist staging, tooling leak check, structural and size checks, drift detection, snapshot and rollback), with a reverse pull onto a review branch
- `demo/`: a seeded, byte-reproducible synthetic retail dataset (orders, customers, products, monthly targets) with documented planted defects for the ETL rules to clean, checked by `tests/test_demo_data.py`
- `pbi-starter/templates/demo/`: a demo PBIP template on that dataset. Its Power Query ETL reads the CSVs behind one `DataFolder` parameter, scrubs junk tokens on date and number columns, normalizes status spelling, fails the refresh on broken keys or domains, maps orphan customers to an UNKNOWN member and lists every defect in a non-loaded `_DataQualityIssues` query, into a star of two facts (order lines, monthly category targets) and four dimensions
- Demo template model: single-direction relationships, `dim_date` marked as the date table with sort-by columns, key columns hidden, and a `_Measures` table (Revenue, Cost, Margin, Margin %, Orders, AOV, Revenue PY, Revenue YoY %, Target, Target Variance, Target Variance %) whose Target stays blank below its month × category grain
- Demo template review fixes: staging fails the refresh, naming the offending rows, on values that are neither junk nor valid for their type and on blank keys, order dates, unit costs or revenue targets (so Margin always compares like with like) or a blank status; `_DataQualityIssues` also lists junk in list prices and signup dates; Revenue PY is blank across more than one year, like YoY %; Target Variance % evaluates Target once; measure folders follow the pack taxonomy (`03 - KPIs`, `07 - Targets`); the `DataFolder` parameter metadata is back in Desktop's form
- Demo template model diagram: a classic star, `fact_sales` at the centre with its four dimensions around it, `fact_targets` below `dim_date` beside `dim_category`, `_Measures` on the right edge, with no crossing relationship lines
- Demo report: three pages (Executive Overview, Product Breakdown, Target Variance) under a shared header with a page navigator and a Year slicer synced across pages, a neutral theme built with `apply_brand.py` from the template's `assets/brand.json`, and every visual in named groups; the skills now point at it for working filter, conditional-formatting and visual JSON, and the extra-filters overlay section left `power-bi-themes` with the template it described
- `apply_brand.py`: a report's first custom theme gets the `reportVersionAtImport` Desktop requires (it refused to open the report without it), and the title swap also reaches textbox titles
- Visual reference from Microsoft's MIT-licensed Power BI Visuals sample: a catalog in `power-bi-visuals` (`references/visual-catalog/`) with one working `visual.json` per visual type and feature, the report itself in `reference/power-bi-visuals/` to browse, both without custom visuals; `scripts/build-visual-catalog.py` rebuilds them and `tests/test_visual_catalog.py` guards them; the report copy also drops the page that held only custom visuals and swaps the Power BI logos for a placeholder, and `THIRD-PARTY-NOTICES.md` carries Microsoft's MIT notice
- CLI policy: `pbi table refresh` is a fourth named write exception, for loading data after a data source or parameter change
- README rewritten for a first-time reader: pitch, screenshot, evidence, quick start and contact come first; the full install material moved to `docs/using-the-pack.md`, and the README warns which scripts change `~/.claude/`
- MIT `LICENSE`
- CI (`.github/workflows/ci.yml`): forbidden-term check, gitleaks, shellcheck, ruff, JSON parsing and the data tests; `sync-claude.yml` declares `contents: write`
- `pbi-pull.sh`: report folder and `.pbip` names with spaces no longer break the copy back from OneDrive
- `check-denylist.sh`: a `git grep` error, such as an invalid pattern, now fails the check instead of reading as clean
- `apply_brand.py`: dead code removed, and lint fixes across the theme scripts with no change in behavior
- Demo report: six visual gallery pages (Columns & Bars, Lines & Areas, Part to Whole, Cards & KPIs, Slicers & Buttons, AI, Maps & Gantt) bring it to 41 built-in visual types, with a bookmark navigator, buttons and four kinds of slicer; five helper measures in `08 - Report Visuals`, and invented region coordinates and states on `dim_customer` for the Azure Map and the shape map, which draws without Azure Maps
- `user/settings.json` is no longer shipped: it held one person's settings, including turning off permission prompts. `sync-user-settings.sh` manages the keys of one you add yourself
- Demo template opens with data: its saved model data is committed, `DataFolder` defaults to `C:\src\pbi-pack\demo\data\` instead of a placeholder, a refresh that can't read the folder names the parameter to set, and `tests/test_demo_template.py` fails when the model changes without a re-save
- `.claude/settings.json` (and its `pbi-starter/` copy) no longer pre-approves installing or probing `mssql-mcp-server` and the `SqlServer` PowerShell module; those commands now ask first
- README screenshots of Executive Overview, Product Breakdown and Target Variance re-captured with the nine-page header

<!-- Release protocol: the human or Claude Code renames [Unreleased] to ## [X.Y.Z] - YYYY-MM-DD
     and opens a fresh [Unreleased] above it. Claude Code creates the vX.Y.Z tag — see RELEASING.md. -->

## Version Numbering (Pack Semver)

| Bump  | Criteria                                                                                  |
| ----- | ------------------------------------------------------------------------------------------ |
| MAJOR | A Hard Rule is removed or renumbered in a way that conflicts with projects' existing `CLAUDE.md` copies; a skill is removed, renamed, or its documented contract changes incompatibly |
| MINOR | A new skill, Hard Rule, policy, or starter template is added, without breaking existing ones |
| PATCH | Wording/doc fixes, hook or script bug fixes, clarifications with no behavior change          |
