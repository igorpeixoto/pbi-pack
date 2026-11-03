#!/usr/bin/env python
"""Build the visual reference from Microsoft's Power BI Visuals sample report.

    python scripts/build-visual-catalog.py import <folder>   copy a PBIP save of the report into reference/
    python scripts/build-visual-catalog.py catalog           regenerate the skill's catalog from reference/

The report is at github.com/microsoft/powerbi-desktop-samples, "Power BI Visuals report", MIT licensed. It ships
as a .pbix: open it in Desktop and save it as a Power BI Project to get the <folder> that `import` reads.

`import` leaves out every custom visual (their licenses are separate from the sample's), the containers that use
them, any page that leaves empty, and Desktop's local cache files, and it swaps the Power BI logo images for a
neutral placeholder (MIT doesn't grant trademark rights). `catalog` picks the smallest example of each visual type and feature and
copies it verbatim. Standard library only. Output is deterministic, and tests/test_visual_catalog.py checks it.
"""
import glob
import json
import os
import re
import shutil
import struct
import sys
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE = os.path.join(REPO, 'reference', 'power-bi-visuals')
CATALOG = os.path.join(REPO, 'skills', 'power-bi-visuals', 'references', 'visual-catalog')
REPORT = 'Power BI Visuals.Report'
TEXT = ('.json', '.tmdl', '.pbip', '.pbir', '.pbism', '.platform')
CURRENT_SCHEMA = 'visualContainer/2.14.0/'
LOGO_FILES = 'power_bi_*.png'
SOURCE = 'https://github.com/microsoft/powerbi-desktop-samples/tree/main/Power%20BI%20Visuals%20report'

MIT = '''MIT License

Copyright (c) Microsoft Corporation. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE
'''

REFERENCE_README = '''# Power BI Visuals sample report

Microsoft's sample report with a worked example of nearly every Power BI visual, plus pages on filtering,
conditional formatting, tooltips, analytics and visual calculations. Open it to browse them.

Source: [microsoft/powerbi-desktop-samples](%s), MIT licensed (see `LICENSE-MICROSOFT.txt`). Copyright belongs to
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
''' % SOURCE

CATALOG_INTRO = '''# Visual catalog

One small, working `visual.json` for each visual type and feature, copied verbatim from Microsoft's Power BI Visuals
sample report. Use them for Hard Rule 11: **read the matching file before writing that JSON, and change only entity,
property, literal and position.** Don't guess the shape.

- **The names are the sample's.** Tables like `Financials` don't exist in your model: rebind them to your own.
- **Copy mechanics, not policy.** Some examples set titles or colors on the visual; Hard Rule 14 and your theme
  still decide those. Group children keep positions relative to their group (Hard Rule 23).
- **Take `$schema` from your own report's visuals when it has any** (Hard Rule 10). A few examples carry older stamps.

Regenerate with `python scripts/build-visual-catalog.py catalog`; don't edit these files by hand. Source:
[microsoft/powerbi-desktop-samples](%s), MIT licensed, see `LICENSE-MICROSOFT.txt`. Copyright belongs to Microsoft.
A full copy to open in Desktop is in the pack's `reference/power-bi-visuals/`.
''' % SOURCE


def read(path):
    return open(path, encoding='utf-8-sig', newline='').read().replace('\r\n', '\n')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + '\n'


def import_report(source):
    if not os.path.isdir(os.path.join(source, REPORT)):
        sys.exit('no %s in %s' % (REPORT, source))
    # Build beside the current copy and swap at the end, so a failure or a locked file can't leave a half-deleted report
    work, previous = REFERENCE + '.new', REFERENCE + '.old'
    for leftover in (work, previous):
        if os.path.isdir(leftover):
            shutil.rmtree(leftover)

    def skip(folder, names):
        return [n for n in names if n in ('CustomVisuals', 'cache.abf', 'localSettings.json', 'Performance', '__pycache__')]
    os.makedirs(work)
    for name in sorted(os.listdir(source)):
        src = os.path.join(source, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(work, name), ignore=skip)
        elif name.endswith('.pbip'):
            shutil.copy(src, work)

    # Line endings as git will store them (Hard Rule 19), so a fresh import diffs clean
    for root, _, files in os.walk(work):
        for f in files:
            if f.endswith(TEXT):
                write(os.path.join(root, f), read(os.path.join(root, f)))

    report_json = os.path.join(work, REPORT, 'definition', 'report.json')
    rj = json.loads(read(report_json))
    packages = rj.get('resourcePackages', [])
    custom = set(rj.pop('publicCustomVisuals', [])) | {p['name'] for p in packages if p.get('type') == 'CustomVisual'}
    rj['resourcePackages'] = [p for p in packages if p.get('type') != 'CustomVisual']
    write(report_json, dump(rj))

    definition = os.path.join(work, REPORT, 'definition')
    removed, emptied = [], set()
    for f in glob.glob(os.path.join(definition, 'pages', '*', 'visuals', '*', 'visual.json')):
        visual_type = json.loads(read(f)).get('visual', {}).get('visualType')
        if visual_type in custom:
            emptied.add(f.replace(os.sep, '/').split('/')[-4])
            shutil.rmtree(os.path.dirname(f))
            removed.append(visual_type)
    pages = remove_empty_pages(definition, sorted(emptied))
    replace_logos(os.path.join(work, REPORT))
    write(os.path.join(work, 'README.md'), REFERENCE_README)
    write(os.path.join(work, 'LICENSE-MICROSOFT.txt'), MIT)
    if os.path.isdir(REFERENCE):
        os.rename(REFERENCE, previous)
    os.rename(work, REFERENCE)
    if os.path.isdir(previous):
        shutil.rmtree(previous)
    print('imported to %s: %d custom visual types excluded, %d containers removed, %d pages left' % (
        REFERENCE, len(custom), len(removed), len(pages)))


