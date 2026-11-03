---
name: power-bi-dev
description: >
  Defines the mandatory development policies for every Power BI project: the 5-stage
  order (scope → source analysis → ETL → modeling → theme/pages/viz), ETL to a star
  schema, pbi CLI for read/validate only, user checkpoints, backup, language and
  versioning rules. IT IS STEP ZERO OF EVERY PROJECT: invoke BEFORE any construction
  skill (power-bi-partitions, -modeling, -dax, -report, -pages, -visuals, -filters,
  -themes, -security) to confirm the current stage and governance.
---

# Power BI Dev — Development Policies

This is a **policy skill**, not a construction skill. It does not edit `.pbip` files or generate documents directly; it establishes rules followed by **all** `power-bi-*` skills.

**When invoked:** confirm which stage the project is currently in, inform the user of current and next steps, and enforce the policies below. If starting a project, Stage 1 (Scope) is a **conversational alignment** — not a formal document. Also run the **Governance Freshness Check** (§5) once per invocation.

---

## 1. Language Policy & Project Artifact Language Alignment

### A. Conversational Response Language
**Always respond in the same language used in the user's prompt** (e.g., if the user prompts in English, reply in English; if in Portuguese, reply in Portuguese). Technical object names (`.pbip`, TMDL syntax, M expressions, DAX functions) remain in their standard technical forms.

### B. Project Artifact Language Alignment (Code, Comments & Metadata)
During Stage 1 (Scope / Kickoff), confirm or ask the user (using `AskUserQuestion`) what language should be used for:
- In-model code comments (`//` in M and DAX)
- DAX measure descriptions (`///`)
- TMDL `displayFolder` names
- Documentation and data dictionaries

Once established (e.g., English or Portuguese), maintain this language consistently across all code comments, measure descriptions, and model metadata throughout the project repository, regardless of the language used in individual chat prompts.

### C. Design-System Template Selection
When kicking off a genuinely **new** project (not when extending an existing one), check `pbi-starter/templates/` for usable templates (a subfolder is usable if it contains a `.pbip` file — skip empty placeholders). If one or more exist, ask the user (`AskUserQuestion`) whether to start from one of them, listing each by name plus a "None — start from scratch" option. If none exist, skip this silently. Either way, also ask the project's name directly (plain question, not a fixed choice) — see `power-bi-themes` for the full move/rename/cleanup instantiation mechanics (chosen template moved to the project root and renamed to that name, `CHANGELOG.md`'s `<PROJECT_NAME>` placeholder filled in, `templates/` folder deleted once the choice is applied). A **full-report template** (`pbi-starter/templates/demo/`, built on the synthetic dataset in `demo/`) is a complete working model and report: Stages 2–4 reduce to setting its parameters (the demo has one, `DataFolder`; see `demo/README.md`) and a green refresh, and Stage 5 starts with filling `assets/brand.json` and running `apply_brand.py` (`power-bi-themes`, "Brand Assets & `apply_brand.py`").

### D. Scope Sign-Off Artifact (built-in `artifact-design`)
Stage 1 itself stays a **conversational alignment** — this does not turn it into a formal document phase. But
when the scope has an audience beyond the person in the chat (several stakeholders, a handed-over meeting
transcript, a KPI list someone else must confirm), **offer** to publish the agreed scope — goals, sources,
KPIs, planned pages, open questions — as an Artifact: load the built-in **`artifact-design`** skill and hand
the user the private link they choose whether to share.

Why here and not later: Stage 1 is the cheapest place in the whole flow to catch a misread requirement. A
wrong KPI definition found at Stage 1 costs a paragraph; found at Stage 4 it costs the ETL and the measures
built on top of it. Cost is one artifact per project — offer it, don't impose it, and never let producing it
delay the move to Stage 2.

---

## 2. Standard Development Flow (Canonical 5-Stage Order)

> **This order is MANDATORY for every new project**, executed **one stage at a time**. Do not skip stages or jump to modeling/viz before completing ETL.

| # | Stage | Executing Skill(s) | Exit Criteria / Output |
|---|-------|----------------------|-------------------|
| 1 | **Scope & Kickoff** | this skill (conversational) | Alignment with user: report goals, available sources, intended KPIs, pages, **Project Artifact Language** selection, and (new projects) **Design-System Template** selection from `pbi-starter/templates/` if any exist. |
| 2 | **Source Analysis** | `power-bi-dax` (profiling) + `power-bi-diagnostics` | Profile tables **as delivered**: real grain, keys, cardinality, distinct counts, ranges, data quality, **key matching**. Defines ETL transformation specs. SQL database sources profiled via their MCP server, installed first if missing (see `power-bi-partitions`). |
| 3 | **ETL (Power Query M)** | `power-bi-partitions` (M) | Shape tables into a **star schema**: separate facts/dimensions, build dimensions (`dCalendar` / `dim_Date`), **normalize spellings**, adjust data types, **materialize flags & deterministic columns in M**, discard unused columns. |
| 4 | **Modeling & DAX** | `power-bi-modeling` + `power-bi-dax` | Relationships (star schema, single-direction filter), `dCalendar` marked as date table, DAX measures with business descriptions (`///`) & line comments (`//`). |
| 5 | **Theme, Pages & Viz** | `power-bi-themes`, `-report`, `-pages`, `-visuals`, `-filters` | Final approved report layer. Every page's visuals organized into named PBIR Visual Groups by functional zone (see `power-bi-visuals`). |

