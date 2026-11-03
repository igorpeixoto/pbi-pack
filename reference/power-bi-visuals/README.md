# Power BI Visuals sample report

Microsoft's sample report with a worked example of nearly every Power BI visual, plus pages on filtering,
conditional formatting, tooltips, analytics and visual calculations. Open it to browse them.

Source: [microsoft/powerbi-desktop-samples](https://github.com/microsoft/powerbi-desktop-samples/tree/main/Power%20BI%20Visuals%20report), MIT licensed (see `LICENSE-MICROSOFT.txt`). Copyright belongs to
Microsoft; this pack doesn't claim it. Upstream it's a `.pbix`; this copy was saved as a Power BI Project.

**Changed from the original:**

- Every custom visual is gone, because their licenses are separate from the sample's: the four containers that used
  them, the two embedded packages (`CustomVisuals/`) and the three marketplace references.
- The `Custom` page held only those visuals, so it's gone too, and the `Other` page's Next arrow now skips it.
- The Power BI logo images are replaced by a plain gray placeholder, because MIT doesn't grant trademark rights. The
  file names stay, so the image buttons on the `Other` page still work as examples.

`scripts/build-visual-catalog.py` makes this copy; don't edit it by hand.

**To open it:** open `Power BI Visuals.pbip` in Power BI Desktop. Its data lives in DAX calculated tables in the
model, so it needs no data source or setup.

**Use it for mechanics, not policy.** It relies on calculated tables and sets titles visual by visual, which this
pack's Hard Rules 2 and 14 steer away from. Claude reads the extracted examples in
`skills/power-bi-visuals/references/visual-catalog/`, not this report.
