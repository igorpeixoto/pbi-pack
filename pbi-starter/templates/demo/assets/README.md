# Brand assets

Input for `apply_brand.py` (see `power-bi-themes`, "Brand Assets & `apply_brand.py`"). Close Power BI Desktop first.

- `brand.json`: what the report should look like. Edit this one.
- `brand.applied.json`: what the report contains now. The tool writes it; don't edit it by hand.

```sh
# Git Bash, from the project root
python ~/.claude/skills/power-bi-themes/scripts/apply_brand.py . --dry-run
python ~/.claude/skills/power-bi-themes/scripts/apply_brand.py . --preview
```

```powershell
# PowerShell, from the project root
python "$HOME\.claude\skills\power-bi-themes\scripts\apply_brand.py" . --dry-run
python "$HOME\.claude\skills\power-bi-themes\scripts\apply_brand.py" . --preview
```

`--preview` writes `assets/preview.html`, a static page with no data. Open it in a browser to check the colors,
then validate in Desktop.
