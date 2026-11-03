---
name: power-bi-custom-visuals
description: >
  Scaffolds, builds, packages, and imports Power BI custom visuals (.pbiviz) using TypeScript and
  powerbi-visuals-tools. Invoke whenever a custom visual, .pbiviz package, pbiviz build or start,
  capabilities.json, TypeScript/D3 visual source, or importing a compiled visual into a report is
  requested.
---

# Power BI Custom Visuals Skill

Builds custom visuals for Power BI using `powerbi-visuals-tools` and TypeScript.

This is a **construction** skill. It runs in two contexts, and the governing policy skill differs:

| Context | Governance / step zero |
| --- | --- |
| A visual built **inside a `.pbip` report project**, for that report | `power-bi-dev` (Stage 5) + the project's `CLAUDE.md` |
| A visual in **its own standalone repo** (`pbiviz.json` at the root) | **`power-bi-visual-dev`** + the repo's visual `CLAUDE.md` — invoke it BEFORE this skill |

**If the user asks to separate / extract / split a custom visual out of a report project into its own repo**, that is not a build task — invoke **`power-bi-visual-dev`** (§2.A) for the extraction procedure: history-preserving subtree split, GUID and version carried verbatim, visual governance installed from `pbiviz-starter/`, host-coupling audit, and host-side cleanup. Never hand-roll the move; the failure modes (a changed GUID, a copied report `CLAUDE.md`, a lost history) are all silent and all expensive.

---

## Language & Execution Guidelines

- **Conversational & Prompt Matching:** Match the user's conversational prompt language.
- **Code Comments & Metadata:** Follow the **Project Artifact Language** selected during Stage 1 alignment for TS comments and visual strings.
- **Binary Exception:** `pbi visual import-custom` is one of the three named CLI write exceptions in `power-bi-dev` §4 (a `.pbiviz` is a compiled binary package). Before running it with `--replace`, ask the user whether to back up the `.pbip` definitions first (`power-bi-dev` Backup Policy).

---

## Prerequisites

`powerbi-visuals-tools` is a separate toolchain from `pbi-cli` — Node-based, not pipx. Check before the first `pbiviz` call, install only if it fails (same guarded pattern as `power-bi-dev` §4):

```bash
pbiviz --version                        # check first
npm i -g powerbi-visuals-tools           # install only if the check fails
pbiviz --install-cert                    # one-time, enables the local dev server over https
```

Certificate installation and enabling *Developer mode* in the Power BI Service are **user actions** — prompt for them, never attempt them silently.

---

## Build Loop

```bash
pbiviz new <VisualName>       # scaffold (once)
cd <VisualName> && npm install
pbiviz start                  # dev server; live-reloads into a Desktop/Service dev visual
pbiviz package                # emits dist/<VisualName>.pbiviz
```

Author the visual in `src/visual.ts`, declare data roles in `capabilities.json` (formatting objects follow the card→group shape below), and keep `pbiviz.json` display name and description in the **Project Artifact Language**. Author and support fields are not translated; they come from **Publisher defaults** below.

---

## Formatting Settings — Always Cards → Groups → Slices

The scaffold from `pbiviz new` emits a flat `SimpleCard` with every slice in one list. **Never ship that
shape.** Every formatting card in a pack visual is a `CompositeCard` whose properties are split into named
`Group`s, so the Format pane reads *Size ▸ Size and position / Padding* instead of a single unlabelled pile
of controls. Convert the scaffolded card before adding the second slice — retrofitting later means renaming
properties, and renamed properties silently drop the settings users already saved.

Requires `powerbi-visuals-utils-formattingmodel` ≥ 6 and API ≥ 5.1 (both are what `pbiviz new` installs today).

### Canonical taxonomy

Start from this card → group map and extend it with the same grain. Card `name` and group `name` are
identifiers: always English camelCase, never translated. Only `displayName` follows the
**Project Artifact Language**.

| Card (`name`)          | Groups (`name` → displayName)                                                      |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Size (`layout`)        | `size` → Size and position · `padding` → Padding                                    |
| Style (`style`)        | `typography` → Font · `colors` → Colors · `border` → Border                         |
| Data labels (`labels`) | `values` → Values · `typography` → Font · `position` → Position                     |
| Axis (`axis`)          | `range` → Range · `title` → Title · `ticks` → Labels · `gridlines` → Gridlines      |
| Legend (`legend`)      | `options` → Options · `typography` → Text                                           |

