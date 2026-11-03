"""Checks that the demo template still opens with its data: the saved model data and the model must match."""
import hashlib
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(REPO, 'pbi-starter', 'templates', 'demo', 'Template-DEMO.SemanticModel')
CACHE = os.path.join(MODEL, '.pbi', 'cache.abf')
# Saved together from Desktop. Desktop drops saved data whose model changed, and the report opens empty,
# so after an edit under definition/: refresh in Desktop, save, then update both values.
MODEL_SHA = 'ee0655817095c5d8'
CACHE_SHA = '1c33b2e1876a5258'


def model_sha():
    h = hashlib.sha256()
    for path in sorted(os.path.join(d, f) for d, _, fs in os.walk(os.path.join(MODEL, 'definition'))
                       for f in fs if f.endswith('.tmdl')):
        rel = os.path.relpath(path, MODEL).replace(os.sep, '/')
        # Desktop saves CRLF and git stores LF, so compare the content, not the line endings
        h.update(rel.encode() + b'\0' + open(path, 'rb').read().replace(b'\r\n', b'\n') + b'\0')
    return h.hexdigest()[:16]


def test_saved_data_is_tracked():
    """Protects the populated first open: .gitignore ignores cache.abf everywhere else."""
    subprocess.run(['git', 'ls-files', '--error-unmatch', os.path.relpath(CACHE, REPO)],
                   cwd=REPO, capture_output=True, check=True)


def test_saved_data_matches_the_model():
    cache = hashlib.sha256(open(CACHE, 'rb').read()).hexdigest()[:16]
    assert (model_sha(), cache) == (MODEL_SHA, CACHE_SHA), (
        'The demo model or its saved data changed without the other. Refresh and save in Desktop, '
        'then set MODEL_SHA and CACHE_SHA to the values on the left.')


def test_data_folder_default_is_the_documented_clone_path():
    text = open(os.path.join(MODEL, 'definition', 'expressions.tmdl'), encoding='utf-8').read()
    folder = re.search(r'^expression DataFolder = "([^"]*)"', text, re.M).group(1)
    assert folder == 'C:\\src\\pbi-pack\\demo\\data\\'
    for doc in ('README.md', os.path.join('demo', 'README.md')):
        assert folder in open(os.path.join(REPO, doc), encoding='utf-8').read(), doc
