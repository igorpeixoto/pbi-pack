# Using the pack

The full reference behind the [README](../README.md). Read its [warning about the scripts that write to `~/.claude/`](../README.md#before-you-run-a-script) first.

---

## How to Start a New Power BI Project (`pbi-starter`)

Whenever you create a new Power BI project repository (`.pbip`), set up governance in seconds:

1. **Copy Starter Contents:** Copy all files and folders inside `pbi-starter/` into the root directory of your new Power BI project repository. Use the trailing `/.` form (not `/*`), since `*` doesn't match dotfiles like `.gitattributes` and `.claude/` in bash:
   ```bash
   cp -r /path/to/pbi-pack/pbi-starter/. /path/to/new-powerbi-project/
   ```
2. **Open in Claude Code:** Launch Claude Code inside your new project folder.
3. **Kickoff (Step Zero):** Prompt Claude with your project requirements (e.g. *"Starting a new Power BI dashboard for Sales Analytics"*).
4. **Automatic Policy Activation:** Claude Code will invoke the `power-bi-dev` skill, guide you through Stage 1 (Scope & Kickoff), ask for your **Project Artifact Language** preference, and enforce the canonical 5-stage workflow.

---

## Custom Visuals: Their Own Repo, Their Own Governance (`pbiviz-starter`)

A custom visual is the one part of a Power BI project that is **ordinary TypeScript**. Once it is good enough to reuse across reports, it wants its own repo — and a report's `CLAUDE.md` is the wrong governance for it in both directions: it enforces TMDL/PBIR rules that do not apply, and omits every rule that does (GUID permanence, append-only data-role and formatting contract, degenerate-`dataView` handling, theme-driven color, the Visual Validation Gate). So the pack ships a **second, independent governance kit**.

| | Report project | Standalone custom visual |
| :--- | :--- | :--- |
| Starter kit | `pbi-starter/` | `pbiviz-starter/` |
| Governance | `CLAUDE.md` (`BEGIN power-bi-skills`) | `CLAUDE.md` (`BEGIN power-bi-visual-skills`) |
| Step zero skill | `power-bi-dev` | **`power-bi-visual-dev`** |
| Canonical flow | 5 stages: Scope → Source → ETL → Modeling → Viz | 6 stages: Scope/Contract → Capabilities → Rendering → Formatting Pane → Build/Review/Package → Distribute |
| Validation gate | Desktop refresh green | **Visual Validation Gate** — real data · zero rows · null measure · resize · grouped Format pane · theme switch |
| Semver severity | What shifts numbers stakeholders saw | What breaks a **consuming report's** bindings and saved settings |

### Case 1 — Extracting a visual out of a report project

Ask inside the report repo: *"separate this visual into its own repo"*. `power-bi-visual-dev` §2.A runs the extraction, and the three steps that are silent-failure territory are the reason it is a procedure and not a copy:

1. **History, not copy-paste** — `git subtree split -P <VisualName>` carries the commits that explain why the visual is shaped the way it is. (It follows one path prefix: if the folder was ever renamed, you are told what history will not come.)
2. **`visual.guid` carried verbatim** — Power BI binds imported visuals **by GUID**. A regenerated GUID makes every field binding in every consuming report vanish with no error message, and re-importing does not bring them back.
3. **Verify before deleting** — the new repo must build, and its binary must re-import into a *backed-up copy* of the host report with bindings intact, before the source folder leaves the report repo. Then a pointer stays behind in the host repo (after its `END power-bi-skills` marker) naming the new repo, the imported version, and the re-import command — so the next session does not find a `.pbiviz` with no source and fork a stale copy.

In between: the visual governance is installed from `pbiviz-starter/`, the host's Project Artifact Language and registered `visualType` are carried over, and a **host-coupling audit** greps for the things that make a visual unusable in anyone else's report — hardcoded colors, hand-rolled number formatting, positional `dataView` access, hardcoded field names, assumed series counts. Findings are reported with severities, never silently "fixed" inside a move commit.

### Case 2 — A standalone visual from scratch

```bash
mkdir MyVisual && cd MyVisual && git init
cp -r /path/to/pbi-pack/pbiviz-starter/. .     # trailing /. so dotfiles come too
```
Then open Claude Code in that folder and say what the visual should do. `power-bi-visual-dev` detects the repo mode, asks for the name and Project Artifact Language, scaffolds via `power-bi-custom-visuals` (`pbiviz new`), and converts the scaffold's flat `SimpleCard` to the mandatory `CompositeCard`/`Group` shape before the second formatting slice exists — the one thing that is genuinely expensive to retrofit, because renaming a released property silently resets every report author's saved settings.

Both governance files carry their own hash stamp, so a visual repo checks its own freshness against `pbiviz-starter/CLAUDE.md` exactly as a project checks against the root `CLAUDE.md` (see *Automated Sync* below). The visual file is **canonical in place** — the pack root is a governance repo, not a `.pbiviz` repo, so there is nothing to copy it from.

---

## Language Policy (Prompt Matching vs. Code Consistency)

- **Conversational Language:** Claude Code automatically replies in the **same language used in your chat prompt** (English, Portuguese, Spanish, etc.).
- **Project Artifact Language:** During Stage 1 Kickoff, Claude Code confirms/asks for your preference for in-model metadata:
  - Code comments (`//` in M and DAX)
  - DAX measure descriptions (`///`)
  - TMDL `displayFolder` names
  - Documentation and data dictionaries

Once selected for a project, Claude Code maintains that language consistently for all code comments and tooltips throughout the project repository.

---

## Git Release Protocol & BI Semver

Both the **human developer** and **Claude Code** can manage and cut releases:

```
[Claude Code / Human] Maintains [Unreleased] in CHANGELOG.md during commits
        │
        ▼ (Feature Complete & Desktop Tested / User Request)
[Claude Code / Human] Cuts release heading in CHANGELOG.md (e.g., ## [1.1.0] - 2026-08-12)
        │
        ▼ (Desktop Refresh & Validation Passed)
[Claude Code] Generates `v1.1.0` annotated Git tag
        │
        ▼
[Human Developer] Publishes .pbip to Power BI Service
```

### BI-Adapted Semver Table

| Bump | Criteria |
| :--- | :--- |
| **MAJOR** (`X.0.0`) | Model schema changes, breaking source changes, or semantic rules shifting numbers stakeholders already saw. |
| **MINOR** (`x.Y.0`) | New pages, new visuals, new measures, or new dimensions added without breaking legacy KPIs. |
| **PATCH** (`x.y.Z`) | Bug fixes in existing measures, conditional formatting tweaks, filter corrections, or label fixes. |

---

## Automated Sync (Git Hooks)

Git hooks are **never tracked by git**, so `.git/hooks/` starts empty on a fresh clone and on every other machine. Their sources of truth live in `scripts/git-hooks/`. Install all three once per clone:
```bash
sh scripts/install-hooks.sh
```

Three hooks driving the governance stamping and the syncs into `~/.claude/`:

1. **`pre-commit` — governance stamping (+ the `CLAUDE.md` → `pbi-starter/CLAUDE.md` copy):** stamps each just-edited governance file with a `<!-- <slug>-hash: ... -->` line (a short hash of its governance block, auto-generated — never hand-edit it) right after its `BEGIN` marker, via the shared `scripts/stamp-governance.sh`. Two files, two independent slugs: `CLAUDE.md` (`power-bi-skills`), whose `BEGIN`..`END` span is then copied to `pbi-starter/CLAUDE.md` by `scripts/sync-starter.sh` and both staged — the root file's pack-only notes after the `END` marker stay behind, and the same script copies `.claude/settings.json` to `pbi-starter/.claude/settings.json` whenever it changes (the starter used to drift behind the root's pre-approved `pbi` verbs); and `pbiviz-starter/CLAUDE.md` (`power-bi-visual-skills`), which is stamped **in place** — it is its own canonical source, since the pack root is a governance repo and not a `.pbiviz` repo, so there is nothing to copy it from. A GitHub Action (`.github/workflows/sync-claude.yml`) repeats both stamps and the copy on push as a backstop, for pushes from a machine where the hook was never installed.
2. **`pre-commit` — `skills/` → `~/.claude/skills/`:** Claude Code loads skills from `~/.claude/skills/`, which has **no automatic link** to this repo's `skills/` folder — it's a separate, manually-installed copy. The hook re-copies every `skills/<name>/` directory into `~/.claude/skills/<name>/` whenever anything under `skills/` is committed, so skill edits take effect in the next session without a manual copy step. (This side of the sync is runtime-only and machine-local — it's never staged into the git commit itself.)
3. **`pre-commit` — `user/CLAUDE.md` → `~/.claude/CLAUDE.md`:** replaces only the `<!-- BEGIN pbi-pack-user -->`..`END` span of your user-level `CLAUDE.md` (`scripts/sync-user-claude.sh`), so anything else you keep in that file survives. If the span was edited directly in `~/.claude/CLAUDE.md` since the last sync, the script **refuses to overwrite it** and says so: move the edit into `user/CLAUDE.md`, or rerun with `--force` (a backup is kept as `CLAUDE.md.bak-pbi-pack`).
   **`user/settings.json` → `~/.claude/settings.json`** is optional: the repo ships no `user/settings.json`, so add your own to share settings between your machines. It works the same way per key (`scripts/sync-user-settings.sh`): only the keys listed in `user/settings.json` are managed, and everything else in your settings (the session hooks, machine-specific `env`, plugins) stays local. Because `/model`, `/effort` and `/config` write to that same file, the merge is three-way against what was last synced: a key changed on this machine keeps its local value and is reported once — run `sh scripts/sync-user-settings.sh --capture` in the pack to copy this machine's values of the managed keys into `user/settings.json`, then commit to share them. `permissions.allow`/`deny`/`ask` merge entry by entry (pack additions added, pack removals removed, a machine's own one-off approvals kept and never captured), and `env` is managed variable by variable, so a machine's own environment variables are never replaced. A value that looks like a secret makes the script refuse to sync: secrets never go in the pack.