### capabilities.json mapping — the one rule that bites

The formatting service builds **every** descriptor with `objectName = card.name`, including slices nested
inside groups. Groups exist only in the pane; they never appear in `capabilities.json`.

- One `objects` entry per **card** — not per group.
- That entry lists **every property of every group in the card, flattened**.
- Property names must therefore be unique **across the whole card**, not just within a group
  (two groups each with a `fontSize` collide onto one stored property).

### Shape to copy

```ts
import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";
import Card = formattingSettings.CompositeCard;
import Group = formattingSettings.Group;

class SizeGroup extends Group {
    width = new formattingSettings.NumUpDown({ name: "width", displayName: "Width", value: 320 });
    height = new formattingSettings.NumUpDown({ name: "height", displayName: "Height", value: 180 });

    constructor() {
        // Group's base constructor takes the object; class fields initialize right after super()
        // returns, so slices must be wired in the body — not in a field initializer above.
        super({ name: "size", displayName: "Size and position" });
        this.slices = [this.width, this.height];
    }
}

class PaddingGroup extends Group {
    padding = new formattingSettings.MarginPadding({
        name: "padding", displayName: "Padding",
        left:  new formattingSettings.NumUpDown({ name: "paddingLeft",   value: 8 }),
        right: new formattingSettings.NumUpDown({ name: "paddingRight",  value: 8 }),
        top:   new formattingSettings.NumUpDown({ name: "paddingTop",    value: 8 }),
        bottom:new formattingSettings.NumUpDown({ name: "paddingBottom", value: 8 })
    });

    constructor() {
        super({ name: "padding", displayName: "Padding" });
        this.slices = [this.padding];
        this.collapsible = true;    // secondary groups start collapsed-able; primary group stays open
    }
}

class LayoutCard extends Card {
    name = "layout";              // ← the capabilities objects key
    displayName = "Size";
    size = new SizeGroup();
    padding = new PaddingGroup();
    groups = [this.size, this.padding];
}

export class VisualFormattingSettingsModel extends formattingSettings.Model {
    layoutCard = new LayoutCard();
    cards = [this.layoutCard];
}
```

```jsonc
// capabilities.json — one object for the whole card, all groups flattened into it
"objects": {
  "layout": {
    "properties": {
      "width":         { "type": { "numeric": true } },
      "height":        { "type": { "numeric": true } },
      "paddingLeft":   { "type": { "numeric": true } },
      "paddingRight":  { "type": { "numeric": true } },
      "paddingTop":    { "type": { "numeric": true } },
      "paddingBottom": { "type": { "numeric": true } }
    }
  }
}
```

Read values through the group in `update()`: `this.formattingSettings.layoutCard.padding.padding.top.value`.

### Group-level details worth getting right

- **Use composite slices instead of four loose numbers.** `MarginPadding` renders padding/margin as one
  four-way control; `FontControl` renders family + size + bold/italic/underline as one font control. Each
  sub-slice still needs its own capabilities property.
- **A group's `topLevelSlice` (usually a `ToggleSwitch`) becomes that group's on/off header** — but only if
  the group has a `displayName`. A group without one hoists its toggle up to the card header instead.
- **Put a card-wide toggle on `card.topLevelSlice`**, not on the first group.
- **`visible = false`** on a group hides the whole subgroup — that is how conditional pane sections are done
  (set it inside `onPreProcess()` on the card), never by rebuilding the model.

---

## Code Quality Loop (built-in `/code-review` and `/simplify`)

This is the one place in the pack where the code under edit is **ordinary TypeScript**, so the general-purpose built-in review skills apply at full strength — unlike TMDL or PBIR JSON, where they are thin.

Both are bound by **CLAUDE.md Hard Rule #20** — explicit level, narrow target, fresh session, never both in one
session. What that means here:

- **Before `pbiviz package`**, run **`/code-review medium src/`**. It is worth the pass here specifically because
  a custom visual has no Desktop validation gate that catches logic errors: a bad `update()` handler renders an
  empty rectangle, not an error message.
