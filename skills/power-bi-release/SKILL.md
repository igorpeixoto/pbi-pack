---
name: power-bi-release
description: >
  Manages release lifecycles, BI-adapted Semantic Versioning (BI Semver), CHANGELOG.md
  version cutting, and automated creation/verification of annotated Git tags (vX.Y.Z).
  Invoke whenever release management, tag generation, semver classification, version audit,
  or publishing lifecycle guidance is requested for a Power BI (.pbip) project.
---

# Power BI Release Skill — Release & Git Tag Governance

Manages release workflows, BI-adapted Semantic Versioning (BI Semver), `CHANGELOG.md` version cutting, and Git tag automation.

---

## 1. The Invariant

> **Tag exactly what is published in the Power BI Service.**
> The tagged commit in Git IS the true representation of what runs in production. Publishing untagged commits breaks repository tracking.

---

## 2. Release Management & Version Bumping

Both the **human developer** and **Claude Code** can manage and cut releases.

When a release is requested or a milestone is completed:
1. **Analyze Changes:** Inspect `CHANGELOG.md` entries under `[Unreleased]` and committed Git history. For a **MAJOR or MINOR** bump, offer a built-in **`/code-review`** pass over the **diff since the last tag** (`/code-review medium v<previous>..HEAD`) *before* cutting the heading — a diff target, never the `definition/` folder, and bound by **CLAUDE.md Hard Rule #20**. Raise it to `high` only for a MAJOR bump — §1's invariant is that the tag **is** production, and a pre-tag fix costs a commit while a post-publish one costs the §5 rollback.
2. **Determine Semver Bump:** Choose MAJOR, MINOR, or PATCH based on BI Semver criteria.
3. **Cut Heading in CHANGELOG.md:** Move items from `[Unreleased]` into a new heading `## [X.Y.Z] - YYYY-MM-DD` and open a fresh `[Unreleased]` section above it.
4. **Create Annotated Tag:** Create the corresponding Git tag `vX.Y.Z`.
5. **Publishing Signal:** The tagged version represents the validated state ready for publishing to the Power BI Service.

---

## 3. BI-Adapted Semantic Versioning (BI Semver)

| Bump | Criteria | Example |
| :--- | :--- | :--- |
| **MAJOR** (`X.0.0`) | Model schema changes; breaking source changes; semantic changes shifting numbers stakeholders already saw. | Re-graining fact table `fSales`, changing primary key cardinality. |
| **MINOR** (`x.Y.0`) | New pages, new visuals, new measures, or new dimensions added without breaking legacy KPIs. | Adding a new "Customer Analytics" page, adding YTD measures. |
| **PATCH** (`x.y.Z`) | Bug fixes in existing measures, conditional formatting tweaks, filter corrections, or label fixes. | Fixing date slicer bounds, correcting theme colors, fixing BLANK tooltip. |

---

## 4. Release Tag Execution Protocol

When executing a release:

### Step 1: Verify Git Status & Close Desktop
```bash
git status
```
Ensure all changes are committed and Power BI Desktop is closed.

### Step 2: Cut Release Heading in CHANGELOG.md (If Not Yet Cut)
If `CHANGELOG.md` has items under `[Unreleased]`, determine the new version number `X.Y.Z` (e.g. `1.1.0`), rename `[Unreleased]` to `## [1.1.0] - YYYY-MM-DD`, and open a fresh `[Unreleased]` above it:

```markdown
## [Unreleased]

- 

## [1.1.0] - 2026-08-12

- Added new Regional Sales analysis page
- Added YoY Growth measures
```

Commit the updated `CHANGELOG.md`:
```bash
git add CHANGELOG.md
git commit -m "chore(release): release v1.1.0"
```

### Step 3: Create Annotated Git Tag
Extract summary lines from that version section in `CHANGELOG.md` and execute:
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z: <summary of changes>"
```

### Step 4: Push and Notify
If remote exists:
```bash
git push origin main --tags
```
Tell the user, in their language, that `vX.Y.Z` is cut and tagged and that this commit is the one to publish.

---

## 5. Emergency Rollback Protocol

If a newly published release fails in the Power BI Service:

```bash
# 1. Close Power BI Desktop
# 2. Checkout last known-good tagged release:
git checkout v1.0.0

# 3. Open .pbip in Desktop, verify, and re-publish to Service.
# 4. Investigate broken release on a separate fix branch:
git checkout -b fix/release-rollback-investigation
```
