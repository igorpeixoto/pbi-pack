# <PROJECT_NAME>

<!--
  This file is the CLIENT-FACING README. `pbi-publish` copies it into the OneDrive deliverable
  folder AS `README.md`. The repo's own `README.md`, if it has one, is tooling documentation and
  never leaves the local working copy.

  Write it in the project artifact language agreed at Step 1 (CLAUDE.md §1.B), not necessarily
  the language of the conversation.

  It must not mention Claude, CLAUDE.md, skills, agents, or any part of the development tooling.
  `pbi-publish` scans published .md files and aborts the publish if it finds a mention, so a slip
  here blocks the deliverable rather than shipping it.

  Delete these comments before the first publish.
-->

One paragraph: what this report shows, for which project or client, and who it is for.

## Opening the report

Open `<PROJECT_NAME>.pbip` in Power BI Desktop.

> Requires a Desktop version with the PBIP / TMDL project format enabled
> (*Options → Preview features → Power BI Project (.pbip) save option*).

## What is in this folder

| Item | Description |
| ---- | ----------- |
| `<PROJECT_NAME>.pbip` | Project file — the entry point |
| `<PROJECT_NAME>.SemanticModel/` | Semantic model: tables, measures, relationships |
| `<PROJECT_NAME>.Report/` | Report definition: pages, visuals, theme |
| `CHANGELOG.md` | Version history of this dashboard |

## Data sources

List the sources the model reads and where they live, so whoever refreshes it knows what has to
be reachable. Name the files or systems, not the credentials.

## Refreshing

Any manual step required before or after a refresh — a spreadsheet that must be updated first,
a parameter that must be pointed at the current period, a check to run afterwards.

## Version history

This folder is version-controlled with Git. `git log` shows one entry per published version;
`CHANGELOG.md` describes what changed in each.
