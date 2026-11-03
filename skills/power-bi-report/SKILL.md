---
name: power-bi-report
description: >
  Scaffolds, validates, previews, and manages Power BI PBIR report structures.
  Invoke whenever creating or managing PBIR report definitions, pages, or report configuration.
---

# Power BI Report Skill

> **Authoring Policy (see `power-bi-dev`).** Author report definitions by **editing PBIR JSON files directly** in `*.Report/definition/`. Never invent `$schema` strings — open `.pbip` in Desktop and save to stamp proper versions.

> **Standard Flow (see `power-bi-dev`).** Executes **Stage 5 — Theme, Pages & Data Viz**. Load `power-bi-pages`, `power-bi-visuals`, and `power-bi-themes` alongside this skill.

---

## Prerequisites (see `power-bi-dev` §4)

Run `pbi --version` before this session's first CLI call and install **only if it fails** — `power-bi-dev` §4 holds the single guarded check, the install sequence, and the PATH-failure notice. Never run a blind `pipx install`. Once the CLI answers, `pbi connect` to the model open in Desktop.

---

## PBIR Report Directory Layout

```
<Project>.Report/
├── definition.pbir
└── definition/
    ├── report.json
    ├── version.json
    ├── staticResources/
    └── pages/
        ├── page1/
        │   ├── page.json
        │   └── visuals/
        │       └── visual1/
        │           └── visual.json
        └── page2/
            └── page.json
```

---

## GUI Rules for Report Authoring

1. **Never hand-type `$schema` URLs.** Copy the value from a sibling file of the same type; Desktop re-stamps the correct version on save (Hard Rule #10).
2. **Conditional Formatting & Field Wells are GUI Work.** Do not invent complex CF JSON manually. Copy JSON structures from existing working visuals in the repository.
3. **Verify Canvas Rendering:** After any PBIR JSON edit, the user MUST verify visual rendering in Power BI Desktop.
