---
name: power-bi-pages
description: >
  Manages report pages, bookmarks, page visibility, navigation, tooltip pages, and drillthrough in
  PBIR reports. Invoke whenever a new page, page rename or reorder, bookmark, page navigation
  button, hidden page, tooltip page, or drillthrough target is requested.
---

# Power BI Pages Skill

> **Authoring Policy (see `power-bi-dev`).** Edit `page.json` files directly in `pages/<pageId>/page.json`.

---

## Page JSON Structure (`page.json`)

```json
{
  "$schema": "<copy verbatim from a sibling page.json in this report — Hard Rule #10>",
  "name": "Page_ExecutiveSummary",
  "displayName": "Executive Summary",
  "displayOption": "FitToPage",
  "width": 1920,
  "height": 1080
}
```

---

## Tooltip & Drillthrough Page Rules

- **Tooltip Pages:** Use plain column filters on tooltip pages. Avoid measures with `SELECTEDVALUE` as tooltip page filters, as hover contexts can return BLANK and empty the tooltip container.
- **Page Layout Selection:** Ask the user (`AskUserQuestion`) before arranging elements on a new page to confirm navigation bar position and card placement.
- **Working examples:** `power-bi-visuals`' catalog has a tooltip `page.json` (`references/visual-catalog/features/page-tooltip.json`), a visual wired to it (`features/tooltip-page-link.json`), a bookmark (`features/bookmark.json`) and a page-navigation button (`features/button-page-navigation.json`).
- **Show/hide bookmarks record every visual's visibility.** A visual you unhide after a bookmark was recorded is hidden again the next time that bookmark runs. After showing a visual on a page that has show/hide bookmarks, *Update* each of them in Desktop; this is the one step that breaks the toggle when skipped.
