---
name: power-bi-partitions
description: >
  Manages Power BI table partitions, named M/Power Query expressions, data sources, and calendar
  table M scripts. Invoke whenever Power Query, M code, ETL staging, query folding, a data source
  connection (Excel, SharePoint, SQL), a partition definition, or a dCalendar/dim_Date script is
  being written or changed. Executes Stage 3 of the canonical flow.
---

# Power BI Partitions & Expressions Skill

> **CLI Policy (see `power-bi-dev`).** All ETL is authored **directly in TMDL files** in `*.SemanticModel/definition/` (`tables/*.tmdl`, `expressions.tmdl`). The CLI is used **only to read and validate data**.

> **Standard Flow (see `power-bi-dev`).** Executes **Stage 3 — ETL (Power Query M)**. Receives raw tables from Stage 2 profiling and shapes them into a **star schema**. Materialize flags, normalizations, type casts, and deterministic column derivations in M.

---

## Prerequisites (see `power-bi-dev` §4)

Run `pbi --version` before this session's first CLI call and install **only if it fails** — `power-bi-dev` §4 holds the single guarded check, the install sequence, and the PATH-failure notice. Never run a blind `pipx install`. Once the CLI answers, `pbi connect` to the model open in Desktop.

---

## SQL Source MCP Prerequisite

> **Mandatory (see `power-bi-dev` Stage 2).** Before profiling or connecting to a **SQL database source** (any M source using `Sql.Database`, `Sql.Databases`, or another engine's equivalent connector), verify the source's MCP server is installed and connected. Profile through the MCP, not raw ODBC/CLI calls, whenever one is available.

**Check first:** search available/deferred tools (`ToolSearch` with a query like `"mssql"`) or the project's MCP registration for a matching server before assuming one is missing.

### SQL Server — reference implementation (`mssql-mcp-server`)

1. **Install** (requires Node.js ≥ 20.0.0; this pulls `tedious`, `@modelcontextprotocol/sdk`, `zod`, `dotenv` as its own dependencies):
   ```bash
   npm install -g mssql-mcp-server
   ```
2. **Register** the server at project scope (`.mcp.json` or the project entry in `~/.claude.json`, `type: stdio`). Enable the extra query-execution tools if the project needs them — the server is read-only by design regardless:
   ```json
   {
     "mcpServers": {
       "mssql": {
         "type": "stdio",
         "command": "mssql-mcp-server",
         "env": {
           "MSSQL_ENABLE_EXECUTE_QUERY": "true"
         }
       }
     }
   }
   ```
3. **Connection string — always user-owned.** The server reads `MSSQL_CONNECTION_STRING` from a **user-level environment variable**. Claude Code never writes this value into any project file, `.mcp.json`, `.env`, or `CLAUDE.md`, and never asks the user to paste the raw string into chat. If the variable is missing, tell the user to set it themselves (e.g. `setx MSSQL_CONNECTION_STRING "..."` in their own terminal) and wait — this is a credential, covered by the standing rule against Claude entering or storing credentials.
4. **DDL/DML beyond the MCP's read-only tools:** the MCP is intentionally read-only. Schema/data changes go through the PowerShell `SqlServer` module instead:
   ```powershell
   Install-Module SqlServer -Scope CurrentUser
   ```
   (auto-installs the NuGet provider prerequisite), then use `Invoke-Sqlcmd` for the actual DDL/DML.

### Other SQL engines (PostgreSQL, MySQL, etc.)

This pack pins no MCP for engines other than SQL Server. Before falling back to CLI-only / M-only profiling, ask the user (`AskUserQuestion`) whether a community MCP server exists for that engine and should be installed the same way (search, install, register at project scope, confirm the credential is a user-owned environment variable). If the user declines or none exists, proceed with `pbi-cli`/M-based profiling.

---

## M / Power Query Code Standards

All M expressions written in TMDL partitions or named expressions follow these 4 rules:

### 1. Comment Every Step
Each step in a `let ... in` block has a `//` comment on the preceding line explaining **what** the step does and **why** (the business rule). Write comments in the **Project Artifact Language** selected during Stage 1 alignment.

### 2. Use Clear, Custom Step Names
Use descriptive step names that reflect the business operation (e.g., `FilteredSales2024`, `RemovedUnusedColumns`, `TypedDateColumn`) rather than generic Power Query defaults (`#"Filtered Rows"`, `#"Added Custom1"`). Avoid spaces where possible to keep code clean without `#"..."`.

### 3. Optimize Refresh Performance
Prioritize performance in this order of impact:
- **Preserve Query Folding:** Keep filters, column selections, and joins as early as possible so SQL sources execute the work server-side. Operations breaking query folding (index columns, `Table.Buffer`, custom M functions) must come AFTER folding steps.
- **Filter Rows Early:** for foldable sources (SQL), filter right after `Source`; for file sources (Excel/CSV/SharePoint), which do not fold, run the Shield/Scrub steps of the staging sequence below first.
- **Remove Unused Columns Early:** Use `Table.SelectColumns` early rather than `Table.RemoveColumns` at the end.
- **Single Type Transformation:** Apply column data types once in a single `Table.TransformColumnTypes` step near the end.

### 4. Explicitly Type Every Column
Every column loaded into the model gets an explicit data type in M (`Table.TransformColumnTypes`). A column left as type `any` loads as text, which breaks sorting, aggregation and relationships.

---

## M Code Pattern Example (Commented, Named, Optimized)

```tmdl
table fSales
	lineageTag: <unique-guid>

	partition fSales = m
		mode: import
		source =
			let
				// 1. Connect to shared SharePoint source query
				Source = _Source,

				// 2. Shield against Excel formula errors before any step reads the values (file sources do not fold)
				ShieldedErrors = Table.ReplaceErrorValues(Source, {{"Year", null}, {"RevenueAmount", null}, {"CostAmount", null}}),

				// 3. Filter raw data to target years
				FilteredYears = Table.SelectRows(ShieldedErrors, each [Year] >= 2024),

				// 4. Keep only columns required for star schema model
				SelectedColumns = Table.SelectColumns(FilteredYears, {"SaleID", "SaleDate", "CustomerID", "ProductID", "RevenueAmount", "CostAmount"}),

				// 5. Materialize deterministic flag in M (ETL over DAX)
				AddedHighValueFlag = Table.AddColumn(SelectedColumns, "IsHighValue", each if [RevenueAmount] >= 10000 then true else false, type logical),

				// 6. Explicitly type all loaded columns in a single step
				TypedColumns = Table.TransformColumnTypes(AddedHighValueFlag, {
					{"SaleID", Int64.Type},
					{"SaleDate", type date},
					{"CustomerID", Int64.Type},
					{"ProductID", Int64.Type},
					{"RevenueAmount", type number},
					{"CostAmount", type number},
					{"IsHighValue", type logical}
				})
			in
				TypedColumns
```

---

## Power Query Staging Sequence (Mandatory Order)

For raw file inputs (Excel/CSV/SharePoint):

1. **Shield:** `Table.ReplaceErrorValues(..., null)` on all columns immediately after sheet read.
2. **Scrub:** Map junk tokens (`{"-", "n/a", "na", "#value!", "#ref!", "#n/a", "#name?", "#div/0!", "#num!", "#null!", ",", ";", ""}`) to `null` for numeric/date columns.
3. **Normalize:** Standardize text spellings and business domain placeholders.
4. **Derive:** Materialize row-level flags, status columns, and categories in M.
5. **Cast:** Apply `Table.TransformColumnTypes` as the final step.