> When RLS or Service publishing is required, it comes **after** Stage 5 as **Stage 6 — Security & Deployment** (`power-bi-security`, `power-bi-deployment`, `power-bi-release`).

---

## 3. Evergreen Premises (Always Enforced)

- **Loaded sources ≠ Ready sources.** Tables brought into `.pbip` are not assumed to be in final shape. Stage 2 profiles them; Stage 3 (ETL) shapes them for the model.
- **SQL Source MCP Prerequisite.** Before Stage 2 profiles a SQL database source, verify (and install if missing) the corresponding MCP server — see `power-bi-partitions` for the mssql-mcp-server reference implementation. Install commands may run automatically; the connection credential itself is always user-owned — Claude never enters, stores, or requests it in chat.
- **ETL is mandatory** (Stage 3), targeting a **star schema**. Even if a source table appears clean, Stage 3 executes — even if only to confirm and record "no transformation required". Never skip ETL to jump straight to DAX modeling.
- **Resolve in ETL (M), not in DAX.** Row-by-row deterministic columns (flags, normalizations, casts, status derivations) are **materialized in Power Query (M)**, not as DAX calculated columns. DAX is reserved strictly for context-dependent aggregations.
- **Design System (`z_*` tables).** Tables prefixed with `z_` store dummy data feeding reference visual styles — either pre-existing from a chosen Stage 1 template (see §1.C) or added later. **Ignore `z_*` tables during Stages 2–4** (do not profile, transform, or model them). Retain them during Stage 5 for visual styling reference, and remove them only after Stage 5 is approved.
- **Page Layout Selection.** Ask the user (`AskUserQuestion`) one page at a time before positioning visuals, selecting standard layouts ("Top Navigation Bar" / "Sidebar Navigation"). For a **new project whose layout is genuinely open** — not for every page, and not when extending an existing report — offer once to mock the layout first as a **Design artifact** (the Artifact tool's design canvas), so the arrangement is settled visually before anyone hand-authors PBIR JSON: rewriting a mockup is cheap, rewriting positioned `visual.json` files is not. Two limits: keep it at **wireframe fidelity** — an HTML canvas does not render like a Power BI visual and must not be shown as a preview of the finished report — and run it **once per project**, since a canvas costs a full artifact generation.
- **Visual Grouping (Selection Pane Organization).** Every page's visuals are organized into named PBIR Visual Groups by functional zone (header, navigation, filters, KPIs/cards, charts, footer), never left as a flat list in the Selection pane. See `power-bi-visuals` for the JSON mechanics and standard group taxonomy.
- **Paused Execution & Git Checkpoints.** Execute **one stage at a time**. Upon completing each stage:
  1. Add a summary line under `[Unreleased]` in `CHANGELOG.md`.
  2. **Quality pass (offer, don't impose).** For stages that produce real logic — Stage 3 (M) above all, then Stage 4 (DAX) — offer to run the built-in **`/code-review`** skill on the M this stage wrote: `/code-review medium <Project>.SemanticModel/definition/expressions.tmdl`, or the specific table files touched — **never the whole `definition/` folder**, which is mostly the TMDL metadata the reviewer is weakest on. A stage's conversation is long by the time the stage ends, so the pass belongs in a fresh session; see **CLAUDE.md Hard Rule #20** for the level, target, and session rules that bind every invocation. Use **`/simplify`** instead when the goal is cleanup only (reuse, dead steps, over-complex expressions) rather than bug-hunting. Two limits to state plainly when offering: it reads **M and TypeScript** well but is thin on TMDL metadata and PBIR JSON — so skip it for Stage 5 output — and a clean pass is **never** a substitute for the Desktop Validation Gate (CLAUDE.md Hard Rule #18), which stays mandatory either way.
  3. **Escalation before the irreversible stage exit (CLAUDE.md §8).** At the **Stage 3 exit**, before committing the fact grain and star design, consult the advisor if it is on — that decision is the one a later fix turns into a MAJOR bump. If the advisor is off, declined, or not attached, climb the CLAUDE.md §8 escalation ladder first, then put the grain decision to the user as an `AskUserQuestion` checkpoint instead. At other stage exits the Desktop refresh is the check; do not spend an advisor call there by default.
  4. Verify Power BI Desktop is closed and commit to Git (e.g., `git commit -m "feat(etl): complete M transformations for fSales"`).
  5. **Notify the user of stage completion and await explicit authorization** before starting the next stage.
- **Release Protocol (`power-bi-release`).** Claude Code can manage release versions upon request or milestone completion: determine version bump (MAJOR/MINOR/PATCH), rename `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`, open a new `[Unreleased]` section, and generate annotated Git tags (`vX.Y.Z`).
- **Backup Policy.** Never automatic or in temp folders. Ask the user (`AskUserQuestion`) before major operations (bulk object deletes, `import-tmdl`, heavy refresh, structural refactoring). Save backups in `<ProjectDir>/backups/<YYYY-MM-DD>_<HHmm>_<reason>/`.

---

## 4. CLI Policy — Read & Validate; Four Named Write Exceptions

> **The `pbi` CLI reads and validates; it does not author.** Reads include `dax execute --file` (Stage 2 source profiling and measure validation) and the inspection commands the sibling skills use (`table list`, `model get`, `database export-tmdl`, `database diff-tmdl`, `report validate`).
>
> **Write commands are limited to four named exceptions**, each owned by one skill. The first three are preceded by the Backup Policy question above:
> - `pbi database import-tmdl` — `power-bi-deployment`, restoring or deploying a TMDL folder.
> - `pbi transaction begin|commit|rollback` — `power-bi-deployment`, wrapping those imports atomically.
> - `pbi visual import-custom` — `power-bi-custom-visuals` / `power-bi-visual-dev`, because a `.pbiviz` is a compiled binary that cannot be hand-edited.
> - `pbi table refresh` — any skill, to load data into the model open in Desktop after a data source or parameter change. It changes no definition, so it needs no backup question unless the refresh is heavy. Save in Desktop to keep the data, and connect to that report's own port when two Desktop windows are open.
>
> Any other write via the CLI (e.g. `pbi measure create`) is out of policy.

**All AUTHORING is performed by directly editing files:**
- **Model / ETL / Measures / Columns / Relationships** → **TMDL** in `*.SemanticModel/definition/`.
- **Pages / Visuals / Filters / Theme** → **PBIR JSON** in `*.Report/definition/`.

**Validation Rhythm:** Edit files ➔ user reopens `.pbip` in Desktop ➔ `pbi connect` ➔ `dax execute --file` to validate. Always execute DAX queries via `--file` (UTF-8).

**CLI Prerequisites Check.** Before the *first* `pbi` invocation in a session, run `pbi --version`. If it fails (command not found / not on PATH):
1. Run the install sequence:
   ```bash
   pip install pipx
   pipx ensurepath
   pipx install pbi-cli-tool
   ```
2. Inform the user that `pbi-cli` was not found and has been installed, and that a new terminal/session may be required for PATH changes to take effect if `pbi --version` still fails afterward.
3. Only then proceed with `pbi connect` and the rest of the stage's work.

---

## 5. Governance Freshness Check (`CLAUDE.md` Sync)

Every project's `CLAUDE.md` is a **point-in-time copy** taken from `pbi-pack/pbi-starter/CLAUDE.md` when the project was created (see the pack's README) — there is no live link after that. The pack's pre-commit hook stamps a `<!-- power-bi-skills-hash: <12-hex-chars> ... -->` line right after `<!-- BEGIN power-bi-skills -->` every time the canonical `CLAUDE.md` changes, so any copy can tell whether it's behind the canonical version **without needing network access** — the hash is compared against the pack repo on the same machine.

The `SessionStart` hook installed by `scripts/install-pbi-sync.sh` already performs steps 1–2 deterministically and prints exactly one `governance:` line: *matches the pack* → step 3; *behind the pack* or *no hash line* → step 4. No line at all means the hook is not installed on this machine — only then run the manual comparison.

**Run once per Step Zero invocation** (not on every message):

1. **Locate the pack:** default `C:\dev\pbi-pack\CLAUDE.md` — a local, unsynced path by design (Hard Rule 22: no Claude tooling in a OneDrive folder, and the pack is tooling). It is deliberately not derived from the user's profile directory: a home-relative path would have to run through `OneDrive\`, which is the thing being avoided. On any machine where that path doesn't hold, set the `PBI_PACK_HOME` environment variable and read `$PBI_PACK_HOME/CLAUDE.md` instead — that variable, not a naming convention, is the cross-machine mechanism. If the current project's own `CLAUDE.md` *is* that file (i.e. you're working inside the pack repo itself), skip this check entirely. If neither exists at all, skip silently — never block work over an unreachable canonical source.
2. **Compare hashes:** read the `power-bi-skills-hash` value from the project's `CLAUDE.md` and from the canonical one. A project file predating this scheme (no hash line at all) counts as unconditionally stale.
3. **Match →** say nothing, continue with the rest of Step Zero.
4. **Mismatch →** tell the user this project's governance block is behind the pack's canonical version. Point them at the pack's `CHANGELOG.md` (`[Unreleased]` plus the most recent release heading) for what changed, and ask (`AskUserQuestion`) whether to update now.
5. **If yes:** read the canonical file's content between `<!-- BEGIN power-bi-skills -->` and `<!-- END power-bi-skills -->` (inclusive — this carries the correct hash line along with it), and replace exactly that span in the project's `CLAUDE.md` with it. Never touch anything before `BEGIN` or after `END` — that's where project-specific additions (if any) live, and they must survive the update untouched.
