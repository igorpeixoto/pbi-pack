"""Checks the project-map generator: the demo template maps cleanly, and a visual that lands off its page is flagged."""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, 'skills', 'power-bi-dev', 'scripts', 'pbi_map.py')
DEMO = os.path.join(REPO, 'pbi-starter', 'templates', 'demo')
MEASURES = os.path.join(DEMO, 'Template-DEMO.SemanticModel', 'definition', 'tables', '_Measures.tmdl')
PAGES = os.path.join(DEMO, 'Template-DEMO.Report', 'definition', 'pages')


def run_map(project, out):
    """Runs the generator the way a session does, writing nowhere but out."""
    done = subprocess.run([sys.executable, SCRIPT, str(project), '--out', str(out), '--no-gitignore'],
                          capture_output=True, text=True, check=True)
    maps = {}
    for name in ('model-map.md', 'report-map.md'):
        path = os.path.join(str(out), name)
        maps[name] = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    return done.stdout, maps


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def test_demo_template_maps(tmp_path):
    _, maps = run_map(DEMO, tmp_path)
    model, report = maps['model-map.md'], maps['report-map.md']
    assert model and report

    # Every measure is listed with the line it starts on, which is what lets a session read a range
    measures = [(no, m.group(1).strip("'")) for no, line in enumerate(open(MEASURES, encoding='utf-8'), 1)
                for m in [re.match(r"\tmeasure ('[^']*'|\S+) =", line)] if m]
    assert measures
    for no, name in measures:
        assert '%s:%d' % (name, no) in model, name
    assert '`tables/_Measures.tmdl`' in model

    pages = [json.load(open(os.path.join(PAGES, d, 'page.json'), encoding='utf-8'))['displayName']
             for d in os.listdir(PAGES) if os.path.isdir(os.path.join(PAGES, d))]
    assert pages
    for name in pages:
        assert re.search(r'^## \d+\. %s - ' % re.escape(name), report, re.M), name

    assert 'OFF-PAGE' not in report
    # --out and --no-gitignore keep the template itself untouched
    assert not os.path.exists(os.path.join(DEMO, 'docs'))


def test_grouped_child_with_absolute_coordinates_is_flagged(tmp_path):
    """Hard Rule 23: a child's position is relative to its group, so a group at (54, 1029) holding a
    child written as (54, 1029) renders that child at (108, 2058), below a 1080-tall page."""
    page = tmp_path / 'project' / 'Tiny.Report' / 'definition' / 'pages' / 'page1'
    write_json(str(page / 'page.json'), {'name': 'page1', 'displayName': 'Tiny', 'width': 1920, 'height': 1080})
    write_json(str(page / 'visuals' / 'footer' / 'visual.json'), {
        'name': 'footer', 'position': {'x': 54, 'y': 1029, 'width': 400, 'height': 40},
        'visualGroup': {'displayName': 'FOOTER'}})
    write_json(str(page / 'visuals' / 'absolute' / 'visual.json'), {
        'name': 'absolute', 'parentGroupName': 'footer',
        'position': {'x': 54, 'y': 1029, 'width': 200, 'height': 40}, 'visual': {'visualType': 'textbox'}})
    write_json(str(page / 'visuals' / 'relative' / 'visual.json'), {
        'name': 'relative', 'parentGroupName': 'footer',
        'position': {'x': 0, 'y': 0, 'width': 200, 'height': 40}, 'visual': {'visualType': 'textbox'}})

    stdout, maps = run_map(tmp_path / 'project', tmp_path / 'out')
    report = maps['report-map.md']
    assert maps['model-map.md'] is None    # no semantic model in this fixture, so no model map

    lines = {name: line for line in report.splitlines() for name in ('footer', 'absolute', 'relative')
             if '`%s`' % name in line}
    assert '@108,2058' in lines['absolute'] and 'OFF-PAGE' in lines['absolute']
    assert '@54,1029' in lines['relative'] and 'OFF-PAGE' not in lines['relative']
    assert 'OFF-PAGE' not in lines['footer']
    assert '1 visible visual(s) land outside their page' in report
    assert '1 OFF-PAGE' in stdout