4. **`post-merge` + `post-checkout` — all of the above after a pull or a branch switch**, via `scripts/sync-home.sh`: skills, the `CLAUDE.md` span, the settings keys, the `pbi-sync` scripts, and the git hooks themselves, each only when the pull touched it. Because the hooks reinstall themselves, a pull that changes the sync logic takes effect on the next pull with no installer to run. `pre-commit` only fires on `git commit`, which helps nothing on a machine where you only *pull*; these two close that gap.

**Nobody has to run `git pull` either.** The `SessionStart` hook (`scripts/pbi-sync/hook-session-start.sh`) pulls the pack in the background at most once every 6 hours (`PBI_PACK_UPDATE_HOURS`), fast-forward only and only on a clean `main`; `post-merge` then does the copying. It never delays a session start, what it pulls takes effect from the next session, and a failed attempt (offline, diverged, no SSH) is reported once at the next session start with the reason kept in `~/.claude/pbi-sync/state/pack-autoupdate.log`. Turn it off with `PBI_PACK_AUTOUPDATE=0`. The one thing it does not do is push: commits made on a machine still need `git push`.

**The post-* hooks are guarded to `main`.** `~/.claude/skills/` is *personal scope* — it loads in **every** project on that machine, not just Power BI ones. Without the guard, checking out a feature branch would install half-finished skills globally and they'd surface in unrelated projects. Switching away to a branch deliberately syncs nothing; switching back to `main` re-syncs.

