#!/usr/bin/env python
"""Static HTML brand preview of a PBIR report - no Desktop, no server, no data.

    python preview_brand.py <project-root> [--out <file.html>]

Writes <project>/assets/preview.html (git-ignored, never published) and prints its path. Open it
in a browser or VS Code's Simple Browser / Live Preview; rerun (or run apply_brand.py --preview)
after every change. Reads files only, so it is safe with Power BI Desktop open.

What is drawn faithfully: page canvas and background, shapes / buttons / nav bar in their resolved
theme colors (ThemeDataColor ids and tint/shade percents), logos and images, header title and
button text, textboxes, visual-group offsets (Hard Rule 23), hidden visuals, layer order, and the
SVG progress bars from the _Brand_* measures. A toggle shows the EXTRA FILTERS group open.
What is NOT: data, charts, slicer values, conditional formatting, exact font metrics. Charts and
tables are outlined boxes carrying their type and series colors. This replaces the Desktop
round-trips while iterating on a brand - not the Desktop Validation Gate (Hard Rule 18).
"""
import base64
import glob
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import apply_brand as ab  # noqa: E402

PT = 4.0 / 3.0            # Power BI font sizes are points
PBI_BLUE = '#118DFF'
EXTRAS_GROUPS = ('EXTRA FILTERS', 'FILTROS EXTRAS')   # extra-filters overlay group, EN and PT reports


def jload(p):
    return json.loads(open(p, encoding='utf-8-sig').read())


def lit(o):
    """Literal value of a PBIR {"expr": {"Literal": {"Value": ...}}} node, unquoted."""
    try:
        v = o['expr']['Literal']['Value']
    except (KeyError, TypeError):
        return None
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    m = re.fullmatch(r'(-?[\d.]+)[DL]?', v)
    return float(m.group(1)) if m else v


class Theme:
    def __init__(self, t):
        self.t = t
        self.bg = t.get('background', '#FFFFFF')
        self.fg = t.get('foreground', '#252423')
        self.dc = t.get('dataColors') or ['#118DFF']

    def color_id(self, cid, pct=0):
        base = self.bg if cid == 0 else self.fg if cid == 1 else self.dc[(cid - 2) % len(self.dc)]
        return ab.shade(base, pct) if pct else base

    def color(self, node):
        """Resolve a PBIR color node ({"solid": {"color": ...}} or the inner {"expr": ...})."""
        if not isinstance(node, dict):
            return None
        node = node.get('solid', node)
        node = node.get('color', node)
        e = node.get('expr', {}) if isinstance(node, dict) else {}
        if 'ThemeDataColor' in e:
            return self.color_id(int(e['ThemeDataColor'].get('ColorId', 0)), float(e['ThemeDataColor'].get('Percent', 0)))
        if 'Literal' in e:
            v = str(lit(node) or '')
            return v if re.fullmatch(r'#[0-9A-Fa-f]{6}', v) else None
        return None

    def style(self, vtype, obj, prop):
        """A property from the theme's visualStyles (type-specific first, then '*')."""
        vs = self.t.get('visualStyles', {})
        for key in (vtype, '*'):
            for entry in (vs.get(key, {}).get('*', {}).get(obj) or []):
                if prop in entry:
                    return entry[prop]
        return None


def props(objs, name, default_selector=True):
    """Merge every properties dict of an object list (Desktop splits them across entries)."""
    out = {}
    for e in objs.get(name) or []:
        sel = e.get('selector', {})
        if default_selector and sel and sel.get('id') not in (None, 'default'):
            continue
        out.update(e.get('properties', {}))
    return out


def text_css(p, theme, default_color, default_size=10):
    color = theme.color(p.get('fontColor')) or default_color
    size = lit(p.get('fontSize', {})) or default_size
    fam = lit(p.get('fontFamily', {})) or 'Segoe UI'
    bold = lit(p.get('bold', {})) in (True, 'true')
    return "color:%s;font-size:%.1fpx;font-family:'%s','Segoe UI',sans-serif;font-weight:%s;" % (
        color, float(size) * PT, html.escape(str(fam).split(',')[0].strip("'\"")), 700 if bold else 400)


