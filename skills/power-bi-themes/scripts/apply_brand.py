#!/usr/bin/env python
"""Apply a client brand to a PBIP report from the project's assets/ folder.

    python apply_brand.py <project-root> [--dry-run] [--preview]

Reads:
  assets/brand.json          what the report SHOULD look like (colors by role, fonts, logos,
                             title, parameters, literal colors, provenance)
  assets/brand.applied.json  what the report CURRENTLY contains (theme file, logo item names,
                             title, literal colors). Written back after every run. A project
                             that predates the tool gets a hand-written one describing its
                             current state (see power-bi-themes, "Brand assets & apply-brand").

Does, in order:
  1. theme     builds the theme from theme.base.json (next to this script, or
               assets/theme.base.json when the project overrides it) or takes
               assets/theme.override.json (the client's theme, with the role colors written
               into dataColors positions 0/1/2/3/7); either way the Hard Rule 14 baselines are
               enforced; registers it in report.json and removes the previous theme file
  2. logos     copies each assets/logos slot file into RegisteredResources under a stable
               slot name, repoints every visual that used the old item, sets image scaling to
               Fit (so a differently shaped logo is never cropped or stretched), removes the
               old file
  3. literals  swaps hard-coded hex literals in visual.json (static fills and conditional
               formatting values alike - the value only, never the rule structure)
  4. title     replaces the header title text
  5. model     sets Project_PK / Schema in expressions.tmdl and the _Brand_<role> color
               measures (e.g. the SVG progress bars) in the model's tables
  6. contrast  checks the fill/text pairs the report actually uses and warns below WCAG AA

Touches only files under <project>/<Name>.Report, expressions.tmdl, and _Brand_* measure lines in tables/*.tmdl.
Line endings of every edited file are preserved. Nothing is committed.
"""
import copy
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CRLF = '\r\n'

# Theme color contract of the full-report template family. Visuals reference theme colors through
# ThemeDataColor ids, and Power BI numbers them: id 0 = theme `background`, id 1 = theme
# `foreground`, id n >= 2 = dataColors[n - 2]. So a brand color is placed by role, never by taste.
#   id 0  background (colors.surface)  nav buttons (at -10 %), slicer boxes
#   id 1  foreground (colors.text)     nav button text, labels
#   dataColors[0] (id 2) primary       current-page nav button, "open" series, card accents
#   dataColors[1] (id 3) secondary     card labels, second series
#   dataColors[2] (id 4) accent        light accent (free for the brand; no fixed use)
#   dataColors[3] (id 5) neutral_dark  section divider bars, some column fills
#   dataColors[5] (id 7) header        header bar, slicer backgrounds, "completed" series
#   dataColors[7] (id 9) neutral_mid   "total" series, +60 % chart backgrounds
#   dataColors[4], [6], [8], [9], 10+  series
POSITIONS = {0: 'primary', 1: 'secondary', 2: 'accent', 3: 'neutral_dark', 5: 'header', 7: 'neutral_mid'}
SERIES_SLOTS = [4, 6, 8, 9]

# Power BI Desktop and the Service render only these families; anything else silently falls back.
PBI_FONTS = {'Segoe UI', 'Segoe UI Semibold', 'Segoe UI Bold', 'Segoe UI Light', 'Arial', 'Arial Black',
             'Calibri', 'Cambria', 'Candara', 'Consolas', 'Constantia', 'Corbel', 'Courier New', 'DIN',
             'Georgia', 'Lucida Sans Unicode', 'Tahoma', 'Times New Roman', 'Trebuchet MS', 'Verdana'}

