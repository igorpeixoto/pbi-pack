# Visual catalog

One small, working `visual.json` for each visual type and feature, copied verbatim from Microsoft's Power BI Visuals
sample report. Use them for Hard Rule 11: **read the matching file before writing that JSON, and change only entity,
property, literal and position.** Don't guess the shape.

- **The names are the sample's.** Tables like `Financials` don't exist in your model: rebind them to your own.
- **Copy mechanics, not policy.** Some examples set titles or colors on the visual; Hard Rule 14 and your theme
  still decide those. Group children keep positions relative to their group (Hard Rule 23).
- **Take `$schema` from your own report's visuals when it has any** (Hard Rule 10). A few examples carry older stamps.

Regenerate with `python scripts/build-visual-catalog.py catalog`; don't edit these files by hand. Source:
[microsoft/powerbi-desktop-samples](https://github.com/microsoft/powerbi-desktop-samples/tree/main/Power%20BI%20Visuals%20report), MIT licensed, see `LICENSE-MICROSOFT.txt`. Copyright belongs to Microsoft.
A full copy to open in Desktop is in the pack's `reference/power-bi-visuals/`.

## Visual types

| visualType | File | Sample page |
|---|---|---|
| `actionButton` | [`actionButton.json`](actionButton.json) | Bars |
| `advancedSlicerVisual` | [`advancedSlicerVisual.json`](advancedSlicerVisual.json) | Conditional formatting |
| `aiNarratives` | [`aiNarratives.json`](aiNarratives.json) | AI-powered |
| `areaChart` | [`areaChart.json`](areaChart.json) | Area |
| `azureMap` | [`azureMap.json`](azureMap.json) | Maps |
| `barChart` | [`barChart.json`](barChart.json) | Filtering |
| `bookmarkNavigator` | [`bookmarkNavigator.json`](bookmarkNavigator.json) | Filtering |
| `cardVisual` | [`cardVisual.json`](cardVisual.json) | Cards or callouts |
| `clusteredBarChart` | [`clusteredBarChart.json`](clusteredBarChart.json) | Bars |
| `clusteredColumnChart` | [`clusteredColumnChart.json`](clusteredColumnChart.json) | Columns |
| `columnChart` | [`columnChart.json`](columnChart.json) | Columns |
| `decompositionTreeVisual` | [`decompositionTreeVisual.json`](decompositionTreeVisual.json) | AI-powered |
| `donutChart` | [`donutChart.json`](donutChart.json) | Report 1 |
| `funnel` | [`funnel.json`](funnel.json) | Part-to-whole |
| `ganttChart` | [`ganttChart.json`](ganttChart.json) | Gantt |
| `gauge` | [`gauge.json`](gauge.json) | Part-to-whole |
| `hundredPercentStackedAreaChart` | [`hundredPercentStackedAreaChart.json`](hundredPercentStackedAreaChart.json) | Area |
| `hundredPercentStackedBarChart` | [`hundredPercentStackedBarChart.json`](hundredPercentStackedBarChart.json) | Bars |
| `image` | [`image.json`](image.json) | Other |
| `keyDriversVisual` | [`keyDriversVisual.json`](keyDriversVisual.json) | AI-powered |
| `kpi` | [`kpi.json`](kpi.json) | Cards or callouts |
| `lineChart` | [`lineChart.json`](lineChart.json) | Lines |
| `lineClusteredColumnComboChart` | [`lineClusteredColumnComboChart.json`](lineClusteredColumnComboChart.json) | Combo |
| `lineStackedColumnComboChart` | [`lineStackedColumnComboChart.json`](lineStackedColumnComboChart.json) | Combo |
| `listSlicer` | [`listSlicer.json`](listSlicer.json) | Filtering |
| `pageNavigator` | [`pageNavigator.json`](pageNavigator.json) | Bars |
| `pieChart` | [`pieChart.json`](pieChart.json) | Part-to-whole |
| `pivotTable` | [`pivotTable.json`](pivotTable.json) | Report 1 |
| `ribbonChart` | [`ribbonChart.json`](ribbonChart.json) | Ribbon & Waterfall |
| `scatterChart` | [`scatterChart.json`](scatterChart.json) | Analytics |
| `shape` | [`shape.json`](shape.json) | Filtering |
| `shapeMap` | [`shapeMap.json`](shapeMap.json) | Maps |
| `slicer` | [`slicer.json`](slicer.json) | Filtering |
| `stackedAreaChart` | [`stackedAreaChart.json`](stackedAreaChart.json) | Area |
| `tableEx` | [`tableEx.json`](tableEx.json) | Table & Matrix |
| `textbox` | [`textbox.json`](textbox.json) | Bars |
| `textSlicer` | [`textSlicer.json`](textSlicer.json) | Filtering |
| `treemap` | [`treemap.json`](treemap.json) | Part-to-whole |
| `visualGroup` | [`visualGroup.json`](visualGroup.json) | Bars |
| `waterfallChart` | [`waterfallChart.json`](waterfallChart.json) | Ribbon & Waterfall |

## Features

| Feature | File | Sample page |
|---|---|---|
| Conditional format: color scale from a measure | [`features/cf-gradient.json`](features/cf-gradient.json) | Conditional formatting |
| Conditional format: if/then rules | [`features/cf-rules.json`](features/cf-rules.json) | Conditional formatting |
| Conditional format: color taken from a measure | [`features/cf-measure-color.json`](features/cf-measure-color.json) | Conditional formatting |
| Visual-level categorical filter | [`features/filter-categorical.json`](features/filter-categorical.json) | Other |
| Visual-level advanced filter | [`features/filter-advanced.json`](features/filter-advanced.json) | Filtering |
| Slicer limited to one value | [`features/slicer-single-select.json`](features/slicer-single-select.json) | Report 2 |
| Slicer in dropdown mode | [`features/slicer-dropdown.json`](features/slicer-dropdown.json) | Filtering |
| Slicer in date-range mode | [`features/slicer-date-range.json`](features/slicer-date-range.json) | Filtering |
| Button with its own text (`show` and `text` sit in separate entries) | [`features/button-text.json`](features/button-text.json) | Filtering |
| Button that opens a page | [`features/button-page-navigation.json`](features/button-page-navigation.json) | Other |
| Button that opens a URL | [`features/button-web-url.json`](features/button-web-url.json) | Filtering |
| Button that applies all slicers | [`features/button-apply-slicers.json`](features/button-apply-slicers.json) | Filtering |
| Button that clears all slicers | [`features/button-clear-slicers.json`](features/button-clear-slicers.json) | Filtering |
| Chart split into small multiples | [`features/small-multiples.json`](features/small-multiples.json) | Ribbon & Waterfall |
| Chart with a reference line | [`features/reference-line.json`](features/reference-line.json) | Analytics |
| Visual calculation | [`features/visual-calculation.json`](features/visual-calculation.json) | Visual calcs |
| Visual bound to a field parameter | [`features/field-parameter.json`](features/field-parameter.json) | Report 2 |
| Visual whose tooltip is a report page | [`features/tooltip-page-link.json`](features/tooltip-page-link.json) | Tooltips |
| Matrix with saved expansion state | [`features/matrix-expanded.json`](features/matrix-expanded.json) | Report 1 |
| Hierarchy slicer with saved expansion state | [`features/slicer-hierarchy.json`](features/slicer-hierarchy.json) | Filtering |
| Visual hidden on the page | [`features/hidden-visual.json`](features/hidden-visual.json) | Filtering |
| Title and subtitle set on one visual | [`features/title-subtitle.json`](features/title-subtitle.json) | Analytics |
| Tooltip page | [`features/page-tooltip.json`](features/page-tooltip.json) | Tooltip report page |
| Page with edited visual interactions and a page filter | [`features/page-interactions.json`](features/page-interactions.json) | Report 2 |
| Bookmark definition | [`features/bookmark.json`](features/bookmark.json) | - |

The sample has no example of: Button that applies a bookmark.

The sample has no Top N filter either: the demo template's `Top 10 products` chart has one (see `power-bi-filters`).