The shared implementation is `scripts/sync-skills.sh`, runnable by hand at any time:
```bash
sh scripts/sync-skills.sh
```
Use it when you've edited a skill and haven't committed yet — that's the one gap the hooks don't cover by design. It also prunes `power-bi-*` skills that were deleted from this repo (otherwise a removed skill keeps loading forever), scoped to that prefix so any personal skills of your own in `~/.claude/skills/` are never touched.

### Why the hash exists: per-repo `CLAUDE.md` drift
Every Power BI project repo — and every standalone custom visual repo — gets its own **point-in-time copy** of the relevant `CLAUDE.md` (via the `cp -r pbi-starter/.` step above) with no ongoing link back to this pack. The stamped hash lets `power-bi-dev`'s Step Zero check, from inside any project, whether its `CLAUDE.md` is behind this pack's canonical version — by comparing hashes against this repo directly on disk (default path `C:\dev\pbi-pack` — local and unsynced by design, since the pack is Claude tooling and Hard Rule 22 keeps tooling out of OneDrive; override with `PBI_PACK_HOME` on a machine where that path doesn't hold) — and offer to update just the governance block if so, leaving any project-specific additions outside the `BEGIN`/`END` markers untouched. The comparison itself runs deterministically in the `SessionStart` hook (`scripts/pbi-sync/hook-session-start.sh`, installed by `install-pbi-sync.sh`), which prints one `governance:` line in every project (matches / behind the pack / no hash line) — Step Zero reads that line instead of recomputing it, and falls back to the manual comparison only when no line appears. See `skills/power-bi-dev/SKILL.md` §5 for the full procedure — and `skills/power-bi-visual-dev/SKILL.md` §7 for the identical check on the visual side, which compares against `pbiviz-starter/CLAUDE.md` instead and preserves the repo's **Project Facts** block written after the `END` marker.

---

## OneDrive: publishing the deliverable (`pbi-sync`)

Client projects have to end up in a corporate OneDrive folder, but Claude tooling must never get
there. The split that makes both true (CLAUDE.md **Hard Rule 22**):

| | Working repo | OneDrive folder |
| --- | --- | --- |
| Path | `C:\dev\pbi\<slug>\` — unsynced | the client's folder |
| Role | the only place you edit; the only place Desktop opens | a **publish target** |
| Contains | everything, tooling included | `.pbip`, `.Report/`, `.SemanticModel/`, `CHANGELOG.md`, `README.md`, `.gitignore`, `.gitattributes` — and its own `.git` |
| Written by | you | `pbi-publish` and nothing else |

Both are git repos with **separate histories on purpose**: your dev history keeps the tooling
commits, the deliverable gets one clean commit per publish (`publish: <msg>  [src <sha>]`) that a
colleague can read with `git log` without ever seeing the tooling.

The scripts are **canonical in this repo** at `scripts/pbi-sync/` and run from
`~/.claude/pbi-sync/bin/` — off every sync root, like everything else Claude touches. `sh
scripts/install-pbi-sync.sh` copies them across; the pre-commit hook re-runs it whenever
`scripts/pbi-sync/` is touched, exactly as it does for `skills/`. Edit them here, never in
`~/.claude/`, or the next install overwrites your change.

The registry mapping local ↔ OneDrive is `~/.claude/pbi-sync/projects.json`, kept there rather
than in the project so it cannot ride along into a synced folder.

```bash
sh ~/.claude/pbi-sync/bin/pbi-register.sh <slug> <local-path> <onedrive-path>
sh ~/.claude/pbi-sync/bin/pbi-status.sh            # read-only: unpublished commits, drift, locks
sh ~/.claude/pbi-sync/bin/pbi-publish.sh <slug> --dry-run
sh ~/.claude/pbi-sync/bin/pbi-publish.sh <slug> --init   # first publish into a target
sh ~/.claude/pbi-sync/bin/pbi-publish.sh <slug>
sh ~/.claude/pbi-sync/bin/pbi-pull.sh <slug>       # someone edited the deliverable: review branch
```

**Operating reference:** [`pbi-sync-runbook.html`](pbi-sync-runbook.html) — which folder to start
in, how to publish, what each gate abort actually means, troubleshooting, and the second-machine setup.

**Nothing reaches OneDrive until every gate passes:** Desktop closed → local tree committed →
deliverable built in a local staging dir from an **allowlist** → leak check (no `.claude/`,
`CLAUDE.md`, `RELEASING.md`, `docs/`, and no published `.md` mentioning the tooling) → structural
check (`.pbip`, `model.tmdl`, at least one page) → file count not collapsed vs. the last publish →
OneDrive side unchanged since the last publish. Then a local snapshot, then the mirror, then a
post-copy verification that restores the snapshot if it fails.

Two `SessionStart` / `SessionEnd` hooks in `~/.claude/settings.json` are **advisory only** — they
report state and never copy anything. `SessionEnd` is documented as "may not fire" on some
terminations, so it is not a safe place for a copy-back; if it misses, the next `SessionStart`
recomputes the same fact from git. `SessionStart` also fires after `/clear` and after a compaction,
where it prints only the project-state block described under **Context & token discipline**.

---

## Setting up a second machine

Everything portable lives in git. What does not is listed below, and is deliberate.

```bash
git clone https://github.com/igorpeixoto/pbi-pack.git C:/dev/pbi-pack
cd /c/dev/pbi-pack
sh scripts/install-hooks.sh       # .git/hooks are never cloned
sh scripts/sync-home.sh           # skills, ~/.claude/CLAUDE.md span, publish tooling + session hooks
```

That is the only manual step a machine ever needs. From then on the `SessionStart` hook pulls the pack and the hooks refresh `~/.claude/` (see **Automated Sync** above). A machine set up before this existed needs one `git pull` here followed by those same two commands.

Then, per project:

```bash
git clone <remote> C:/dev/pbi/<slug>
sh ~/.claude/pbi-sync/bin/pbi-register.sh <slug> C:/dev/pbi/<slug> "<onedrive path>"
```

**Do not copy `projects.json` between machines.** Its OneDrive half embeds the Windows profile
name (`C:\Users\<you>\OneDrive - <Org>\…`), which differs where the account is named
differently. A copied registry points publishes at paths that do not exist. Re-register instead —
it is three arguments per project.

`~/.claude/pbi-sync/state/` is per-machine too: it records what was last published *from here*.
On a fresh machine every project reads as never-published until its first publish, and the drift
gate will refuse `--init` against a folder that is already a deliverable repo. That is correct —
reconcile with `pbi-pull.sh` rather than forcing.

**If the network blocks outbound SSH (port 22)**, add the SSH-over-443 config from the
Prerequisites section below first, or every `git@github.com:` remote hangs for two minutes and
fails while the HTTPS ones work.

---

## Advisor: Sonnet codes, Opus advises, Fable above them

The pack names four consult points for Claude Code's [advisor tool](https://code.claude.com/docs/en/advisor) — Stage 3 grain, a load error that survived two fixes, hand-authored PBIR structure, custom-visual extraction (CLAUDE.md §8) — and a **pairing ladder**:

| Who writes the code | Who advises | How |
| --- | --- | --- |
| Sonnet (`sonnet[1m]`, effort `high`) | Opus | `pbi-claude.sh` default; also the seeded user settings |
| Opus (`opus[1m]`) | Fable | `pbi-claude.sh --opus` |
| either | Fable, after Opus **declined** at a consult point | you type `/advisor fable` in the session, Claude re-consults once |

The advisor is configured **per user**, never in a project. Your own choice of `model`, `advisorModel` and `fallbackModel` can travel with the pack in a `user/settings.json` you add (see **Automated Sync**). `scripts/install-pbi-sync.sh` also seeds `model: "sonnet[1m]"`, `advisorModel: "opus"` and `fallbackModel: ["opus[1m]"]`, but **only for keys that are absent** — it never overwrites a value, so it only matters on a machine that has neither. `fallbackModel` covers a *server-side* outage of the main model mid-session; it is unrelated to the advisor.

Claude Code has no advisor fallback setting: `--advisor <m>` exits at launch when `<m>` cannot act as advisor (Fable needs the one-time usage-credits consent via `/model fable`; org allowlists; unsupported pairings), and a saved `advisorModel` is silently dropped instead. So the launcher walks the ladder at launch:

```bash
sh ~/.claude/pbi-sync/bin/pbi-claude.sh            # sonnet + opus  -> sonnet + fable  -> sonnet, no advisor
sh ~/.claude/pbi-sync/bin/pbi-claude.sh --opus     # opus + fable   -> opus + opus     -> opus, no advisor
```

A rung is skipped when `claude` exits non-zero within 20 seconds (a launch refusal, not a session) — a timing heuristic, stated plainly in the script. The last rung launches *without* an advisor on purpose, so the banner shows it and the skills fall back to `AskUserQuestion` checkpoints. `CLAUDE_BIN`, `PBI_CLAUDE_MAIN`, `PBI_CLAUDE_SONNET_EFFORT` and `PBI_CLAUDE_LAUNCH_SECONDS` override the binary, the default rung, the Sonnet effort and the threshold. The launcher never edits settings; `/advisor` and `/model` inside the session behave as usual, and its explicit flags override whatever `/advisor` saved last time. Feature-flag fetching must be on (`DISABLE_TELEMETRY` turns the advisor off).

---

## Context & token discipline

Every request re-sends the whole conversation, so the cost of a session is driven by how large its context is allowed to grow, far more than by the size of `CLAUDE.md` or the skills. Three pieces ship with the pack and work as soon as it is installed; a fourth is a pair of settings you opt into.

| Piece | Where | What it does |
| --- | --- | --- |
| `docs/STATE.md` + `/clear` | `pbi-starter/docs/STATE.md`, `power-bi-dev` §6, `CLAUDE.md` *Compact instructions* | The stage, the decisions and the open checkpoints live in a file, so each stage checkpoint can end in a `/clear`. *Compact instructions* tells an automatic compaction what to keep. |
| Session-start hook | `scripts/pbi-sync/hook-session-start.sh` | Runs on startup, resume, `/clear` and after a compaction. In a project folder it prints `docs/STATE.md` (first 4,000 characters) and whether the maps are current, stale or missing; after a compaction it also lists what is uncommitted. On `/clear` and compaction it prints nothing else. |
| Project maps | `skills/power-bi-dev/scripts/pbi_map.py` ➔ `docs/model-map.md`, `docs/report-map.md` | A generated index of the project: tables, columns, measures with line numbers, relationships and shared M expressions; pages ➔ groups ➔ visuals with absolute positions and bound fields. A session reads the map, then only the file or line range it points at, instead of the `definition/` folders. It also flags visuals that land outside their page (Hard Rule 23). |
| Read deny rules | `.claude/settings.json` | Denies `Read` on `**/definition/cultures/**` and `**/.pbi/cache.abf`, the two paths where one accidental read costs the most. |

```bash
python ~/.claude/skills/power-bi-dev/scripts/pbi_map.py              # from a project root: writes docs/*.md, adds them to .gitignore
python ~/.claude/skills/power-bi-dev/scripts/pbi_map.py <dir> --out <elsewhere> --no-gitignore   # look at another project without writing into it
```

The maps are generated and not committed; `STATE.md` is hand-written and committed. Neither is published to the client folder (`docs/` never is).

A session hook installed before this existed is matched on `startup|resume` only. Rerun `sh scripts/install-pbi-sync.sh` (with the git hooks installed, the pull that brings this change does it): it widens that matcher to `startup|resume|clear|compact` once, and leaves any matcher you wrote yourself alone.

### Opt-in: a smaller context window and a cheaper subagent model

The pack ships no `user/settings.json` and the installer sets neither of these, because both change how every session on the machine behaves. To use them, add them to your own `~/.claude/settings.json`, or to a `user/settings.json` in your clone so `sync-user-settings.sh` carries them to your other machines (see **Automated Sync**):

```json
{
  "model": "sonnet[1m]",
  "effortLevel": "high",
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "250000",
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"
  }
}
```

| Key | What it does |
| --- | --- |
| `model`, `effortLevel` | The first rung of the pairing ladder above: Sonnet writes the code at effort `high`. `advisorModel` and `fallbackModel` can sit beside them. |
| `env.CLAUDE_CODE_AUTO_COMPACT_WINDOW` | How full the context gets before Claude Code compacts it, in tokens, from `100000` to `1000000`. Without it, a model with a 1M window compacts at about 967K. While the variable is set it wins over `/autocompact` and the `autoCompactWindow` setting; use that setting in its place if you want `/autocompact` to keep working per session. |
| `env.CLAUDE_CODE_SUBAGENT_MODEL` | The default model for subagents that are not given one another way, so they stop inheriting the main model. It is a default: a model passed for one call, or the `model` field in an agent's definition, still wins, and it does not change the built-in Explore and Plan agents. |

Both variables are described here from the Claude Code documentation ([model configuration](https://code.claude.com/docs/en/model-config), [subagents](https://code.claude.com/docs/en/sub-agents)) as it read in November 2026; the pack has no test that proves either takes effect in a live session, so confirm it on your machine (that documentation says `/autocompact` reports the override while the variable is set). `250000` is a starting point: lower it for shorter sessions, raise it if compactions interrupt long stages.

`sync-user-settings.sh` merges `env` variable by variable: variables in your `user/settings.json` are added, a variable only one machine sets stays there, and a value you changed locally is kept and reported, like every other managed key.

---

## Prerequisites

**Report projects** — for full model reading and validation capabilities:
```bash
pipx install pbi-cli-tool
pbi connect
```
*(Note: Authoring is always performed via direct file editing of TMDL/PBIR files; `pbi-cli` is used exclusively to read, query, and validate data.)*

**Custom visual repos** — a separate, Node-based toolchain:
```bash
npm i -g powerbi-visuals-tools    # provides pbiviz
pbiviz --install-cert             # one-time, USER action: it writes to the OS trust store
```
Enabling *Developer mode* in the Power BI Service is likewise a user action. `pbi-cli` is needed in a visual repo only at the last stage, for `pbi visual import-custom` — there is no semantic model to connect to.

**GitHub over SSH on a network that blocks port 22** — when outbound port 22 is blocked, any `git@github.com:` remote hangs and eventually fails with `Connection timed out`. GitHub also serves SSH on 443, which is not blocked. One-time fix in `~/.ssh/config`:
```
Host github.com
  Hostname ssh.github.com
  Port 443
  User git
```
Symptom to recognise: `git push` / `git fetch` stalls for ~2 minutes on an SSH remote while an HTTPS remote on the same machine works fine. When your repos are split between both remote styles, only some of them fail — which makes it look like a repo problem rather than a network one.
