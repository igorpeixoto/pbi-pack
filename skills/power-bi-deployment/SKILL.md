---
name: power-bi-deployment
description: >
  Imports and exports TMDL/TMSL formats, manages semantic model lifecycles with transactions,
  executes backup policies, and controls versioning for Power BI semantic models. Invoke whenever
  deployment, TMDL export/import, diffing, model backup, transaction rollback, or git version
  control is requested in a Power BI (.pbip) project.
---

# Power BI Deployment Skill

> **CLI Policy (see `power-bi-dev`).** Authoring objects is performed by **direct file editing** (TMDL in `*.SemanticModel/definition/`). This skill handles **exporting, importing, comparing, versioning, and deploying** model definitions.

> **Standard Flow (see `power-bi-dev`).** Supports **Stage 6 — Security & Deployment** and cross-stage version control and backup policies.

---

## Prerequisites (see `power-bi-dev` §4)

Run `pbi --version` before this session's first CLI call and install **only if it fails** — `power-bi-dev` §4 holds the single guarded check, the install sequence, and the PATH-failure notice. Never run a blind `pipx install`. Once the CLI answers, `pbi connect` to the model open in Desktop.

---

## Backup Policy — Ask First (Never Automatic)

Before executing any operation that **replaces or modifies** model structure (`import-tmdl`, heavy table refresh, major refactoring), **ask the user** (`AskUserQuestion`) if they wish to create a backup first.

**Mandatory Backup Folder Naming Convention:**
```
<ProjectDir>/backups/<YYYY-MM-DD>_<HHmm>_<reason>/
```

- `<YYYY-MM-DD>_<HHmm>` — Current timestamp (e.g. `2026-08-12_1430`).
- `<reason>` — Short kebab-case description (e.g. `pre-import`, `pre-deploy`, `pre-refactoring`).

For `.pbip` projects, execute backup by copying definition folders:
```powershell
$bkp = "./backups/2026-08-12_1430_pre-import"
New-Item -ItemType Directory -Force $bkp | Out-Null
Copy-Item -Recurse "<Project>.SemanticModel/definition" "$bkp/SemanticModel_definition"
Copy-Item -Recurse "<Project>.Report/definition"        "$bkp/Report_definition"
```

---

## TMDL Export & Import

```bash
# Export model definition to TMDL folder
pbi database export-tmdl ./model-tmdl/

# Import TMDL definition folder into connected Desktop model (offer backup first)
pbi database import-tmdl ./model-tmdl/
```

---

## TMDL Diffing (Snapshot Comparison)

Compare TMDL export folders to inspect structural changes (useful for PR reviews and CI/CD audit):

```bash
pbi database diff-tmdl ./model-before/ ./model-after/
pbi --json database diff-tmdl ./baseline/ ./current/
```

---

## Transactions

Make CLI operations atomic during scripted deployment tasks:

```bash
pbi transaction begin
# ... CLI operations ...
pbi transaction commit     # apply all
pbi transaction rollback   # revert all on error
```

---

## Version Control, Changelog & Release Workflow

Whenever finalizing a commit in a Power BI project repository:

```bash
# 1. Close Power BI Desktop to release file locks

# 2. Update CHANGELOG.md under [Unreleased] if user-visible or model changes occurred

# 3. Add files and commit
git add .
git commit -m "feat(modeling): add revenue measures and calendar dimension"
```

A commit is not a release. Cutting the version heading and creating the `vX.Y.Z` tag belong to **`power-bi-release`**, and only for the commit that is published to the Power BI Service.
