---
name: power-bi-visual-dev
description: >
  Development policies for a standalone Power BI custom visual (.pbiviz) repository:
  repo-mode detection, the 6-stage flow, the Visual Validation Gate, governance bootstrap,
  and extracting a custom visual out of a report project into its own repo. IT IS STEP ZERO
  OF EVERY CUSTOM VISUAL REPO: invoke BEFORE power-bi-custom-visuals. Invoke whenever a custom
  visual is to be extracted, split out, moved into its own repository or reused across
  reports; whenever a standalone .pbiviz repo is created; or whenever a visual repo's
  governance, CLAUDE.md, stages, versioning or validation gate is in question.
---

# Power BI Visual Dev — Custom Visual Repository Policies

This is a **policy skill**, not a construction skill. It writes no `src/` code and no `capabilities.json`; it establishes the rules that `power-bi-custom-visuals` and every other skill follow inside a standalone custom-visual repo. It is the `.pbiviz` counterpart of `power-bi-dev`.

**When invoked:** run §1 (Repo Mode Detection) first — it decides whether the answer is a bootstrap, an extraction, or a stage of ordinary work. Then confirm the current stage, tell the user the current and next steps, and enforce §3–§5. Run the **Governance Freshness Check** (§7) once per invocation.

---

## 1. Repo Mode Detection (run first, every invocation)

The same request means different work depending on where it is asked. Detect before acting:

| Signals on disk / in the prompt | Mode | Do this |
|---|---|---|
| `pbiviz.json` at the repo root, `CLAUDE.md` carries `<!-- BEGIN power-bi-visual-skills -->` | **Visual repo, governed** | §7 freshness check, then confirm the stage (§3) and proceed |
| `pbiviz.json` at the root, but no `CLAUDE.md` or a *report* `CLAUDE.md` (`BEGIN power-bi-skills`) | **Visual repo, ungoverned** | §2.C — install governance first, then proceed. A report `CLAUDE.md` here is a defect: it enforces TMDL/PBIR rules that do not apply and omits every rule that does |
| A `.pbip` at the root **and** a visual source folder inside it, and the user asks to separate / extract / split out / move / reuse the visual elsewhere | **Extraction requested** | §2.A — the full extraction procedure |
| No `pbiviz.json` anywhere, user wants a new visual from scratch, unrelated to one specific report | **Greenfield** | §2.B |
| A `.pbip` at the root, user wants a visual *for this report only* | **In-project visual** | Do **not** extract. Stay in the report repo under `power-bi-dev`'s Stage 5, build the visual with `power-bi-custom-visuals`, and mention that §2.A exists for the day it earns its own repo |

Ambiguous between the last two? Ask (`AskUserQuestion`): *"Build it inside this report, or as its own reusable repo from the start?"* — a visual that already has a second consumer in mind is cheaper to start standalone than to extract later.

---

## 2. Bootstrap Paths

The pack lives at `C:\dev\pbi-pack` by default — a local, unsynced path by design (report-governance Hard Rule 22: the pack is Claude tooling and must not sit in a OneDrive folder). Override with `PBI_PACK_HOME` on any machine where that path doesn't hold. Referred to below as `$PACK`.

### A. Extraction — a visual leaves its host report repo

> The visual was built inside a `.pbip` project and is now good enough to reuse. The failure this procedure exists to prevent: an extracted repo that carries the *report's* governance (or none at all), loses the authoring history that explains its shape, and silently keeps assumptions about the one model it grew up in.

Execute **in order**, checkpointing with the user at steps 4 and 7.

1. **Locate and confirm the source.** Find the folder holding `pbiviz.json` inside the host repo (commonly `<VisualName>/`). List what it contains — `src/`, `capabilities.json`, `style/`, `assets/`, `package.json`, `tsconfig.json` — and confirm with the user that this folder is the whole visual. Anything the visual needs that lives *outside* it (a shared `.less`, a helper module, a JSON fixture) must be identified now; it will not come along with a subtree split.