class Page:
    def __init__(self, report_dir, page_dir, theme, images, brand_measures):
        self.theme, self.images, self.bm = theme, images, brand_measures
        self.meta = jload(os.path.join(page_dir, 'page.json'))
        self.v = {}
        for f in glob.glob(os.path.join(page_dir, 'visuals', '*', 'visual.json')):
            j = jload(f)
            self.v[j['name']] = j

    def chain(self, n):
        out = []
        while n in self.v:
            out.append(n)
            n = self.v[n].get('parentGroupName')
        return out[::-1]

    def abs_pos(self, n):
        x = y = 0.0
        for a in self.chain(n)[:-1]:
            x += self.v[a]['position'].get('x', 0)
            y += self.v[a]['position'].get('y', 0)
        p = self.v[n]['position']
        return x + p.get('x', 0), y + p.get('y', 0), p.get('width', 0), p.get('height', 0)

    def state(self, n):
        """'shown' | 'extras' (hidden only because the extra-filters group is closed) | 'hidden'."""
        via_extras = False
        for a in self.chain(n):
            j = self.v[a]
            if j.get('isHidden'):
                if (j.get('visualGroup') or {}).get('displayName', '').upper() in EXTRAS_GROUPS:
                    via_extras = True
                else:
                    return 'hidden'
        return 'extras' if via_extras else 'shown'

    def render(self):
        w, h = self.meta.get('width', 1280), self.meta.get('height', 720)
        bgp = props(self.meta.get('objects', {}), 'background')
        bg = self.theme.color(bgp.get('color')) or self.theme.color(
            {'solid': {'color': self.theme.style('page', 'background', 'color') or {}}}) or '#FFFFFF'
        tv = self.theme.style('page', 'background', 'color')
        if not bgp.get('color') and isinstance(tv, dict):
            bg = tv.get('solid', {}).get('color', bg)
        order = sorted((n for n, j in self.v.items() if 'visual' in j),
                       key=lambda n: [self.v[a]['position'].get('z', 0) for a in self.chain(n)])
        parts = []
        for n in order:
            st = self.state(n)
            if st == 'hidden':
                continue
            x, y, vw, vh = self.abs_pos(n)
            inner = self.visual(self.v[n], vw, vh)
            parts.append('<div class="v%s" style="left:%.1fpx;top:%.1fpx;width:%.1fpx;height:%.1fpx" title="%s">%s</div>' % (
                ' extras' if st == 'extras' else '', x, y, vw, vh, html.escape(self.label(self.v[n])), inner))
        return '<div class="canvas" style="width:%dpx;height:%dpx;background:%s">%s</div>' % (w, h, bg, ''.join(parts))

    @staticmethod
    def label(j):
        t = props(j['visual'].get('visualContainerObjects', {}), 'title').get('text')
        return (lit(t) if t else None) or j['visual']['visualType']

    def container_bg(self, j, vtype):
        vco = j['visual'].get('visualContainerObjects', {})
        b = props(vco, 'background')
        show = lit(b.get('show', {}))
        if show is None:
            show = vtype not in ('shape', 'image', 'textbox', 'actionButton', 'basicShape')
        if show in (False, 'false'):
            return ''
        c = self.theme.color(b.get('color')) or self.theme.bg
        tr = lit(b.get('transparency', {})) or 0
        rad = props(vco, 'border').get('radius')
        rad = lit(rad) if rad else self.theme.style('*', 'border', 'radius') or 0
        return 'background:%s;opacity:1;border-radius:%spx;%s' % (ab_rgba(c, 1 - float(tr) / 100), rad, '')

    def visual(self, j, w, h):
        v = j['visual']
        vt = v['visualType']
        o = v.get('objects', {})
        if vt in ('shape', 'basicShape', 'actionButton'):
            return self.shape(vt, o, w, h, v.get('visualContainerObjects', {}))
        if vt == 'image':
            return self.image(o)
        if vt == 'textbox':
            return self.textbox(o)
        if vt in ('slicer', 'textSlicer'):
            return self.slicer(j, o)
        return self.placeholder(j, vt, w, h)

    def shape(self, vt, o, w, h, vco=None):
        vco = vco or {}
        pad = props(vco, 'padding')
        pt, pb, pl, pr = (float(lit(pad.get(k, {})) or 0) for k in ('top', 'bottom', 'left', 'right'))
        box = 'top:%.1fpx;bottom:%.1fpx;left:%.1fpx;right:%.1fpx;' % (pt, pb, pl, pr)
        sp = props(o, 'shape')
        tile = str(lit(sp.get('tileShape', {})) or 'rectangle')
        outl = props(o, 'outline')
        if tile == 'line':
            angle = float(lit(props(o, 'rotation').get('angle', {})) or 0)
            weight = max(1.0, float(lit(outl.get('weight', {})) or 1) * PT)
            color = self.theme.color(outl.get('lineColor')) or self.theme.fg
            if round(angle) % 180 == 90:
                line = 'left:50%%;top:0;bottom:0;border-left:%.1fpx solid %s' % (weight, color)
            else:
                line = 'top:50%%;left:0;right:0;border-top:%.1fpx solid %s' % (weight, color)
            return '<div class="fill" style="%s"><div style="position:absolute;%s"></div></div>' % (box, line)
        fillp = props(o, 'fill')
        fill = self.theme.color(fillp.get('fillColor'))
        if lit(fillp.get('show', {})) in (False, 'false'):
            fill = None
        tr = float(lit(fillp.get('transparency', {})) or 0)
        if tile == 'tabRoundTopCorners':
            r = float(lit(sp.get('tabRoundCornerTop', {})) or 10) * min(w, h) / 100
            rad = '%.1fpx %.1fpx 0 0' % (r, r)
        elif tile == 'rectangleRoundedByPixel':
            rad = '%.1fpx' % float(lit(sp.get('roundEdge', {})) or 10)
        elif 'Rounded' in tile:
            rad = '%.1fpx' % (min(w, h) * 0.2)
        else:
            rad = '0'
        border = ''
        if lit(outl.get('show', {})) in (True, 'true'):
            border = 'border:%spx solid %s;' % (lit(outl.get('weight', {})) or 1, self.theme.color(outl.get('lineColor')) or '#999')
        shadow = ''
        sh = props(o, 'shadow')
        if lit(sh.get('show', {})) in (True, 'true'):
            shadow = 'box-shadow:2px 2px 0 rgba(0,0,0,%.2f);' % (1 - float(lit(sh.get('transparency', {})) or 75) / 100)
        style = box + 'border-radius:%s;%s%s' % (rad, border, shadow)
        if fill:
            style += 'background:%s;' % ab_rgba(fill, 1 - tr / 100)
        tp = props(o, 'text')
        txt = ''
        if lit(tp.get('show', {})) in (True, 'true') and tp.get('text'):
            value = lit(tp['text'])
            if value is None:
                m = re.search(r'"Property":\s*"([^"]+)"', json.dumps(tp['text']))
                value = '[%s]' % (m.group(1) if m else 'measure')
            ha = lit(tp.get('horizontalAlignment', {})) or 'center'
            va = lit(tp.get('verticalAlignment', {})) or 'middle'
            padt = 'padding:%spx %spx %spx %spx;' % (lit(tp.get('topMargin', {})) or 0, lit(tp.get('rightMargin', {})) or 0,
                                                    lit(tp.get('bottomMargin', {})) or 0, lit(tp.get('leftMargin', {})) or 0)
            wrap = 'white-space:normal;text-align:center;line-height:1.05;' if vt == 'actionButton' else ''
            txt = '<div class="t" style="%sjustify-content:%s;align-items:%s;%s%s">%s</div>' % (
                text_css(tp, self.theme, '#FFFFFF' if vt != 'actionButton' else self.theme.fg, 10 if vt != 'actionButton' else 12),
                {'left': 'flex-start', 'right': 'flex-end'}.get(ha, 'center'),
                {'top': 'flex-start', 'bottom': 'flex-end'}.get(va, 'center'), padt, wrap, html.escape(str(value)))
        return '<div class="fill" style="%s">%s</div>' % (style, txt)

    def image(self, o):
        p = props(o, 'image').get('sourceFile', {}).get('image', {}) or {}
        item = (p.get('url', {}).get('expr', {}).get('ResourcePackageItem') or
                props(o, 'general').get('imageUrl', {}).get('expr', {}).get('ResourcePackageItem') or {}).get('ItemName')
        scaling = str(lit(p.get('scaling', {})) or 'Fit')
        src = self.images.get(item)
        if not src:
            return '<div class="ph">image: %s</div>' % html.escape(str(item))
        fit = {'Fit': 'contain', 'Fill': 'fill', 'Normal': 'none'}.get(scaling, 'contain')
        return '<img src="%s" style="object-fit:%s">' % (src, fit)

    def textbox(self, o):
        out = []
        for para in props(o, 'general').get('paragraphs') or []:
            runs = ''.join('<span style="%s">%s</span>' % (
                "font-size:%.1fpx;color:%s;font-weight:%s;font-family:'%s',sans-serif" % (
                    float(str(r.get('textStyle', {}).get('fontSize', '10pt')).rstrip('pt') or 10) * PT,
                    r.get('textStyle', {}).get('color', self.theme.fg), r.get('textStyle', {}).get('fontWeight', 'normal'),
                    r.get('textStyle', {}).get('fontFamily', 'Segoe UI')), html.escape(r.get('value') or ''))
                for r in para.get('textRuns', []))
            out.append('<div style="text-align:%s">%s</div>' % (para.get('horizontalTextAlignment', 'left'), runs))
        return '<div class="tb">%s</div>' % ''.join(out)

    def slicer(self, j, o):
        hp, ip = props(o, 'header'), props(o, 'items')
        proj = [p for r in j['visual'].get('query', {}).get('queryState', {}).values() for p in r.get('projections', [])]
        t = props(j['visual'].get('visualContainerObjects', {}), 'title').get('text')
        name = (proj[0].get('displayName') if proj else None) or (lit(t) if t else None) or \
            (proj[0].get('queryRef', '').split('.')[-1] if proj else j['visual']['visualType'])
        hc = self.theme.color(hp.get('fontColor')) or self.theme.fg
        hb = self.theme.color(hp.get('background'))
        ib = self.theme.color(ip.get('background')) or '#FFFFFF'
        size = float(lit(hp.get('textSize', {})) or 10) * PT
        mode = lit(props(o, 'data').get('mode', {})) or 'Basic'
        head = ''
        if lit(hp.get('show', {})) not in (False, 'false'):
            head = '<div style="color:%s;%sfont-size:%.1fpx;font-weight:600;padding:1px 2px">%s</div>' % (
                hc, 'background:%s;' % hb if hb else '', size, html.escape(str(name)))
        if j['visual']['visualType'] == 'textSlicer':
            return '<div class="tb" style="%s">%s<div class="dd" style="background:%s">&#128269;</div></div>' % (
                self.container_bg(j, 'textSlicer'), head, ib)
        if mode == 'Dropdown':
            return '<div class="tb">%s<div class="dd" style="background:%s">All<span>&#8964;</span></div></div>' % (head, ib)
        return '<div class="box" style="%s">%s<div class="cap"><small>slicer (%s)</small></div></div>' % (
            self.container_bg(j, 'slicer'), head, html.escape(str(mode)))

    def placeholder(self, j, vt, w, h):
        v = j['visual']
        style = self.container_bg(j, vt)
        q = json.dumps(v)
        name = self.label(j)
        body = ''
        if '_BarraProgressoGradiente' in q or 'Percentual' in name:
            body = progress_svg(self.bm, 0.62)
        if vt == 'card':
            o = v.get('objects', {})
            lc = self.theme.color(props(o, 'categoryLabels').get('color')) or self.theme.dc[1]
            vc = self.theme.color(props(o, 'labels').get('color')) or self.theme.dc[0]
            return '<div class="box" style="%s"><div class="card" style="color:%s">%s</div>' \
                   '<div class="cval" style="color:%s">123</div></div>' % (style, lc, html.escape(str(name)), vc)
        if vt in ('tableEx', 'pivotTable'):
            hb = self.theme.style(vt, 'columnHeaders', 'backColor')
            hb = self.theme.color(hb) if isinstance(hb, dict) and 'expr' in json.dumps(hb) else (
                hb.get('solid', {}).get('color') if isinstance(hb, dict) else None)
            hb = hb or self.theme.fg
            body = '<div style="height:22px;background:%s"></div>' % hb + body
        colors = []
        for dp in v.get('objects', {}).get('dataPoint', []):
            c = self.theme.color(dp.get('properties', {}).get('fill'))
            if c and c not in colors:
                colors.append(c)
        if not colors and vt not in ('slicer', 'textSlicer', 'card', 'cardVisual', 'kpi', 'tableEx', 'pivotTable'):
            colors = self.theme.dc[:3]
        sw = ''.join('<i style="background:%s"></i>' % c for c in colors[:6])
        return '<div class="box" style="%s">%s<div class="cap">%s<br><small>%s</small><span class="sw">%s</span></div></div>' % (
            style, body, html.escape(str(name)), html.escape(vt[:32]), sw)


