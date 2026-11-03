<!-- BEGIN pbi-pack-user -->
<!-- Managed by pbi-pack (user/CLAUDE.md). scripts/sync-user-claude.sh replaces this span in
     ~/.claude/CLAUDE.md on every machine: edit it in the pack, not here. Text outside the span is yours. -->
# Power BI - step zero of every new project

When starting ANY new Power BI project (report, dashboard, model from scratch) --
triggers such as "I started a project", "I'm building a new report/dashboard",
"new BI project", a meeting transcript, a list of KPIs -- invoke the
**power-bi-dev** skill BEFORE any construction skill (power-bi-report, -modeling,
-dax, etc.). The triggers work in any language: match the intent, not the wording.
It is step zero: it sets the mandatory policies the other skills follow -- the
canonical order of the 5 stages (scope -> source analysis -> ETL -> modeling ->
theme/pages/viz), ETL always mandatory and targeting a star schema, deterministic
derivations in M and not in DAX, the `pbi` (CLI) to read/validate, with four write exceptions
named in its §4 (authoring is direct editing of TMDL/PBIR), a checkpoint with the user's authorization at the end of each stage,
handling of the design system (`z_*`), page layout chosen by asking the user,
backup never automatic, and replies in the language the question was asked in. It
builds nothing (at most it offers to publish the Stage 1 scope as an Artifact) -- consult it also to learn which stage the
project is in and who executes the next one.

<!-- pbi-cli:start -->
<!-- pbi-cli:end -->
<!-- END pbi-pack-user -->
