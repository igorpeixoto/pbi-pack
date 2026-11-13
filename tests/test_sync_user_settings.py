"""Checks the three-way merge of user/settings.json into ~/.claude/settings.json, in a throwaway HOME."""
import json
import os
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, 'scripts', 'sync-user-settings.sh').replace('\\', '/')

pytestmark = pytest.mark.skipif(not (shutil.which('sh') and shutil.which('python')),
                                reason='the script needs sh and python on PATH')

PACK_V1 = {
    '$comment': 'never synced',
    'model': 'sonnet[1m]',
    'effortLevel': 'high',
    'modelSettings': {'claude-opus-5-5': {'effortLevel': 'high'}},
    'env': {'CLAUDE_CODE_AUTO_COMPACT_WINDOW': '250000', 'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'},
    'permissions': {'defaultMode': 'default', 'allow': ['Bash(git add *)', 'Bash(git tag *)']},
}


def without_window_variable(pack):
    """The same pack after it moved the window from the environment variable to the setting."""
    new = json.loads(json.dumps(pack))
    del new['env']['CLAUDE_CODE_AUTO_COMPACT_WINDOW']
    new['autoCompactWindow'] = 250000
    return new


class Machine:
    """A clone holding user/settings.json, and the home folder the script merges it into."""

    def __init__(self, tmp_path):
        self.work = tmp_path / 'clone'
        self.home = tmp_path / 'home'
        (self.work / 'user').mkdir(parents=True)
        (self.home / '.claude').mkdir(parents=True)
        self.settings = self.home / '.claude' / 'settings.json'
        self.state = self.home / '.claude' / 'pbi-sync' / 'state' / 'user-settings.json'
        self.pack = self.work / 'user' / 'settings.json'

    def sync(self, pack=None, *args):
        if pack is not None:
            self.pack.write_text(json.dumps(pack, indent=2), encoding='utf-8')
        # The ceiling keeps git from finding a repo above the temp folder, so the script stays in cwd
        env = dict(os.environ, HOME=str(self.home).replace('\\', '/'),
                   GIT_CEILING_DIRECTORIES=str(self.work.parent))
        done = subprocess.run(['sh', SCRIPT, *args], cwd=str(self.work), env=env,
                              capture_output=True, text=True, check=True)
        return done.stdout, done.stderr

    def read(self):
        return json.loads(self.settings.read_text(encoding='utf-8'))

    def write(self, data):
        self.settings.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def edit(self, change):
        data = self.read()
        change(data)
        self.write(data)


@pytest.fixture
def machine(tmp_path):
    return Machine(tmp_path)


def test_first_run_takes_the_pack_and_removes_nothing(machine):
    machine.write({'model': 'opus', 'statusLine': {'type': 'command'}, 'env': {'MY_OWN': '1'},
                   'permissions': {'allow': ['Bash(ls *)']}})
    out, err = machine.sync(PACK_V1)
    got = machine.read()

    assert got['model'] == 'sonnet[1m]'
    assert got['statusLine'] == {'type': 'command'}
    assert got['env'] == {'MY_OWN': '1', 'CLAUDE_CODE_AUTO_COMPACT_WINDOW': '250000',
                          'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'}
    assert got['permissions']['allow'] == ['Bash(ls *)', 'Bash(git add *)', 'Bash(git tag *)']
    assert '$comment' not in got
    assert 'applied' in out and err == ''


def test_second_run_changes_nothing(machine):
    machine.sync(PACK_V1)
    before = machine.settings.read_bytes()
    out, err = machine.sync()

    assert machine.settings.read_bytes() == before
    assert out == '' and err == ''


def test_variable_dropped_from_the_pack_is_removed_where_unchanged(machine):
    machine.sync(PACK_V1)
    machine.edit(lambda d: d['env'].update(MY_OWN='1'))
    out, err = machine.sync(without_window_variable(PACK_V1))
    got = machine.read()

    assert got['env'] == {'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet', 'MY_OWN': '1'}
    assert got['autoCompactWindow'] == 250000
    assert got['modelSettings'] == {'claude-opus-5-5': {'effortLevel': 'high'}}
    assert 'CLAUDE_CODE_AUTO_COMPACT_WINDOW (removed' in out and err == ''
    assert machine.sync() == ('', '')


