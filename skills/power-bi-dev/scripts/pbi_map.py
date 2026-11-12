#!/usr/bin/env python3
"""Generate docs/model-map.md and docs/report-map.md for a Power BI (.pbip) project.

    python ~/.claude/skills/power-bi-dev/scripts/pbi_map.py [project_dir] [--out DIR] [--no-gitignore]

Why: a project's definition/ folders run to megabytes of generated TMDL and PBIR JSON. Finding one
measure or one visual by reading them costs tens of thousands of tokens per look, on every look.
These two files are the index that replaces the looking: a few KB each, deterministic, rebuilt in
under a second, never hand-edited.

    model-map.md    tables (file, size, storage mode, source, columns), measures grouped by
                    displayFolder WITH LINE NUMBERS, relationships, shared M expressions, and the
                    files that must never be read whole (cultures/*.tmdl above all).
    report-map.md   pages in order -> visual groups -> visuals: type, folder id, ABSOLUTE canvas
                    position (group origins already added - CLAUDE.md Hard Rule 23), bound fields,
                    text. Visuals that land outside the page are flagged.

Pure standard library. Reads only; the two maps (and, once, two .gitignore lines) are all it writes.
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import sys

BIG_FILE_BYTES = 60 * 1024        # anything larger is listed under "Do not read whole"
MAX_REFS_PER_ROLE = 6
MAX_LABEL_CHARS = 48
GITIGNORE_LINES = ("docs/model-map.md", "docs/report-map.md")
REGEN = "python ~/.claude/skills/power-bi-dev/scripts/pbi_map.py"

NAME = r"('(?:[^']|'')*'|\"[^\"]*\"|[^\s=]+)"
OBJ_RE = re.compile(r"^(\t*)(table|measure|column|partition|hierarchy|calculationGroup|calculationItem|expression|relationship)\s+" + NAME + r"\s*(=?)")
PROP_RE = re.compile(r"^(\t+)([A-Za-z]+)(?::\s*(.*))?$")
CONNECTOR_RE = re.compile(
    r"\b(Sql\.Databases?|Excel\.Workbook|SharePoint\.(?:Files|Contents|Tables)|Csv\.Document|Web\.Contents|"
    r"OData\.Feed|Folder\.(?:Files|Contents)|Json\.Document|AnalysisServices\.Databases?|"
    r"PowerPlatform\.Dataflows|PowerBI\.Dataflows|Salesforce\.\w+|Odbc\.\w+|Oracle\.Database|"
    r"PostgreSQL\.Database|Lakehouse\.Contents|Fabric\.Warehouse|Table\.FromRows|#table)\b")
SOURCE_REF_RE = re.compile(r"^\s*Source\s*=\s*(#?\"[^\"]+\"|[A-Za-z_][\w.]*)\s*,?\s*$")


def read_text(path):
    with io.open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def unquote(name):
    if len(name) >= 2 and name[0] == name[-1] and name[0] in "'\"":
        return name[1:-1].replace("''", "'")
    return name


def kb(n):
    return "%d KB" % round(n / 1024.0) if n >= 1024 else "%d B" % n


def rel(path, base):
    return os.path.relpath(path, base).replace(os.sep, "/")


def big_files(definition_dir):
    """Files nobody should Read whole: over the size limit, plus every culture file."""
    out = []
    for root, _dirs, files in os.walk(definition_dir):
        for name in files:
            p = os.path.join(root, name)
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            r = rel(p, definition_dir)
            if size >= BIG_FILE_BYTES or r.startswith("cultures/"):
                out.append((size, r))
    return sorted(out, reverse=True)


# ------------------------------------------------------------------------------------------ TMDL

def parse_table(path):
    """Line-based TMDL read of one tables/*.tmdl file. Indentation is tabs (CLAUDE.md Hard Rule 1):
    the table sits at indent 0, its objects at 1, their properties at 2, expression bodies deeper."""
    t = {"name": None, "path": path, "size": os.path.getsize(path), "hidden": False,
         "columns": [], "measures": [], "partitions": [], "hierarchies": [], "calcitems": []}
    cur = None
    for no, line in enumerate(read_text(path).splitlines(), 1):
        m = OBJ_RE.match(line)
        if m:
            indent, kind, name, eq = len(m.group(1)), m.group(2), unquote(m.group(3)), m.group(4)
            if kind == "table" and indent == 0:
                t["name"] = name
                cur = None
                continue
            if indent == 1 and kind in ("measure", "column", "partition", "hierarchy", "calculationGroup"):
                cur = {"kind": kind, "name": name, "line": no, "calc": bool(eq) and kind == "column"}
                if kind == "measure":
                    t["measures"].append(cur)
                elif kind == "column":
                    t["columns"].append(cur)
                elif kind == "partition":
                    cur["ptype"] = line.split("=", 1)[1].strip() if "=" in line else ""
                    t["partitions"].append(cur)
                elif kind == "hierarchy":
                    t["hierarchies"].append(cur)
                continue
            if indent == 2 and kind == "calculationItem":
                t["calcitems"].append({"name": name, "line": no})
                continue
        p = PROP_RE.match(line)
        if p:
            indent, key, val = len(p.group(1)), p.group(2), (p.group(3) or "").strip()
            if indent == 1 and key == "isHidden":
                t["hidden"] = True
            elif indent == 2 and cur is not None:
                if key in ("displayFolder", "dataType", "mode", "sourceColumn"):
                    cur[key] = unquote(val)
                elif key == "isHidden":
                    cur["hidden"] = True
            continue
        if cur is not None and cur["kind"] == "partition" and "source_hint" not in cur:
            c = CONNECTOR_RE.search(line)
            if c:
                cur["source_hint"] = c.group(1)
            else:
                s = SOURCE_REF_RE.match(line)
                if s:
                    cur["source_ref"] = s.group(1).strip('#"')
    if t["name"] is None:
        t["name"] = os.path.splitext(os.path.basename(path))[0]
    return t


def parse_relationships(path):
    rels, cur = [], None
    for line in read_text(path).splitlines():
        if line.startswith("relationship "):
            cur = {}
            rels.append(cur)
        elif cur is not None and line.startswith("\t") and ":" in line:
            k, v = line.strip().split(":", 1)
            cur[k.strip()] = v.strip()
    return rels


def parse_expressions(path):
    out, cur = [], None
    for no, line in enumerate(read_text(path).splitlines(), 1):
        m = OBJ_RE.match(line)
        if m and m.group(2) == "expression" and not m.group(1):
            cur = {"name": unquote(m.group(3)), "line": no, "group": "",
                   "param": "IsParameterQuery=true" in line.replace(" ", "")}
            out.append(cur)
        elif cur is not None and line.startswith("\tqueryGroup:"):
            cur["group"] = unquote(line.split(":", 1)[1].strip())
    return out


def by_folder(measures):
    folders = {}
    for m in measures:
        folders.setdefault(m.get("displayFolder", ""), []).append(m)
    return sorted(folders.items(), key=lambda kv: kv[0].lower())


def model_map(definition_dir, project_dir, stamp):
    model_name = os.path.basename(os.path.dirname(definition_dir))
    tables = [parse_table(p) for p in sorted(glob.glob(os.path.join(definition_dir, "tables", "*.tmdl")))]
    rel_path = os.path.join(definition_dir, "relationships.tmdl")
    rels = parse_relationships(rel_path) if os.path.exists(rel_path) else []
    expr_path = os.path.join(definition_dir, "expressions.tmdl")
    exprs = parse_expressions(expr_path) if os.path.exists(expr_path) else []
    n_meas = sum(len(t["measures"]) for t in tables)
    base = rel(definition_dir, project_dir)

    L = ["# Model map - %s" % model_name,
         "<!-- generated by pbi_map.py - do not edit. Regenerate: %s -->" % REGEN, "",
         "Generated %s - %d tables, %d measures, %d relationships." % (stamp, len(tables), n_meas, len(rels)), "",
         "Paths are relative to `%s/`. `Name:123` is a line number in that file: Read it with "
         "`offset`/`limit` instead of reading the file. `~` = hidden, `=` = DAX calculated column." % base, ""]

    big = big_files(definition_dir)
    if big:
        L.append("## Do not read whole")
        L.append("Grep these, or Read a line range - never the whole file.")
        for size, r in big:
            L.append("- `%s` - %s" % (r, kb(size)))
        L.append("")

    design = [t for t in tables if t["name"].startswith("z_")]
    L.append("## Tables")
    for t in tables:
        if t in design:
            continue
        bits = ["`%s`" % rel(t["path"], definition_dir), kb(t["size"])]
        for p in t["partitions"][:1]:
            mode = p.get("mode") or p.get("ptype") or ""
            src = p.get("source_hint") or (("from " + p["source_ref"]) if p.get("source_ref") else "")
            bits.append(" ".join(x for x in (mode, src) if x) or p.get("ptype", ""))
        if len(t["partitions"]) > 1:
            bits.append("%d partitions" % len(t["partitions"]))
        if t["hidden"]:
            bits.append("hidden")
        L.append("### %s - %s" % (t["name"], " - ".join(b for b in bits if b)))
        if t["columns"]:
            cols = ["%s%s%s%s" % ("~" if c.get("hidden") else "", "=" if c.get("calc") else "", c["name"],
                                  ":" + c["dataType"] if c.get("dataType") else "") for c in t["columns"]]
            L.append("columns (%d): %s" % (len(cols), " | ".join(cols)))
        if t["hierarchies"]:
            L.append("hierarchies: " + " | ".join(h["name"] for h in t["hierarchies"]))
        if t["calcitems"]:
            L.append("calculation items: " + " | ".join("%s:%d" % (c["name"], c["line"]) for c in t["calcitems"]))
        if t["measures"]:
            L.append("measures: %d - see Measures below" % len(t["measures"]))
        L.append("")
    if design:
        L.append("### Design-system tables (`z_*`) - ignore in Stages 2-4, remove after Stage 5 is approved")
        L.append(" | ".join("%s (`%s`)" % (t["name"], rel(t["path"], definition_dir)) for t in design))
        L.append("")

    if n_meas:
        L.append("## Measures")
        for t in tables:
            if not t["measures"]:
                continue
            L.append("### %s - `%s` (%d)" % (t["name"], rel(t["path"], definition_dir), len(t["measures"])))
            for folder, ms in by_folder(t["measures"]):
                L.append("- `%s`: %s" % (folder or "(no displayFolder)",
                                         " | ".join("%s:%d" % (m["name"], m["line"]) for m in ms)))
            L.append("")

    if rels:
        L.append("## Relationships (`relationships.tmdl`)")
        L.append("many -> one unless noted; single-direction filter unless `both`.")
        for r in rels:
            notes = []
            if r.get("crossFilteringBehavior") == "bothDirections":
                notes.append("both")
            if r.get("isActive") == "false":
                notes.append("INACTIVE")
            card = (r.get("fromCardinality"), r.get("toCardinality"))
            if card != (None, None):
                notes.append("%s:%s" % (card[0] or "many", card[1] or "one"))
            L.append("- %s -> %s%s" % (r.get("fromColumn", "?"), r.get("toColumn", "?"),
                                      " (" + ", ".join(notes) + ")" if notes else ""))
        L.append("")

    if exprs:
        L.append("## Shared M expressions (`expressions.tmdl`)")
        groups = {}
        for e in exprs:
            groups.setdefault(e["group"], []).append(e)
        for g, es in sorted(groups.items()):
            L.append("- %s: %s" % (g or "(no query group)",
                                   " | ".join("%s%s:%d" % (e["name"], " (param)" if e["param"] else "", e["line"]) for e in es)))
        L.append("")
    return "\n".join(L), {"tables": len(tables), "measures": n_meas, "relationships": len(rels)}


# ------------------------------------------------------------------------------------------ PBIR

def load_json(path):
    try:
        return json.loads(read_text(path))
    except (ValueError, OSError):
        return None


def literal(node):
    """'text' out of {"expr": {"Literal": {"Value": "'text'"}}}, else None."""
    try:
        v = node["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    return v[1:-1].replace("''", "'") if isinstance(v, str) and len(v) >= 2 and v[0] == "'" else None


def clip(s):
    s = " ".join(str(s).split())
    return s if len(s) <= MAX_LABEL_CHARS else s[:MAX_LABEL_CHARS - 1] + "..."


def field_ref(field):
    """Entity.Property for a Column/Measure field, wrapped by the aggregation when there is one."""
    if not isinstance(field, dict):
        return "?"
    for kind in ("Column", "Measure", "HierarchyLevel"):
        if kind in field:
            f = field[kind]
            src = f.get("Expression", {})
            ent = src.get("SourceRef", {}).get("Entity")
            if ent is None and "Hierarchy" in src:
                h = src["Hierarchy"]
                ent = "%s.%s" % (h.get("Expression", {}).get("SourceRef", {}).get("Entity", "?"), h.get("Hierarchy", "?"))
            return "%s.%s" % (ent or "?", f.get("Property") or f.get("Level") or "?")
    if "Aggregation" in field:
        return "agg(%s)" % field_ref(field["Aggregation"].get("Expression", {}))
    return "?"


def visual_label(vis, container):
    vtype = vis.get("visualType")
    objects = vis.get("objects") or {}
    if vtype == "textbox":
        runs = []
        for g in objects.get("general", []):
            for para in (g.get("properties") or {}).get("paragraphs", []) or []:
                for run in para.get("textRuns", []) or []:
                    val = run.get("value") if isinstance(run, dict) else None
                    if isinstance(val, str) and val.strip():
                        runs.append(val)
                    elif val:                      # a run bound to a measure or field, not literal text
                        runs.append("{dynamic}")
        if runs:
            return clip(" ".join(runs))
    for t in objects.get("text", []):
        txt = literal((t.get("properties") or {}).get("text"))
        if txt:
            return clip(txt)
    for t in ((container.get("visual") or {}).get("visualContainerObjects") or {}).get("title", []):
        txt = literal((t.get("properties") or {}).get("text"))
        if txt:
            return clip(txt)
    return None


def visual_fields(vis):
    out = []
    state = ((vis.get("query") or {}).get("queryState")) or {}
    for role, q in state.items():
        refs = [p.get("queryRef") or field_ref(p.get("field")) for p in (q.get("projections") or [])]
        if not refs:
            continue
        shown = refs[:MAX_REFS_PER_ROLE]
        more = " +%d" % (len(refs) - len(shown)) if len(refs) > len(shown) else ""
        out.append("%s: %s%s" % (role, ", ".join(shown), more))
    return out


def fmt(n):
    return "%d" % round(n) if isinstance(n, (int, float)) else "?"


def by_position(node):
    """Reading order: top to bottom, then left to right, on absolute positions."""
    return (round(node["y"]), round(node["x"]))


def report_map(definition_dir, project_dir, stamp):
    report_name = os.path.basename(os.path.dirname(definition_dir))
    pages_dir = os.path.join(definition_dir, "pages")
    meta = load_json(os.path.join(pages_dir, "pages.json")) or {}
    order = list(meta.get("pageOrder") or [])
    on_disk = sorted(d for d in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, d))) if os.path.isdir(pages_dir) else []
    order += [d for d in on_disk if d not in order]
    base = rel(pages_dir, project_dir)

    body, n_vis, n_grp, n_off = [], 0, 0, 0
    for idx, pid in enumerate(order, 1):
        pdir = os.path.join(pages_dir, pid)
        page = load_json(os.path.join(pdir, "page.json"))
        if page is None:
            continue
        pw, ph = page.get("width"), page.get("height")
        tags = ["`%s/`" % pid, "%sx%s" % (fmt(pw), fmt(ph))]
        ptype = page.get("type") or (page.get("pageBinding") or {}).get("type")
        if ptype:
            tags.append(str(ptype))
        if page.get("visibility") and page.get("visibility") != "AlwaysVisible":
            tags.append("hidden")
        if pid == meta.get("activePageName"):
            tags.append("active")
        body.append("## %d. %s - %s" % (idx, page.get("displayName", pid), " - ".join(tags)))
        pf = [field_ref(f.get("field")) for f in (page.get("filterConfig") or {}).get("filters", [])]
        if pf:
            body.append("page filters: " + ", ".join(pf))

        nodes = {}
        for vjson in glob.glob(os.path.join(pdir, "visuals", "*", "visual.json")):
            v = load_json(vjson)
            if v is None:
                continue
            folder = os.path.basename(os.path.dirname(vjson))
            nodes[v.get("name") or folder] = {"v": v, "folder": folder, "children": []}
        roots = []
        for node in nodes.values():
            parent = nodes.get(node["v"].get("parentGroupName"))
            (parent["children"] if parent else roots).append(node)

        def absolute(node, ox, oy):
            pos = node["v"].get("position") or {}
            node["x"], node["y"] = ox + (pos.get("x") or 0), oy + (pos.get("y") or 0)
            node["w"], node["h"] = pos.get("width") or 0, pos.get("height") or 0
            for c in node["children"]:
                absolute(c, node["x"], node["y"])

        def emit(node, depth, pw=pw, ph=ph):   # bound per page: this def sits inside the page loop
            nonlocal n_vis, n_grp, n_off
            v = node["v"]
            where = "@%s,%s %sx%s" % (fmt(node["x"]), fmt(node["y"]), fmt(node["w"]), fmt(node["h"]))
            hidden = " (hidden)" if v.get("isHidden") else ""
            off = ""
            if (not v.get("isHidden") and isinstance(pw, (int, float)) and isinstance(ph, (int, float))
                    and (node["x"] + node["w"] < 0 or node["y"] + node["h"] < 0 or node["x"] >= pw or node["y"] >= ph)):
                off = " **OFF-PAGE**"
                n_off += 1
            pad = "  " * depth
            if "visualGroup" in v:
                n_grp += 1
                g = v["visualGroup"]
                body.append("%s- **%s** group `%s` %s%s%s" % (pad, g.get("displayName", "?"), node["folder"], where, hidden, off))
                for c in sorted(node["children"], key=by_position):
                    emit(c, depth + 1)
                return
            n_vis += 1
            vis = v.get("visual") or {}
            parts = ["%s- %s `%s` %s%s%s" % (pad, vis.get("visualType", "?"), node["folder"], where, hidden, off)]
            label = visual_label(vis, v)
            if label:
                parts.append('"%s"' % label)
            fields = visual_fields(vis)
            if fields:
                parts.append("<- " + " ; ".join(fields))
            nf = len((v.get("filterConfig") or {}).get("filters", []))
            if nf:
                parts.append("[%d filter%s]" % (nf, "" if nf == 1 else "s"))
            body.append(" ".join(parts))

        for r in roots:
            absolute(r, 0, 0)
        groups = sorted((r for r in roots if "visualGroup" in r["v"]), key=by_position)
        loose = sorted((r for r in roots if "visualGroup" not in r["v"]), key=by_position)
        for g in groups:
            emit(g, 0)
        if loose:
            body.append("- (ungrouped - Hard Rule 13 wants these in a named group)")
            for n in loose:
                emit(n, 1)
        body.append("")

    marks = sorted(glob.glob(os.path.join(definition_dir, "bookmarks", "*.bookmark.json")))
    if marks:
        names = [(load_json(p) or {}).get("displayName") or os.path.basename(p) for p in marks]
        body.append("## Bookmarks (%d, `bookmarks/`)" % len(names))
        body.append(" | ".join(names))
        body.append("")

    report = load_json(os.path.join(definition_dir, "report.json")) or {}
    theme = ((report.get("themeCollection") or {}).get("customTheme") or {}).get("name")

    L = ["# Report map - %s" % report_name,
         "<!-- generated by pbi_map.py - do not edit. Regenerate: %s -->" % REGEN, "",
         "Generated %s - %d pages, %d visuals in %d groups%s." % (
             stamp, len(order), n_vis, n_grp, ", custom theme `%s`" % theme if theme else ""), "",
         "Each visual lives at `%s/<page id>/visuals/<visual id>/visual.json`. Positions are **absolute** "
         "canvas `@x,y WxH` with every parent group's origin already added; the JSON of a visual inside "
         "a group stores its position **relative** to that group (Hard Rule 23), so subtract the "
         "group's `@x,y` before writing one." % base, ""]
    if n_off:
        L += ["**%d visible visual(s) land outside their page** - search for OFF-PAGE below; that is the "
              "Hard Rule 23 symptom (absolute coordinates written into a grouped child)." % n_off, ""]
    big = big_files(definition_dir)
    if big:
        L.append("## Do not read whole")
        for size, r in big:
            L.append("- `%s` - %s" % (r, kb(size)))
        L.append("")
    return "\n".join(L + body), {"pages": len(order), "visuals": n_vis, "groups": n_grp, "off_page": n_off}


# ------------------------------------------------------------------------------------------ main

def ensure_gitignore(project_dir):
    path = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(path):
        return None
    text = read_text(path)
    have = set(line.strip() for line in text.splitlines())
    missing = [g for g in GITIGNORE_LINES if g not in have]
    if not missing:
        return None
    with io.open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(("" if text.endswith("\n") or not text else "\n") +
                "\n# Generated project maps (pbi_map.py) - rebuilt on demand, never committed\n" +
                "\n".join(missing) + "\n")
    return missing


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n")
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project_dir", nargs="?", default=".", help="project root (holds the .pbip); default: current directory")
    ap.add_argument("--out", help="directory to write the two maps into (default: <project_dir>/docs)")
    ap.add_argument("--no-gitignore", action="store_true", help="do not add the two maps to the project's .gitignore")
    a = ap.parse_args()

    project = os.path.abspath(a.project_dir)
    models = sorted(glob.glob(os.path.join(project, "*.SemanticModel", "definition")))
    reports = sorted(glob.glob(os.path.join(project, "*.Report", "definition")))
    if not models and not reports:
        sys.stderr.write("pbi_map: no <Name>.SemanticModel/definition or <Name>.Report/definition under %s - "
                         "run it from the project root (the folder holding the .pbip).\n" % project)
        return 2

    out_dir = os.path.abspath(a.out) if a.out else os.path.join(project, "docs")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    source_bytes = sum(os.path.getsize(os.path.join(r, f)) for d in models + reports for r, _d, fs in os.walk(d) for f in fs)

    lines = []
    if models:
        built = [model_map(d, project, stamp) for d in models]
        parts, stats = [b[0] for b in built], [b[1] for b in built]
        size = write(os.path.join(out_dir, "model-map.md"), "\n\n".join(parts))
        lines.append("model-map.md   %s - %d tables, %d measures, %d relationships" % (
            kb(size), sum(s["tables"] for s in stats), sum(s["measures"] for s in stats), sum(s["relationships"] for s in stats)))
    if reports:
        built = [report_map(d, project, stamp) for d in reports]
        parts, stats = [b[0] for b in built], [b[1] for b in built]
        size = write(os.path.join(out_dir, "report-map.md"), "\n\n".join(parts))
        off = sum(s["off_page"] for s in stats)
        lines.append("report-map.md  %s - %d pages, %d visuals, %d groups%s" % (
            kb(size), sum(s["pages"] for s in stats), sum(s["visuals"] for s in stats), sum(s["groups"] for s in stats),
            " - %d OFF-PAGE (Hard Rule 23), see the map" % off if off else ""))

    print("pbi_map: wrote to %s (indexing %s of definition files)" % (out_dir, kb(source_bytes)))
    for line in lines:
        print("  " + line)
    if not a.out and not a.no_gitignore:
        added = ensure_gitignore(project)
        if added:
            print("  .gitignore: added %s" % ", ".join(added))
    return 0


if __name__ == "__main__":
    sys.exit(main())