# Header icons stay ON for these (Hard Rule 14): tables, matrices, charts.
HEADER_ON = ['tableEx', 'pivotTable', 'lineChart', 'areaChart', 'stackedAreaChart', 'hundredPercentStackedAreaChart',
             'barChart', 'clusteredBarChart', 'hundredPercentStackedBarChart', 'columnChart', 'clusteredColumnChart',
             'hundredPercentStackedColumnChart', 'lineStackedColumnComboChart', 'lineClusteredColumnComboChart',
             'ribbonChart', 'waterfallChart', 'funnel', 'scatterChart', 'pieChart', 'donutChart', 'treemap', 'map',
             'filledMap', 'gauge', 'kpi', 'decompositionTreeVisual', 'keyDriversVisual']


def die(msg):
    sys.exit('apply-brand: ' + msg)


def read(path):
    raw = open(path, encoding='utf-8', newline='').read()
    return raw.replace(CRLF, '\n'), CRLF in raw


def write(path, text, crlf, dry):
    if dry:
        return
    open(path, 'w', encoding='utf-8', newline='').write(text.replace('\n', CRLF) if crlf else text)


def dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


# --- color helpers --------------------------------------------------------------------------

def rgb(h):
    h = h.lstrip('#')
    if not re.fullmatch(r'[0-9A-Fa-f]{6}', h):
        die('not a #RRGGBB color: #' + h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(c):
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    """t=0 -> a, t=1 -> b"""
    a, b = rgb(a), rgb(b)
    return hexc(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def shade(h, pct):
    """Power BI ThemeDataColor Percent: >0 lightens toward white, <0 darkens toward black."""
    return mix(h, '#FFFFFF', pct) if pct >= 0 else mix(h, '#000000', -pct)


def lum(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# --- brand resolution -----------------------------------------------------------------------

def resolve_colors(brand):
    c = dict(brand.get('colors') or {})
    for need in ('primary', 'secondary', 'accent', 'text'):
        if not c.get(need):
            die('brand.json colors.%s is required' % need)
    c.setdefault('surface', '#FFFFFF')
    c.setdefault('on_dark', '#FFFFFF')
    c.setdefault('page', mix(c['primary'], '#FFFFFF', 0.94))
    c.setdefault('row_alt', mix(c['primary'], '#FFFFFF', 0.96))
    c.setdefault('text_muted', mix(c['text'], '#FFFFFF', 0.25))
    c.setdefault('border', '#E0E0E0')
    c.setdefault('outspace', '#EEEEEE')
    c.setdefault('outspace_pane', '#F5F5F5')
    c.setdefault('shape_fill', '#D0D0D0')
    c.setdefault('header', c['primary'])
    c.setdefault('table_header', c['text'])
    c.setdefault('neutral_dark', c['text'])
    c.setdefault('neutral_mid', mix(c['text'], '#FFFFFF', 0.45))
    c.setdefault('good', '#2F8F6D')
    c.setdefault('bad', '#D64545')
    c.setdefault('neutral', c['neutral_mid'])
    c.setdefault('center', mix(c['neutral_mid'], '#FFFFFF', 0.4))
    c.setdefault('progress_end', c['secondary'])
    c.setdefault('progress_start', shade(c['progress_end'], -0.25))
    c.setdefault('progress_track', c['accent'])
    for k, v in c.items():
        if k != 'series':
            c[k] = hexc(rgb(v))
    series = [hexc(rgb(s)) for s in (c.get('series') or [])]
    if len(series) < len(SERIES_SLOTS):
        die('brand.json colors.series needs at least %d colors (dataColors slots %s)' % (len(SERIES_SLOTS), SERIES_SLOTS))
    c['series'] = series
    return c


def data_colors(c):
    out = [None] * 10
    for pos, role in POSITIONS.items():
        out[pos] = c[role]
    for pos, s in zip(SERIES_SLOTS, c['series'], strict=False):
        out[pos] = s
    return out + c['series'][len(SERIES_SLOTS):]


def resolve_fonts(brand):
    f = dict(brand.get('fonts') or {})
    report = f.get('report', 'Segoe UI')
    semibold = f.get('report_semibold', 'Segoe UI Semibold')
    for name in (report, semibold):
        if name not in PBI_FONTS:
            die('fonts.report "%s" is not a Power BI font - keep the brand font in fonts.brand and pick a '
                'fallback from: %s' % (name, ', '.join(sorted(PBI_FONTS))))
    return report, semibold


# --- theme ----------------------------------------------------------------------------------

def enforce_baselines(theme, custom_on):
    vs = theme.setdefault('visualStyles', {})
    star = vs.setdefault('*', {}).setdefault('*', {})
    star['title'] = [dict((star.get('title') or [{}])[0], show=False)]
    star['visualHeader'] = [dict((star.get('visualHeader') or [{}])[0], show=False)]
    for v in HEADER_ON + list(custom_on):
        entry = vs.setdefault(v, {}).setdefault('*', {})
        entry['visualHeader'] = [dict((entry.get('visualHeader') or [{}])[0], show=True)]
    grp = vs.setdefault('group', {}).setdefault('*', {})
    grp['background'] = [{'show': False}]
    grp['visualHeader'] = [{'show': False}]
    return theme


def build_theme(project, brand, c):
    override = os.path.join(project, 'assets', 'theme.override.json')
    if os.path.exists(override):
        theme = json.load(open(override, encoding='utf-8-sig'))
        theme['name'] = brand.get('theme_name') or theme.get('name') or brand['client']
        # The client's palette order means nothing to this report: the visuals read positions
        # 0/1/2/3/7 by role. Keep the client's colors, but put the roles where the report looks.
        dc = list(theme.get('dataColors') or [])
        dc += [None] * max(0, 10 - len(dc))
        for pos, role in POSITIONS.items():
            if dc[pos] and dc[pos].upper() != c[role].upper():
                print('NOTE       theme.override.json dataColors[%d] %s replaced by colors.%s %s' % (pos, dc[pos], role, c[role]))
            dc[pos] = c[role]
        for pos, s in zip(SERIES_SLOTS, c['series'], strict=False):
            dc[pos] = dc[pos] or s
        theme['dataColors'] = dc
    else:
        base = os.path.join(project, 'assets', 'theme.base.json')
        if not os.path.exists(base):
            base = os.path.join(HERE, 'theme.base.json')
        text = open(base, encoding='utf-8').read()
        font, semibold = resolve_fonts(brand)
        tokens = dict((k, v) for k, v in c.items() if k != 'series')
        tokens.update(font=font, font_semibold=semibold, name=brand.get('theme_name') or brand['client'])
        theme = json.loads(text)
        theme.pop('$comment', None)

        def fill(o):
            if isinstance(o, dict):
                return dict((k, fill(v)) for k, v in o.items())
            if isinstance(o, list):
                return [fill(v) for v in o]
            if isinstance(o, str):
                m = re.fullmatch(r'\{([a-z_]+)\}', o)
                if m:
                    if m.group(1) not in tokens:
                        die('theme base uses {%s}, which brand.json does not resolve' % m.group(1))
                    return tokens[m.group(1)]
            return o
        theme = fill(theme)
        theme['name'] = brand.get('theme_name') or brand['client']
        theme['dataColors'] = data_colors(c)
    return enforce_baselines(theme, brand.get('header_icons_on') or [])


def slug(s):
    s = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')
    return s or 'brand'


# --- report helpers -------------------------------------------------------------------------

def find_one(project, pattern):
    hits = glob.glob(os.path.join(project, pattern))
    if len(hits) != 1:
        die('expected exactly one %s in %s, found %d' % (pattern, project, len(hits)))
    return hits[0]


def registered(report_json):
    for pkg in report_json.get('resourcePackages', []):
        if pkg.get('name') == 'RegisteredResources':
            return pkg
    die('report.json has no RegisteredResources package')


def visual_files(report_dir):
    return glob.glob(os.path.join(report_dir, 'definition', 'pages', '*', 'visuals', '*', 'visual.json'))


def replace_in_visuals(report_dir, pairs, dry, flags=0):
    """pairs: list of (regex, replacement). Returns number of files changed."""
    n = 0
    for f in visual_files(report_dir):
        s, cr = read(f)
        new = s
        for pat, rep in pairs:
            new = re.sub(pat, rep, new, flags=flags)
        if new != s:
            write(f, new, cr, dry)
            n += 1
    return n


def contrast_pairs(c):
    """(label, fg, bg, required ratio, actual ratio) for the fill/text pairs the report renders."""
    pairs = [('nav text on nav button', c['text'], shade(c['surface'], -0.1), 4.5),
             ('current-page nav text on primary', c['surface'], c['primary'], 4.5),
             ('header title on header bar', c['on_dark'], c['header'], 3.0),
             ('current-page button on header bar', c['primary'], c['header'], 1.5),
             ('table header text', c['on_dark'], c['table_header'], 4.5),
             ('table total text', c['on_dark'], c['primary'], 4.5),
             ('body text on page', c['text'], c['page'], 4.5),
             ('body text on surface', c['text'], c['surface'], 4.5)]
    return [(label, f, b, n, contrast(f, b)) for label, f, b, n in pairs]


def json_block(text, key):
    """Yield (start, end) spans of every `"key": [...]` / `"key": {...}` value in raw JSON text."""
    for m in re.finditer(r'"%s":\s*([\[{])' % re.escape(key), text):
        depth, i, in_str = 0, m.start(1), False
        while i < len(text):
            ch = text[i]
            if in_str:
                if ch == '\\':
                    i += 1
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch in '[{':
                depth += 1
            elif ch in ']}':
                depth -= 1
                if depth == 0:
                    yield m.start(1), i + 1
                    break
            i += 1


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    dry = '--dry-run' in argv
    if len(args) != 1:
        die('usage: apply_brand.py <project-root> [--dry-run] [--preview]')
    project = os.path.abspath(args[0])
    assets = os.path.join(project, 'assets')
    brand_path = os.path.join(assets, 'brand.json')
    applied_path = os.path.join(assets, 'brand.applied.json')
    if not os.path.exists(brand_path):
        die('no assets/brand.json in ' + project)
    if not os.path.exists(applied_path):
        die('no assets/brand.applied.json - describe what the report contains now before the first run')
    brand = json.load(open(brand_path, encoding='utf-8-sig'))
    applied = json.load(open(applied_path, encoding='utf-8-sig'))
    for k in ('client', 'title'):
        if not brand.get(k):
            die('brand.json %s is required' % k)

    report_dir = find_one(project, '*.Report')
    model_dir = find_one(project, '*.SemanticModel')
    res_dir = os.path.join(report_dir, 'StaticResources', 'RegisteredResources')
    rj_path = os.path.join(report_dir, 'definition', 'report.json')
    rj_text, rj_cr = read(rj_path)
    rj = json.loads(rj_text)
    pkg = registered(rj)
    items = pkg['items']
    log = []
    new_applied = copy.deepcopy(applied)
    to_remove = []

    # 1. theme
    c = resolve_colors(brand)
    theme = build_theme(project, brand, c)
    theme_item = slug(theme['name']) + '.json'
    old_theme = applied.get('theme') or rj.get('themeCollection', {}).get('customTheme', {}).get('name')
    write(os.path.join(res_dir, theme_item), dump(theme) + '\n', False, dry)
    if old_theme and old_theme != theme_item:
        items[:] = [i for i in items if i['name'] != old_theme]
        to_remove.append(os.path.join(res_dir, old_theme))
    if not any(i['name'] == theme_item for i in items):
        items.append({'name': theme_item, 'path': theme_item, 'type': 'CustomTheme'})
    collection = rj.setdefault('themeCollection', {})
    custom = collection.setdefault('customTheme', {})
    custom.update(name=theme_item, type='RegisteredResources')
    # Desktop refuses to open a customTheme with no reportVersionAtImport; a report's first custom
    # theme has none yet, so it takes the base theme's.
    base_version = collection.get('baseTheme', {}).get('reportVersionAtImport')
    if base_version:
        custom.setdefault('reportVersionAtImport', base_version)
    new_applied['theme'] = theme_item
    log.append('theme      %s -> %s (%d dataColors)' % (old_theme, theme_item, len(theme.get('dataColors', []))))

    # 2. logos
    logos = brand.get('logos') or {}
    cur_logos = dict(applied.get('logos') or {})
    for slot, src_rel in logos.items():
        src = os.path.join(assets, src_rel)
        if not os.path.exists(src):
            die('logos.%s points at %s, which does not exist' % (slot, src_rel))
        ext = os.path.splitext(src)[1].lower()
        new_item = slot + ext
        old_item = cur_logos.get(slot)
        if not dry:
            shutil.copyfile(src, os.path.join(res_dir, new_item))
        if not any(i['name'] == new_item for i in items):
            items.append({'name': new_item, 'path': new_item, 'type': 'Image'})
        if old_item and old_item != new_item:
            items[:] = [i for i in items if i['name'] != old_item]
            to_remove.append(os.path.join(res_dir, old_item))
            old_display = re.sub(r'\d{6,}(?=\.\w+$)', '', old_item)
            pat_item = r'("ItemName":\s*)"%s"' % re.escape(old_item)
            n = 0
            for f in visual_files(report_dir):
                s, cr = read(f)
                if not re.search(pat_item, s):
                    continue
                s2 = re.sub(pat_item, r'\1"%s"' % new_item, s)
                s2 = s2.replace("\"'%s'\"" % old_display, "\"'%s'\"" % new_item)
                s2 = re.sub(r'("scaling":\s*\{\s*"expr":\s*\{\s*"Literal":\s*\{\s*"Value":\s*)"\'Normal\'"', "\\1\"'Fit'\"", s2)
                write(f, s2, cr, dry)
                n += 1
            log.append('logo       %-13s %s -> %s (%d visuals)' % (slot, old_item, new_item, n))
        else:
            log.append('logo       %-13s %s refreshed' % (slot, new_item))
        cur_logos[slot] = new_item
    new_applied['logos'] = cur_logos

    # 3. literal colors (value only; conditional-formatting structure is never touched)
    # Slots are found by their current value, so two slots may never share one: they could not be
    # told apart on the next run. All swaps happen in one pass, so a slot's new value can safely be
    # another slot's old one.
    cur_lits = dict(applied.get('literals') or {})
    want = dict((k, hexc(rgb(v))) for k, v in (brand.get('literals') or {}).items())
    for name in want:
        if not cur_lits.get(name):
            die('literals.%s has no current value in brand.applied.json' % name)
    final = dict(cur_lits, **want)
    dupes = [v for v in set(x.upper() for x in final.values()) if [x.upper() for x in final.values()].count(v) > 1]
    if dupes:
        die('literal slots would share a value (%s) - give each slot a distinct color' % ', '.join(dupes))
    swap = dict((cur_lits[k].upper(), v) for k, v in want.items() if cur_lits[k].upper() != v.upper())
    if swap:
        pat = re.compile("'(%s)'" % '|'.join(re.escape(k) for k in swap), re.IGNORECASE)
        counts = dict.fromkeys(swap, 0)
        for f in visual_files(report_dir):
            s, cr = read(f)
            hit = set()

            def sub(m):
                # Called by pat.sub below, within this iteration
                hit.add(m.group(1).upper())  # noqa: B023
                return "'%s'" % swap[m.group(1).upper()]
            s2 = pat.sub(sub, s)
            if s2 != s:
                write(f, s2, cr, dry)
                for h in hit:
                    counts[h] += 1
        for k, v in want.items():
            if cur_lits[k].upper() in swap:
                log.append('literal    %-13s %s -> %s (%d visuals)' % (k, cur_lits[k], v, counts[cur_lits[k].upper()]))
    new_applied['literals'] = final

    # 4. title
    old_titles = applied.get('titles') or []
    n = 0
    for t in old_titles:
        if t != brand['title']:
            new_title = brand['title'].replace('\\', r'\\')
            # A title lives in a shape or button literal ('...') or in a textbox run ("value": "...")
            n += replace_in_visuals(report_dir, [("'%s'" % re.escape(t), "'%s'" % new_title),
                                                 (r'("value":\s*)"%s"' % re.escape(t), r'\g<1>"%s"' % new_title)], dry)
    if old_titles and old_titles != [brand['title']]:
        log.append('title      %s -> %r (%d visuals)' % (old_titles, brand['title'], n))
    new_applied['titles'] = [brand['title']]

    # 5. parameters
    params = brand.get('parameters') or {}
    if params:
        ex = os.path.join(model_dir, 'definition', 'expressions.tmdl')
        s, cr = read(ex)
        s2 = s
        if 'Project_PK' in params:
            s2 = re.sub(r'^(expression Project_PK = )\d+', r'\g<1>%d' % int(params['Project_PK']), s2, flags=re.M)
        if 'Schema' in params:
            s2 = re.sub(r'^(expression Schema = )"[^"]*"', r'\1"%s"' % params['Schema'], s2, flags=re.M)
        if s2 != s:
            write(ex, s2, cr, dry)
        log.append('parameters Project_PK=%s Schema=%s' % (params.get('Project_PK'), params.get('Schema')))

    # 5b. brand color measures: `measure _Brand_<role> = "rgb(r,g,b)"` - the one place DAX that
    # draws its own colors (SVG progress bars) reads the brand from. rgb(), not #hex: a raw '#'
    # ends a data: URI.
    n = 0
    for f in glob.glob(os.path.join(model_dir, 'definition', 'tables', '*.tmdl')):
        s, cr = read(f)

        def brand_measure(m):
            role = m.group(2)
            if role not in c or role == 'series':
                die('measure _Brand_%s in %s has no colors.%s to take its value from' % (role, os.path.basename(f), role))  # noqa: B023 - called by re.sub below, within this iteration
            return '%s"rgb(%d,%d,%d)"' % ((m.group(1),) + rgb(c[role]))
        s2 = re.sub(r'^(	measure _Brand_([a-z_]+) = )"[^"]*"', brand_measure, s, flags=re.M)
        if s2 != s:
            n += len(re.findall(r'^	measure _Brand_', s2, flags=re.M))
            write(f, s2, cr, dry)
    if n:
        log.append('measures   %d _Brand_* color measures set' % n)

    # 6. contrast on the pairs the report family actually renders
    warn = []
    if 'colors' in brand:
        for label, fg, bg, need, r in contrast_pairs(c):
            if r < need:
                warn.append('contrast   %-36s %s on %s = %.2f (needs %.1f)' % (label, fg, bg, r, need))

    if not dry:
        write(rj_path, dump(rj) + ('\n' if rj_text.endswith('\n') else ''), rj_cr, dry)
        for f in to_remove:
            if os.path.exists(f):
                os.remove(f)
        json.dump(new_applied, open(applied_path, 'w', encoding='utf-8', newline='\n'), indent=2, ensure_ascii=False)

    print(('DRY RUN - nothing written\n' if dry else '') + '\n'.join(log))
    src = brand.get('source') or {}
    print('source     %s (%s)' % (src.get('kind', '?'), src.get('ref', '')))
    if src.get('kind') == 'improvised':
        print('           palette is IMPROVISED - revisit when the client supplies a brand guide')
    for w in warn:
        print('WARNING    ' + w)
    if '--preview' in argv and not dry:
        import preview_brand
        print('preview    ' + preview_brand.render(project))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