def placeholder_png(size=64, gray=0x9A):
    """A plain square PNG, built here so the repo needs no image library."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = (b'\x00' + bytes([gray]) * size) * size
    header = struct.pack('>IIBBBBB', size, size, 8, 0, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b'')


def replace_logos(report_dir):
    for path in glob.glob(os.path.join(report_dir, 'StaticResources', 'RegisteredResources', LOGO_FILES)):
        with open(path, 'wb') as f:
            f.write(placeholder_png())


def remove_empty_pages(definition, candidates):
    """Drop pages that no longer show data, and repoint the arrows that led to them at the page beyond."""
    meta_path = os.path.join(definition, 'pages', 'pages.json')
    meta = json.loads(read(meta_path))
    for page_id in candidates:
        visuals = [json.loads(read(f)) for f in glob.glob(os.path.join(definition, 'pages', page_id, 'visuals', '*', 'visual.json'))]
        if any('query' in v.get('visual', {}) for v in visuals):
            continue
        order = meta['pageOrder']
        at = order.index(page_id)
        for other in order:
            if other == page_id:
                continue
            beyond = order[at + 1] if order.index(other) < at else order[at - 1]
            for f in glob.glob(os.path.join(definition, 'pages', other, 'visuals', '*', 'visual.json')):
                text = read(f)
                if page_id in text:
                    write(f, text.replace(page_id, beyond))
        order.remove(page_id)
        for pointer in ('activePageName', 'landingPageName'):
            if meta.get(pointer) == page_id:
                meta[pointer] = order[0]
        shutil.rmtree(os.path.join(definition, 'pages', page_id))
    write(meta_path, dump(meta))
    return meta['pageOrder']


def has(*needles):
    return lambda text: all(n in text for n in needles)


def matches(pattern):
    return lambda text: re.search(pattern, text) is not None


def filter_type(kind):
    return lambda text: any(x.get('type') == kind for x in (json.loads(text).get('filterConfig') or {}).get('filters', []))


def button_action(kind):
    return has('"actionButton"', '"visualLink"', "'%s'" % kind)


FEATURES = [
    ('cf-gradient', 'Conditional format: color scale from a measure', has('linearGradient')),
    ('cf-rules', 'Conditional format: if/then rules', has('"Conditional"', '"Cases"')),
    ('cf-measure-color', 'Conditional format: color taken from a measure', matches(r'"color":\s*\{\s*"expr":\s*\{\s*"Measure"')),
    ('filter-categorical', 'Visual-level categorical filter', filter_type('Categorical')),
    ('filter-advanced', 'Visual-level advanced filter', filter_type('Advanced')),
    ('slicer-single-select', 'Slicer limited to one value', has('strictSingleSelect')),
    ('slicer-dropdown', 'Slicer in dropdown mode', has('"slicer"', "'Dropdown'")),
    ('slicer-date-range', 'Slicer in date-range mode', has('"slicer"', "'Between'")),
    ('button-text', 'Button with its own text (`show` and `text` sit in separate entries)',
     lambda text: '"actionButton"' in text and bool(json.loads(text)['visual'].get('objects', {}).get('text'))),
    ('button-page-navigation', 'Button that opens a page', button_action('PageNavigation')),
    ('button-web-url', 'Button that opens a URL', button_action('WebUrl')),
    ('button-apply-slicers', 'Button that applies all slicers', button_action('ApplyAllSlicers')),
    ('button-clear-slicers', 'Button that clears all slicers', button_action('ClearAllSlicers')),
    ('button-bookmark', 'Button that applies a bookmark', button_action('Bookmark')),
    ('small-multiples', 'Chart split into small multiples', has('smallMultiplesLayout')),
    ('reference-line', 'Chart with a reference line', has('y1AxisReferenceLine')),
    ('visual-calculation', 'Visual calculation', has('NativeVisualCalculation')),
    ('field-parameter', 'Visual bound to a field parameter', has('"Field parameter"')),
    ('tooltip-page-link', 'Visual whose tooltip is a report page', matches(r'"visualTooltip":\s*\[[^\]]*"section"')),
    ('matrix-expanded', 'Matrix with saved expansion state', has('"pivotTable"', 'expansionStates')),
    ('slicer-hierarchy', 'Hierarchy slicer with saved expansion state', has('"slicer"', 'expansionStates')),
    ('hidden-visual', 'Visual hidden on the page', has('"isHidden"')),
    ('title-subtitle', 'Title and subtitle set on one visual', has('"subTitle"', '"title"')),
]


def smallest(candidates):
    """Prefer the current $schema stamp, then the shortest example; the path breaks ties, so output is stable."""
    return min(candidates, key=lambda c: (CURRENT_SCHEMA not in c[1], len(c[1]), c[0]))


def build_catalog(out=CATALOG):
    definition = os.path.join(REFERENCE, REPORT, 'definition')
    pages_meta = json.loads(read(os.path.join(definition, 'pages', 'pages.json')))
    page_names, visuals, by_type = {}, [], {}
    for page_id in pages_meta['pageOrder']:
        page = json.loads(read(os.path.join(definition, 'pages', page_id, 'page.json')))
        page_names[page_id] = page['displayName']
        for f in sorted(glob.glob(os.path.join(definition, 'pages', page_id, 'visuals', '*', 'visual.json'))):
            text = read(f)
            visuals.append((page_id, text))
            container = json.loads(text)
            kind = container.get('visual', {}).get('visualType') or ('visualGroup' if 'visualGroup' in container else None)
            # A chart with no bound fields teaches nothing about its wells
            if kind and ('query' in container.get('visual', {}) or kind not in by_type):
                by_type.setdefault(kind, []).append((page_id, text))

    files = {}
    rows_types, rows_features, rows_other = [], [], []
    for kind in sorted(by_type, key=str.lower):
        page_id, text = smallest(by_type[kind])
        files['%s.json' % kind] = text
        rows_types.append((kind, '%s.json' % kind, page_names[page_id]))
    for name, label, test in FEATURES:
        hits = [v for v in visuals if test(v[1])]
        if hits:
            page_id, text = smallest(hits)
            files['features/%s.json' % name] = text
            rows_features.append((label, 'features/%s.json' % name, page_names[page_id]))
        else:
            rows_other.append(label)

    page_examples = [('page-tooltip', 'Tooltip page', lambda p: p.get('type') == 'Tooltip'),
                     ('page-interactions', 'Page with edited visual interactions and a page filter',
                      lambda p: 'visualInteractions' in p)]
    for name, label, test in page_examples:
        for page_id in pages_meta['pageOrder']:
            raw = read(os.path.join(definition, 'pages', page_id, 'page.json'))
            if test(json.loads(raw)):
                files['features/%s.json' % name] = raw
                rows_features.append((label, 'features/%s.json' % name, page_names[page_id]))
                break
    bookmarks = sorted(glob.glob(os.path.join(definition, 'bookmarks', '*.bookmark.json')))
    if bookmarks:
        files['features/bookmark.json'] = read(min(bookmarks, key=lambda b: (len(read(b)), b)))
        rows_features.append(('Bookmark definition', 'features/bookmark.json', '-'))

    def table(heading, first, rows):
        lines = ['## %s' % heading, '', '| %s | File | Sample page |' % first, '|---|---|---|']
        lines += ['| %s | [`%s`](%s) | %s |' % (a, b, b, c) for a, b, c in rows]
        return '\n'.join(lines) + '\n'

    index = CATALOG_INTRO + '\n' + table('Visual types', 'visualType', [('`%s`' % a, b, c) for a, b, c in rows_types])
    index += '\n' + table('Features', 'Feature', rows_features)
    if rows_other:
        index += '\nThe sample has no example of: %s.\n' % '; '.join(rows_other)
    index += '\nThe sample has no Top N filter either: the demo template\'s `Top 10 products` chart has one (see `power-bi-filters`).\n'
    files['README.md'] = index
    files['LICENSE-MICROSOFT.txt'] = MIT

    if os.path.isdir(out):
        shutil.rmtree(out)
    for name, text in files.items():
        write(os.path.join(out, *name.split('/')), text)
    return files


def main(argv):
    if len(argv) == 2 and argv[0] == 'import':
        import_report(argv[1])
    elif len(argv) == 1 and argv[0] == 'catalog':
        files = build_catalog()
        print('catalog: %d files, %.0f KB' % (len(files), sum(len(t.encode('utf-8')) for t in files.values()) / 1024))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