def test_variable_dropped_from_the_pack_is_kept_where_changed(machine):
    machine.sync(PACK_V1)
    machine.edit(lambda d: d['env'].update(CLAUDE_CODE_AUTO_COMPACT_WINDOW='400000'))
    _, err = machine.sync(without_window_variable(PACK_V1))
    got = machine.read()

    assert got['env']['CLAUDE_CODE_AUTO_COMPACT_WINDOW'] == '400000'
    assert got['autoCompactWindow'] == 250000
    assert 'env.CLAUDE_CODE_AUTO_COMPACT_WINDOW is no longer in the pack' in err
    # Said once; from here on the variable is the machine's own
    assert machine.sync() == ('', '')
    assert machine.read()['env']['CLAUDE_CODE_AUTO_COMPACT_WINDOW'] == '400000'


def test_emptied_parent_goes_with_its_last_entry(machine):
    machine.sync(PACK_V1)
    pack = json.loads(json.dumps(PACK_V1))
    del pack['env'], pack['modelSettings'], pack['effortLevel']
    machine.sync(pack)
    got = machine.read()

    assert 'env' not in got and 'modelSettings' not in got and 'effortLevel' not in got
    assert got['model'] == 'sonnet[1m]'


def test_permission_list_dropped_from_the_pack_takes_its_entries_back(machine):
    machine.sync(PACK_V1)
    machine.edit(lambda d: d['permissions']['allow'].append('Bash(ls *)'))
    pack = json.loads(json.dumps(PACK_V1))
    del pack['permissions']['allow']
    machine.sync(pack)

    assert machine.read()['permissions'] == {'defaultMode': 'default', 'allow': ['Bash(ls *)']}


def test_model_settings_are_merged_per_model_and_key(machine):
    machine.sync(PACK_V1)

    # What /autocompact and /effort save: a window for the listed model, and a model the pack doesn't list
    def saved_from_a_session(d):
        d['modelSettings']['claude-opus-5-5']['autoCompactWindow'] = 400000
        d['modelSettings']['claude-sonnet-5-5'] = {'autoCompactWindow': 300000}
    machine.edit(saved_from_a_session)
    assert machine.sync() == ('', '')

    pack = json.loads(json.dumps(PACK_V1))
    pack['modelSettings']['claude-opus-5-5']['effortLevel'] = 'xhigh'
    out, err = machine.sync(pack)

    assert machine.read()['modelSettings'] == {
        'claude-opus-5-5': {'effortLevel': 'xhigh', 'autoCompactWindow': 400000},
        'claude-sonnet-5-5': {'autoCompactWindow': 300000},
    }
    assert 'modelSettings.claude-opus-5-5.effortLevel' in out and err == ''


def test_state_written_when_model_settings_was_one_block_still_merges(machine):
    machine.sync(PACK_V1)
    # The state file as the script wrote it before modelSettings was managed per model
    old = json.loads(machine.state.read_text(encoding='utf-8'))
    old = {k: v for k, v in old.items() if not k.startswith('modelSettings')}
    old['modelSettings'] = PACK_V1['modelSettings']
    machine.state.write_text(json.dumps(old), encoding='utf-8')
    machine.edit(lambda d: d['modelSettings'].update({'claude-sonnet-5-5': {'autoCompactWindow': 300000}}))

    assert machine.sync() == ('', '')
    pack = json.loads(json.dumps(PACK_V1))
    del pack['modelSettings']
    machine.sync(pack)
    assert machine.read()['modelSettings'] == {'claude-sonnet-5-5': {'autoCompactWindow': 300000}}


def test_local_change_is_kept_and_reported_once(machine):
    machine.sync(PACK_V1)
    machine.edit(lambda d: d.update(model='opus'))
    _, err = machine.sync()

    assert machine.read()['model'] == 'opus'
    assert 'model is changed on this machine' in err
    assert machine.sync() == ('', '')


def test_capture_copies_a_per_model_change_into_the_pack(machine):
    machine.sync(PACK_V1)
    machine.edit(lambda d: d['modelSettings']['claude-opus-5-5'].update(effortLevel='medium'))
    out, _ = machine.sync(None, '--capture')

    assert 'modelSettings.claude-opus-5-5.effortLevel' in out
    assert json.loads(machine.pack.read_text(encoding='utf-8'))['modelSettings'] == {
        'claude-opus-5-5': {'effortLevel': 'medium'}}