2. **Capture the facts that exist only in the host's context**, before anything moves. These are unrecoverable once the folder is out:
   - `visual.guid` and `visual.version` from `pbiviz.json` — both carried **verbatim** (Hard Rule #1/#2 of the visual governance: the GUID is what binds this visual inside every report that already imports it).
   - The **registered `visualType` string** the host report uses, and any `visualStyles` entry keyed to it in the host `theme.json` (see `power-bi-themes`).
   - The **Project Artifact Language** the host project settled on — the new repo inherits it rather than asking again.
   - Which host tables/measures were bound to which data role, as the reference test case for the validation gate.

3. **Split with history, not with `cp`.** The commit history is the documentation of why the visual is shaped the way it is; a copy-paste extraction throws it away permanently. **Consult the advisor before this step** if it is on (report-governance CLAUDE.md §8): the split and the GUID carry-over are the two irreversible moves of the procedure, and it is the moment the step-2 facts are still verifiable. If the advisor is off or declines (after the report-governance CLAUDE.md §8 escalation ladder), put the step-2 facts to the user as a checkpoint instead. From a clean tree in the host repo:
   ```bash
   git subtree split -P <VisualName> -b visual-extract     # history of that prefix only
   git init ../<VisualName> && cd ../<VisualName>
   git fetch ../<HostRepo> visual-extract
   git checkout -b main FETCH_HEAD                          # files land at the new repo root
   ```
   Then, back in the host repo, `git branch -D visual-extract`.
   **Caveat to check first:** `subtree split` follows one path prefix. If the folder was renamed or moved during development, history before that move will not come across — verify with `git log --follow -- <VisualName>` and tell the user what will be lost. When falling back to a plain copy, record the host repo name and the source commit SHA in the new repo's first commit message, so the lineage stays recoverable by hand.

4. **Install the visual governance — never the host's.** Copy the starter kit in, using the trailing `/.` form so dotfiles come too:
   ```bash
   cp -r "$PACK/pbiviz-starter/." .
   ```
   This brings `CLAUDE.md` (visual governance), `CHANGELOG.md`, `RELEASING.md`, `.gitattributes`, `.gitignore`, `.claude/settings.json`, `docs/tasks/_TEMPLATE.md`. If the extracted folder already had a `.gitignore` or `.claude/settings.json`, **merge** — do not blind-overwrite. If a host `CLAUDE.md` came along in the split, delete it: report governance in a TS repo is worse than none, because it reads as authoritative.
   Then fill the placeholders while the facts from step 2 are in hand:
   - `CHANGELOG.md` header: `<VISUAL_NAME>` → the visual's name.
   - `CHANGELOG.md`: open with a `## [X.Y.Z] - YYYY-MM-DD` heading at the **version the visual already reached in the host** (not `1.0.0` — reports have that binary already, and versions only go up), one line recording the extraction and naming the host project, then a fresh `[Unreleased]` above it.
   - Tag that heading: `git tag -a vX.Y.Z -m "Extracted from <HostProject>"`.
   - Append a **Project Facts** block to `CLAUDE.md` *after* the `<!-- END power-bi-visual-skills -->` marker — Project Artifact Language, host `visualType` string, extraction origin (repo + SHA), and the reference data used to validate. Everything outside those markers survives future governance updates untouched (§7); anything written inside them will be overwritten.
   **Checkpoint:** show the user the new repo's tree and the filled placeholders before continuing.

5. **Run the host-coupling audit.** The visual was written against one model; reuse across reports is the entire premise of the new repo. Grep and report — do not silently fix:
   ```bash
   grep -rnE '#[0-9a-fA-F]{3,8}' src/ style/          # hardcoded colors → Hard Rule #8 (host.colorPalette)
   grep -rn 'toFixed\|toLocaleString\|pt-BR\|en-US'   # hand-rolled formatting → Hard Rule #9 (valueFormatter)
   grep -rn 'values\[[0-9]\]\|categories\[[0-9]\]'    # positional dataView access → fragile role binding
   ```
   Then read `src/` for: host table/measure names appearing as string literals, an assumed number of series or categories, an assumed date grain, user-facing strings hardcoded in one language, and any `update()` path that assumes a non-empty `dataView` (Hard Rule #6). Present the findings as a list with a severity each, and ask which to fix now versus record under `[Unreleased]` as known coupling. **Never** fix them all silently in the extraction commit — a behavior change mixed into a move is unreviewable.

6. **Verify the new repo actually builds and renders**, before anything is deleted anywhere:
   ```bash
   npm install
   pbiviz package                 # must emit dist/<VisualName>.pbiviz
   ```
   Then the full **Visual Validation Gate** (§5) with the host report as the test bed, plus the extraction-specific check: import the freshly built binary into a **copy** of the host `.pbip` and confirm the visual still renders **with its existing field bindings intact**. Bindings survive precisely because the GUID did not change — if they do not survive, the GUID moved and step 2 was not honored.
   ```bash
   pbi visual import-custom ./dist/<VisualName>.pbiviz --replace   # against a BACKED-UP copy
   ```

7. **Only now, clean up the host repo** — and ask before deleting (`AskUserQuestion`):
   - Remove the visual's source folder from the host repo. The compiled `.pbiviz` the report imports is a binary the report already holds; the *source* has moved and a second copy will drift.
   - Add a line to the host's `CHANGELOG.md` under `[Unreleased]` naming the new repo and the version imported.
   - Leave a pointer the next person will actually find: a short block in the host repo's `CLAUDE.md` **after** its `<!-- END power-bi-skills -->` marker (project-specific additions live there and survive governance updates) naming the visual, its new repo path/URL, the imported version, and the re-import command. Without it, the next session finds a `.pbiviz` in the report with no source and re-scaffolds a fork.
   - Commit in the host repo with a message naming the destination.

### B. Greenfield — a standalone visual from scratch

1. Ask the visual's **name** (plain question) and the **Project Artifact Language** (§3.B).
2. `mkdir <VisualName> && cd <VisualName> && git init`, then `cp -r "$PACK/pbiviz-starter/." .`, filling `<VISUAL_NAME>` in `CHANGELOG.md`.
3. Scaffold with `power-bi-custom-visuals` (`pbiviz new`, `npm install`) — into this folder, and reconcile: the scaffold writes its own `.gitignore` and `tsconfig.json`; keep the starter's `.gitignore` and merge anything the scaffold adds.
4. **Convert the scaffolded flat `SimpleCard` to `CompositeCard` + `Group` before adding the second formatting slice** — Hard Rule #3, and the one thing that is expensive to retrofit.
5. Commit the scaffold as its own commit, then proceed to Stage 1 (§3).

### C. Ungoverned visual repo — adopt governance in place

`cp -r "$PACK/pbiviz-starter/." .`, merging rather than overwriting any `.gitignore`, `CHANGELOG.md`, or `.claude/settings.json` that already exists. Delete any report `CLAUDE.md` found here. Then run §5's gate once as a baseline before touching code — adopting the rules is not the same as the code already satisfying them, and the difference should be recorded under `[Unreleased]`, not discovered mid-feature.

---

## 3. Language Policy & Project Artifact Language Alignment

### A. Conversational Response Language
**Always respond in the language of the user's prompt.** Technical names (`pbiviz.json`, `capabilities.json`, TS/D3 API symbols) stay in their standard technical forms.

### B. Project Artifact Language Alignment
At Stage 1 — or inherited from the host project on extraction (§2.A step 2) — confirm or ask (`AskUserQuestion`) the language for TS comments, user-facing strings, `pbiviz.json` `displayName`/`description`, and every `displayName` in the formatting model and `capabilities.json`. Record it in the repo's `CLAUDE.md` Project Facts block so the next session does not re-ask.

### C. Identifiers stay English camelCase, always
Card `name`, group `name`, property `name`, data-role `name`, TS symbols — never translated, in any project. Only `displayName` follows the artifact language. Renaming an identifier after release silently resets every consuming report author's saved settings (visual governance Hard Rule #5), so the artifact-language decision must never reach an identifier.

---

## 4. Standard Development Flow (Canonical 6-Stage Order)

> **Executed one stage at a time.** Stages 2 and 4 define the contract; skipping ahead to rendering means discovering at Stage 4 that a property has to be renamed, which is exactly the move Hard Rule #5 forbids.

| # | Stage | Executing Skill(s) | Exit Criteria / Output |
|---|-------|--------------------|------------------------|
| 1 | **Scope & Contract** | this skill (conversational) | What the visual must show and for whom; the encoding chosen with the built-in **`dataviz`** form heuristic; which data roles it needs and which are optional; **explicitly, what it must NOT assume about the host model**; Project Artifact Language; publisher identity set per `power-bi-custom-visuals` → **Publisher defaults** (on extraction, check the carried-over author and support fields against it). |
| 2 | **Capabilities & Data Roles** | `power-bi-custom-visuals` | `capabilities.json`: `dataRoles`, `dataViewMappings` (with `conditions` min/max so Power BI enforces the contract rather than the code), `objects` skeleton. Role names are final from here on. |
| 3 | **Rendering** | `power-bi-custom-visuals` | `src/visual.ts`: `update()` with explicit degenerate-`dataView` handling, an intentional empty state, resize handling, cleanup between updates, host services for tooltips/selection. Default colors from the **`dataviz`** palette, read through `host.colorPalette`. |
| 4 | **Formatting Pane** | `power-bi-custom-visuals` | `CompositeCard` ➔ `Group` ➔ slices model; every group's properties flattened into one `objects` entry per card, names unique card-wide. |
| 5 | **Build, Review & Package** | `power-bi-custom-visuals` | `pbiviz start` dev loop; **Visual Validation Gate** (§5) passed; `/code-review medium src/` in a fresh session; `pbiviz package` emits the binary. |
| 6 | **Distribute & Import** | `power-bi-release`, then `power-bi-custom-visuals` + `power-bi-themes` | Version bumped in `pbiviz.json` + `CHANGELOG.md` + tag as one number; binary attached to the tag; imported into the consuming report(s); the report's `theme.json` `visualStyles` entry keyed to the registered `visualType`. |

---

## 5. Evergreen Premises (Always Enforced)

- **Host independence is the product.** A visual in its own repo exists to be used by reports it has never seen. Hardcoded field names, assumed series counts, assumed grain, assumed locale, and hardcoded colors are not style issues here — they are functional defects that surface as a broken visual in someone else's report.
- **Contract before code.** `capabilities.json` and the formatting model are the public surface. They are designed at Stages 2 and 4 and then treated as append-only: new properties yes, renames never (Hard Rule #5).
- **Visual Validation Gate replaces the Desktop refresh gate.** A report project has a green refresh to lean on; this repo has nothing equivalent, because a broken visual renders an **empty rectangle rather than an error**. Before any commit touching `src/`, `capabilities.json`, or the formatting model, confirm in a Desktop dev visual (`pbiviz start`): real data · **zero rows** · **null/missing measure** · resize both directions · Format pane shows **grouped** cards with working defaults · colors follow a theme switch. A green `pbiviz package` proves compilation, nothing more. State plainly which of these were actually observed and which were not.
- **Paused Execution & Git Checkpoints.** One stage at a time. On completing each:
  1. Add a summary line under `[Unreleased]` in `CHANGELOG.md`.
  2. **Quality pass.** `src/` is ordinary TypeScript, so the built-in reviewers work here at full strength — unlike TMDL/PBIR, where they are thin. Run **`/code-review medium src/`** before every `pbiviz package` (Stage 5), and **`/simplify`** in its own session after a feature lands for reuse/dead-code cleanup. Bound by the repo's `CLAUDE.md` Hard Rule #16: explicit level, narrow target, fresh session, never both in one session — never the repo root, which drags `node_modules/`, `.api/`, and `dist/` into the pass. A clean pass is **not** a substitute for the validation gate above.
  3. Commit.
  4. **Notify the user of stage completion and await explicit authorization** before the next stage.
- **Release Protocol (`power-bi-release`).** Version bump classification is **visual-adapted**: severity is what breaks in a *consuming report* (see the repo's `CLAUDE.md` §6), not how much code changed. `pbiviz.json` `visual.version`, the `CHANGELOG.md` heading, and the git tag move together, only upward.
- **Backup Policy.** Never automatic, never in temp folders. Before `pbi visual import-custom --replace` against a real report, **ask the user** (`AskUserQuestion`) whether to back up that report's `.pbip` definitions first, and if yes save them to `<ProjectDir>/backups/<YYYY-MM-DD>_<HHmm>_<reason>/` — importing a binary over a live report is the one destructive operation this repo can perform on someone else's project.
- **Out of scope.** AppSource submission, Microsoft certification, org-store administration, tenant Developer Mode, and `pbiviz --install-cert` are **user actions** — prompt, never perform.

---

## 6. Toolchain Prerequisites Check

`powerbi-visuals-tools` is Node-based and entirely separate from `pbi-cli` (pipx). Check before the first `pbiviz` call in a session; install only if the check fails:

```bash
pbiviz --version                     # check first
npm i -g powerbi-visuals-tools        # only if the check fails
```

`pbiviz --install-cert` and enabling Developer Mode are **user actions** — prompt for them and wait; never run the cert install silently, it writes to the OS trust store.

`pbi-cli` is needed **only** at Stage 6, for `pbi visual import-custom`. Do not run `pbi connect` in this repo — there is no semantic model here.

---

## 7. Governance Freshness Check (visual `CLAUDE.md` sync)

Mechanically identical to `power-bi-dev` §5, with two differences: the marker slug is `power-bi-visual-skills`, and the canonical source is **`$PACK/pbiviz-starter/CLAUDE.md`** itself (there is no pack-root counterpart, because the pack repo is not a visual repo).

**Run once per Step Zero invocation** (not per message):

1. **Locate the canonical file:** `$PACK/pbiviz-starter/CLAUDE.md`, `$PACK` resolved as in §2. If the current repo *is* the pack (i.e. you are editing the starter itself), skip entirely. If the canonical file is unreachable, skip silently — never block work over it.
2. **Compare** the `power-bi-visual-skills-hash` value in this repo's `CLAUDE.md` against the canonical one. No hash line at all counts as unconditionally stale.
3. **Match →** say nothing and continue.
4. **Mismatch →** tell the user this repo's governance block is behind the pack, point them at the pack's `CHANGELOG.md` for what changed, and ask (`AskUserQuestion`) whether to update now.
5. **If yes:** replace exactly the span from `<!-- BEGIN power-bi-visual-skills -->` to `<!-- END power-bi-visual-skills -->` (inclusive — that carries the correct hash line) with the canonical span. **Never touch anything before `BEGIN` or after `END`** — the Project Facts block written at §2.A step 4 lives there and must survive.
