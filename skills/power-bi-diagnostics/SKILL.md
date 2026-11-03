---
name: power-bi-diagnostics
description: >
  Diagnoses Power BI connection failures, model load errors, TMDL syntax errors, and tracing.
  Invoke whenever DataModelLoadFailed, InvalidLineType, a .pbip that will not open or refresh, a
  failing pbi connect, a broken multi-line DAX execution, or an unreachable SQL source MCP server
  needs troubleshooting.
---

# Power BI Diagnostics Skill

Diagnoses runtime, load, and compilation errors in Power BI semantic models and reports.

---

## Common Error Diagnostics

### 1. `DataModelLoadFailed` on TMDL Load
- **Cause 1:** Tabs vs spaces mismatch. Ensure all indentation in TMDL uses `\t` (Tab characters), not spaces.
- **Cause 2:** Comments (`//` or `///`) in `relationship` blocks. Remove ALL comments inside or above `relationship` definitions in `relationships.tmdl`.
- **Cause 3:** Calculated table DAX validation failure. Revert calculated tables to Power Query (M) partitions.

### 2. Multi-line DAX Execution Failure via CLI
- **Cause:** Inline `-e` collapses line breaks. Move query to a `.dax` file and run `pbi dax execute --file query.dax`.

### 3. SQL Source MCP Not Connected
- **Cause 1:** MCP server not installed. Install per `power-bi-partitions` (e.g. `npm install -g mssql-mcp-server` for SQL Server).
- **Cause 2:** MCP installed but not registered at project scope. Check `.mcp.json` / the project's `~/.claude.json` entry for a `type: stdio` server matching the source engine.
- **Cause 3:** Connection credential missing. The credential is a user-owned environment variable (e.g. `MSSQL_CONNECTION_STRING`) — never set or read by Claude. If unset, ask the user to set it themselves and wait.

### 4. The Same Error Survives Two Fixes — Stop Looping
Two failed fixes for one error mean the **diagnosis** is wrong, not the patch. Before any third edit:
- **Consult the advisor** if it is on (CLAUDE.md §8), giving it the exact error text, the two fixes tried, and what each changed in the output. Apply its guidance, or surface the conflict if the files contradict it.
- **If the advisor is off, declined, or not attached**, climb the CLAUDE.md §8 escalation ladder first. If that yields nothing, stop and report the same three facts to the user, plus the hypothesis you have not been able to test. Do not attempt a fourth fix unprompted.
- Either way, `git diff` the working tree first — two fixes stacked on each other are a common cause of the third error.

### 5. Refresh Fails Naming an Unrelated Table
- **Cause:** One table's failure cancels the whole load, and Desktop reports the table it was processing at that moment, not the one at fault. Look for **duplicate keys on the one-side of a relationship** — profile with `dax execute --file` comparing `COUNTROWS` vs `DISTINCTCOUNT` on each dimension key — before touching the table named in the message.

### 6. Custom Visual Renders as an Empty Rectangle (No Error)
- **Cause 1:** `visual.guid` changed between builds — every field binding is gone (CLAUDE.md Hard Rule 21). Never regenerate the GUID; re-import the build that carries the original.
- **Cause 2:** `update()` threw on a degenerate `dataView` (zero rows, null measure, missing role). A custom visual swallows the exception and paints nothing — see the Visual Validation Gate in `power-bi-visual-dev` §5.

### 7. Mass of Modified Files, Empty `git diff`
- **Cause:** CRLF flip from a Desktop save (CLAUDE.md Hard Rule 19). Check `git ls-files --eol`; if `.gitattributes` is missing, add it and renormalize as its own commit before any real change.