def ab_rgba(hexc, alpha):
    r, g, b = ab.rgb(hexc)
    return 'rgba(%d,%d,%d,%.3f)' % (r, g, b, max(0.0, min(1.0, alpha)))


def progress_svg(bm, frac):
    s, e, t = (bm.get(k, d) for k, d in (('progress_start', 'rgb(236,100,57)'), ('progress_end', 'rgb(255,166,118)'),
                                          ('progress_track', 'rgb(230,230,230)')))
    return ('<svg class="bar" viewBox="0 0 100 20" preserveAspectRatio="none"><defs><linearGradient id="g">'
            '<stop offset="0%%" stop-color="%s"/><stop offset="100%%" stop-color="%s"/></linearGradient></defs>'
            '<rect x="0" y="3" width="100" height="15" fill="%s"/><rect x="0" y="3" width="%d" height="15" fill="url(#g)"/></svg>'
            % (s, e, t, round(frac * 100)))


def render(project, out=None):
    rep = ab.find_one(project, '*.Report')
    model = ab.find_one(project, '*.SemanticModel')
    D = os.path.join(rep, 'definition')
    rj = jload(os.path.join(D, 'report.json'))
    res = os.path.join(rep, 'StaticResources', 'RegisteredResources')
    theme_name = rj.get('themeCollection', {}).get('customTheme', {}).get('name')
    theme = Theme(jload(os.path.join(res, theme_name)) if theme_name else {})
    images = {}
    for f in glob.glob(os.path.join(res, '*')):
        ext = os.path.splitext(f)[1].lower().lstrip('.')
        if ext in ('png', 'jpg', 'jpeg', 'gif', 'svg'):
            mime = 'image/svg+xml' if ext == 'svg' else 'image/' + ('jpeg' if ext == 'jpg' else ext)
            images[os.path.basename(f)] = 'data:%s;base64,%s' % (mime, base64.b64encode(open(f, 'rb').read()).decode())
    bm = {}
    for f in glob.glob(os.path.join(model, 'definition', 'tables', '*.tmdl')):
        for m in re.finditer(r'^\tmeasure _Brand_([a-z_]+) = "([^"]*)"', open(f, encoding='utf-8').read(), re.M):
            bm[m.group(1)] = m.group(2)

    order = jload(os.path.join(D, 'pages', 'pages.json')).get('pageOrder', [])
    pages = []
    for pid in order:
        pd = os.path.join(D, 'pages', pid)
        if os.path.isdir(pd):
            p = Page(rep, pd, theme, images, bm)
            hidden = p.meta.get('visibility') == 'HiddenInViewMode'
            pages.append((p.meta.get('displayName', pid) + (' (oculta)' if hidden else ''), p.render()))

    # palette + contrast, from the brand when there is one
    brand_p = os.path.join(project, 'assets', 'brand.json')
    roles = dict((pos, role) for pos, role in ab.POSITIONS.items())
    sw = ['<div class="sw2"><i style="background:%s"></i><b>id 0</b> background<br>%s</div>' % (theme.bg, theme.bg),
          '<div class="sw2"><i style="background:%s"></i><b>id 1</b> foreground<br>%s</div>' % (theme.fg, theme.fg)]
    for k, c in enumerate(theme.dc[:14]):
        sw.append('<div class="sw2"><i style="background:%s"></i><b>id %d</b> %s<br>%s</div>' % (
            c, k + 2, roles.get(k, 'series' if k in ab.SERIES_SLOTS or k >= 10 else ''), c))
    rows = []
    src = ''
    if os.path.exists(brand_p):
        brand = jload(brand_p)
        s = brand.get('source') or {}
        src = '%s - %s' % (s.get('kind', '?'), s.get('ref', ''))
        c = ab.resolve_colors(brand)
        for label, fg, bg, need, r in ab.contrast_pairs(c):
            rows.append('<tr class="%s"><td>%s</td><td><span class="chip" style="color:%s;background:%s">Aa</span></td><td>%.2f</td><td>%.1f</td></tr>' % (
                'ok' if r >= need else 'bad', html.escape(label), fg, bg, r, need))

    tabs = ''.join('<button onclick="show(%d)" id="b%d">%s</button>' % (i, i, html.escape(n)) for i, (n, _) in enumerate(pages))
    body = ''.join('<section id="p%d" class="page">%s</section>' % (i, c) for i, (_, c) in enumerate(pages))
    doc = HTML.replace('{{TITLE}}', html.escape(os.path.basename(os.path.abspath(project)))) \
              .replace('{{TABS}}', tabs).replace('{{PAGES}}', body).replace('{{SWATCHES}}', ''.join(sw)) \
              .replace('{{CONTRAST}}', ''.join(rows) or '<tr><td colspan=4>no assets/brand.json</td></tr>') \
              .replace('{{SOURCE}}', html.escape(src)).replace('{{THEME}}', html.escape(str(theme_name)))
    out = out or os.path.join(project, 'assets', 'preview.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8', newline='\n').write(doc)
    return out


HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Preview - {{TITLE}}</title>
<style>
:root{--ui:#1f1f1f;--ui2:#2b2b2b;--tx:#e8e8e8}
body{margin:0;background:var(--ui);color:var(--tx);font:13px "Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--ui2);padding:8px 12px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
header button{background:#3a3a3a;color:var(--tx);border:0;border-radius:4px;padding:5px 10px;cursor:pointer}
header button.on{background:#0e639c}
header label{margin-left:auto}
.wrap{padding:12px}
.page{display:none}.page.on{display:block}
.stage{transform-origin:0 0}
.canvas{position:relative;overflow:hidden;box-shadow:0 2px 12px #0008}
.v{position:absolute;box-sizing:border-box}
.v.extras{display:none}
body.extras-open .v.extras{display:block}
.fill,.box,.tb{position:absolute;inset:0;box-sizing:border-box;overflow:hidden}
.t{position:absolute;inset:0;display:flex;white-space:nowrap}
img{width:100%;height:100%;display:block}
.box{outline:1px dashed #9aa4b155;font-size:11px;color:#6b7280}
.cap{position:absolute;left:4px;bottom:3px;line-height:1.2}
.cap small{opacity:.7}.sw i{display:inline-block;width:10px;height:10px;margin:2px 2px 0 0;border-radius:2px}
.bar{position:absolute;left:10%;right:10%;top:45%;width:80%;height:14px}
.ph{position:absolute;inset:0;outline:1px dashed #d33;color:#d33;font-size:10px}
.tb{padding:2px 4px;color:#333}
.card{position:absolute;left:6px;top:4px;font-size:12px;font-weight:600}
.cval{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:600}
.dd{margin:2px;height:20px;border:1px solid #bbb;border-radius:2px;color:#333;font-size:11px;padding:2px 5px;box-sizing:border-box;display:flex;justify-content:space-between}
aside{padding:12px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
.sw2{display:inline-block;width:150px;margin:0 8px 8px 0;font-size:11px;vertical-align:top}
.sw2 i{display:block;height:34px;border-radius:4px;margin-bottom:3px;border:1px solid #fff2}
table{border-collapse:collapse;font-size:12px}td{padding:3px 8px;border-bottom:1px solid #fff1}
tr.bad td{color:#ff8a80}.chip{padding:1px 8px;border-radius:3px;font-weight:600}
.note{opacity:.6;font-size:11px}
</style></head><body>
<header><b>{{TITLE}}</b>&nbsp;{{TABS}}<label><input type="checkbox" onchange="document.body.classList.toggle('extras-open',this.checked)"> Extra filters open</label></header>
<div class="wrap">{{PAGES}}</div>
<aside><div><h3>Theme: {{THEME}}</h3><div class="note">brand source: {{SOURCE}}</div><br>{{SWATCHES}}</div>
<div><h3>Contrast (WCAG)</h3><table>{{CONTRAST}}</table>
<p class="note">Brand preview: no data, charts drawn as boxes. Does not replace validation in Desktop.</p></div></aside>
<script>
function fit(){document.querySelectorAll('.page.on .canvas').forEach(c=>{const s=Math.min(1,(innerWidth-24)/c.offsetWidth);
c.parentElement.style.height=(c.offsetHeight*s)+'px';c.style.transform='scale('+s+')';c.style.transformOrigin='0 0'})}
function show(i){document.querySelectorAll('.page').forEach((p,k)=>p.classList.toggle('on',k==i));
document.querySelectorAll('header button').forEach((b,k)=>b.classList.toggle('on',k==i));try{localStorage.setItem('pg',i)}catch(e){}fit()}
addEventListener('resize',fit);let i0=0;try{i0=+localStorage.getItem('pg')||0}catch(e){}
const hm=location.hash.match(/page=([0-9]+)/);if(hm)i0=+hm[1];
if(location.hash.includes('extras')){document.body.classList.add('extras-open');document.querySelector('header input').checked=true}
show(i0)
</script></body></html>'''


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    if out:
        args.remove(out)
    if len(args) != 1:
        sys.exit('usage: preview_brand.py <project-root> [--out file.html]')
    print(render(os.path.abspath(args[0]), out))