- Run **`/simplify`** after a feature lands, in its own session, to sweep reuse, dead code, and over-complex D3
  selections. Quality only — it does not hunt bugs, so it complements rather than replaces `/code-review`.
- The target is always `src/`, a single file, or a branch diff — never the repo root, which drags the project's
  generated PBIR/TMDL JSON into the pass.
- `high`/`max` is for a deliberate pre-publish audit of a visual going out to many report authors, never for the
  routine pre-package pass.
- Pay particular attention to what the reviewers are good at catching in this file type: unhandled `dataView` shapes (null `categorical`, zero rows, missing measure), unremoved D3 event listeners across `update()` calls, and hardcoded colors that should read from the report theme via `IColorPalette`. Flag any formatting card still shaped as a flat `SimpleCard`.

---

## Publisher defaults

Every visual the pack creates carries the same publisher identity. Fill these fields right after `pbiviz new`. This section is the only place the values are written down; `power-bi-visual-dev` and `pbiviz-starter/CLAUDE.md` point here instead of repeating them.

| Field | Value |
|---|---|
| `pbiviz.json` → `author.name` | `Igor Peixoto` |
| `pbiviz.json` → `author.email` | `visuals@igorpp.dev` (`AUTHOR`) |
| `package.json` → `author` | `"Igor Peixoto <visuals@igorpp.dev>"` |
| `pbiviz.json` → `visual.supportUrl` | `https://github.com/<owner>/<visual-repo>/issues` |
| `pbiviz.json` → `visual.gitHubUrl` | `https://github.com/<owner>/<visual-repo>` |
| AppSource / Partner Center support contact | `visuals@igorpp.dev` (`AUTHOR`) |

```jsonc
// pbiviz.json (excerpt)
{
  "visual": {
    "supportUrl": "https://github.com/<owner>/<visual-repo>/issues",
    "gitHubUrl": "https://github.com/<owner>/<visual-repo>"
  },
  "author": { "name": "Igor Peixoto", "email": "visuals@igorpp.dev" }
}
```

```jsonc
// package.json (excerpt)
{ "author": "Igor Peixoto <visuals@igorpp.dev>" }
```

`AUTHOR` is the address published with the package. It ends up in the `.pbiviz` metadata and the AppSource listing, so it attracts spam and is a dedicated alias. The contact address in the pack's README (`CONTACT`) is for people reading the repo and never goes into package metadata. Support goes through the visual repo's GitHub Issues, so `supportUrl` and `gitHubUrl` both point at that repo and no separate support site is needed.

**Pre-package check:** before every `pbiviz package`, the author email is `AUTHOR`, not a personal or employer address. Before a binary leaves the machine (attached to a tag, imported into a client report, submitted to AppSource), the visual repo is public with Issues enabled, so `supportUrl` resolves for someone who is not signed in to GitHub.

---

## Identity — `pbiviz.json` (never edited casually)

- **`visual.guid` is permanent from the first import onward.** Power BI binds an imported visual to a report *by GUID*: change it and every report already using the visual shows a missing-visual placeholder, and re-importing under the new GUID does **not** restore the field bindings — every well has to be re-bound by hand, on every page, in every report. `displayName` renames freely; the GUID does not.
- **`visual.version` only goes up**, and moves together with the `CHANGELOG.md` heading and the git tag. The org store refuses to replace an imported visual with a lower version. `pbiviz package` stamps the version into the binary, so bump before packaging.
- **Never bump `apiVersion` without moving `powerbi-visuals-api` to match** — a mismatch fails at package time or, worse, only at runtime in the Service, where there is no console to read.

In a standalone visual repo these are Hard Rules #1, #2 and #12 of that repo's `CLAUDE.md` — see `power-bi-visual-dev`.

---

## Import into the Report

```bash
pbi visual import-custom ./dist/<VisualName>.pbiviz            # Binary Exception, see above
pbi visual import-custom ./dist/<VisualName>.pbiviz --replace   # back up .pbip definitions first
```

After import, the visual's registered `visualType` string is what `power-bi-themes` needs for a per-visual `visualStyles` entry (e.g. keeping functional header icons ON — see `power-bi-themes` and CLAUDE.md Hard Rule #14).
