"""Checks on the visual reference built by scripts/build-visual-catalog.py from Microsoft's sample report."""
import glob
import importlib.util
import json
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('build_visual_catalog', os.path.join(REPO, 'scripts', 'build-visual-catalog.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

REPORT = os.path.join(builder.REFERENCE, builder.REPORT)
# Custom visual types end in a 32-character GUID; built-in ones don't
CUSTOM_TYPE = re.compile(r'[0-9A-Fa-f]{32}$')
# Leaves a clone folder path of about 130 characters on Windows' 260 limit
MAX_TRACKED_PATH = 130


def text_of(path):
    return open(path, encoding='utf-8', newline='').read().replace('\r\n', '\n')


def test_catalog_matches_a_fresh_build(tmp_path):
    """Protects against hand edits to the catalog, or a reference change without a rebuild."""
    out = tmp_path / 'catalog'
    built = builder.build_catalog(str(out))
    committed = {os.path.relpath(p, builder.CATALOG).replace(os.sep, '/')
                 for p in glob.glob(os.path.join(builder.CATALOG, '**', '*'), recursive=True) if os.path.isfile(p)}
    assert committed == set(built)
    for name, text in built.items():
        assert text_of(os.path.join(builder.CATALOG, *name.split('/'))) == text, name


def test_reference_report_has_no_custom_visuals():
    """Protects the license boundary: custom visuals aren't covered by the sample's MIT license."""
    assert not os.path.exists(os.path.join(REPORT, 'CustomVisuals'))
    report = json.loads(text_of(os.path.join(REPORT, 'definition', 'report.json')))
    assert 'publicCustomVisuals' not in report
    assert not [p for p in report['resourcePackages'] if p.get('type') == 'CustomVisual']
    for f in glob.glob(os.path.join(REPORT, 'definition', 'pages', '*', 'visuals', '*', 'visual.json')):
        visual_type = json.loads(text_of(f)).get('visual', {}).get('visualType', '')
        assert not CUSTOM_TYPE.search(visual_type), f


def test_catalog_examples_are_built_in_and_listed():
    """Protects the index: every example parses, is a built-in visual, and can be found from the README."""
    index = text_of(os.path.join(builder.CATALOG, 'README.md'))
    examples = glob.glob(os.path.join(builder.CATALOG, '**', '*.json'), recursive=True)
    assert examples
    for f in examples:
        name = os.path.relpath(f, builder.CATALOG).replace(os.sep, '/')
        assert '(%s)' % name in index, name
        assert not CUSTOM_TYPE.search(json.loads(text_of(f)).get('visual', {}).get('visualType', '')), name


def test_examples_show_what_their_labels_claim():
    """Protects the selection rules: a loose match once labelled a slicer as a matrix example."""
    def visual_type(name):
        return json.loads(text_of(os.path.join(builder.CATALOG, 'features', name + '.json')))['visual']['visualType']
    if os.path.exists(os.path.join(builder.CATALOG, 'features', 'matrix-expanded.json')):
        assert visual_type('matrix-expanded') == 'pivotTable'
    assert visual_type('button-text') == 'actionButton'
    button = json.loads(text_of(os.path.join(builder.CATALOG, 'features', 'button-text.json')))
    assert button['visual']['objects']['text']


def test_microsoft_notice_ships_with_every_copy():
    """Protects the MIT condition: the notice stays with all copies or substantial portions."""
    for folder in (builder.REFERENCE, builder.CATALOG):
        notice = text_of(os.path.join(folder, 'LICENSE-MICROSOFT.txt'))
        assert 'Copyright (c) Microsoft Corporation' in notice
        assert 'shall be included in all' in notice


def test_page_links_all_resolve():
    """Protects the removed page: an arrow left pointing at it would be a dead button with no error."""
    definition = os.path.join(REPORT, 'definition')
    pages = json.loads(text_of(os.path.join(definition, 'pages', 'pages.json')))['pageOrder']
    for f in glob.glob(os.path.join(definition, 'pages', '*', 'visuals', '*', 'visual.json')):
        visual = json.loads(text_of(f)).get('visual', {})
        for link in visual.get('visualContainerObjects', {}).get('visualLink', []):
            target = link.get('properties', {}).get('navigationSection', {}).get('expr', {}).get('Literal', {}).get('Value')
            if target:
                assert target.strip("'") in pages, f


def test_no_page_is_left_empty():
    """Protects against empty pages: the sample is a gallery, so a page with only navigation and text shows nothing."""
    definition = os.path.join(REPORT, 'definition')
    frame = {'pageNavigator', 'textbox', 'actionButton', None}
    for page_id in json.loads(text_of(os.path.join(definition, 'pages', 'pages.json')))['pageOrder']:
        visuals = glob.glob(os.path.join(definition, 'pages', page_id, 'visuals', '*', 'visual.json'))
        kinds = {json.loads(text_of(f)).get('visual', {}).get('visualType') for f in visuals}
        assert kinds - frame, page_id


def test_power_bi_logos_are_replaced():
    """Protects the trademark line: MIT grants no rights to the logo, so only the placeholder may ship under its names."""
    logos = glob.glob(os.path.join(REPORT, 'StaticResources', 'RegisteredResources', builder.LOGO_FILES))
    assert logos
    for logo in logos:
        with open(logo, 'rb') as f:
            assert f.read() == builder.placeholder_png()


def test_tracked_paths_stay_clonable_on_windows():
    """Protects Windows clones: past 260 characters a checkout fails, so leave room for the clone folder's own path."""
    tracked = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
    assert tracked
    longest = max(tracked, key=len)
    assert len(longest) <= MAX_TRACKED_PATH, longest
