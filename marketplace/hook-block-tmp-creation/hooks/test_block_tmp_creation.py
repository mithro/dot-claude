#!/usr/bin/env python3
"""Tests for block_tmp_creation.py hook."""

import json
import os
import subprocess
import sys

# Import from same directory
sys.path.insert(0, os.path.dirname(__file__))
import block_tmp_creation

HOOK = os.path.join(os.path.dirname(__file__), 'block_tmp_creation.py')


def denied(command):
    return block_tmp_creation.check_bash(command) is not None


# --- Existing creation patterns ---

def test_redirect_denied():
    assert denied('echo hi > /tmp/out.txt')


def test_append_redirect_denied():
    assert denied('make 2>> /tmp/build.log')


def test_tee_denied():
    assert denied('make | tee -a /tmp/build.log')


def test_cp_denied():
    assert denied('cp results.json /tmp/results.json')


def test_mkdir_denied():
    assert denied('mkdir -p /tmp/work')


def test_touch_denied():
    assert denied('touch /tmp/marker')


def test_bare_mktemp_denied():
    assert denied('d=$(mktemp -d)')


def test_mktemp_custom_dir_allowed():
    assert not denied('d=$(mktemp -d -p ./tmp)')


# --- Read-only inspection stays allowed ---

def test_du_allowed():
    assert not denied('du -xh --max-depth=2 /tmp')


def test_ls_allowed():
    assert not denied('ls -la /tmp/claude-1000')


def test_df_allowed():
    assert not denied('df -h /tmp')


def test_find_allowed():
    assert not denied("find /tmp/claude-1000 -maxdepth 2 -mmin -5 -printf '%p\\n'")


def test_git_commit_message_allowed():
    assert not denied('git commit -m "Stop writing to /tmp/ in tests"')


def test_rsync_exclude_pattern_allowed():
    """--exclude/--include/--filter take patterns, not output paths."""
    assert not denied("rsync -aHAX -x --exclude='/tmp/*' --exclude='/var/tmp/*' / /backups/root/")


def test_tmp_prefix_not_tmp_dir():
    assert not denied('echo hi > /tmpfoo/out.txt')


# --- Indirect writes seen filling /tmp on big-storage ---

def test_variable_assignment_denied():
    """A /tmp path saved in a variable is written to later via $P/..."""
    assert denied('P=/tmp/claude-1000/proj/sess/scratchpad/p2-11; '
                  'until [ -f $P/done.json ]; do sleep 30; done')


def test_tmpdir_assignment_denied():
    """Pointing TMPDIR at /tmp sends tempfile/mktemp output there."""
    assert denied('TMPDIR=/tmp/claude-1000/x/scratchpad/probe/tmp uv run probe.py')


def test_export_tmpdir_denied():
    assert denied('export TMPDIR=/tmp/work && uv run probe.py')


def test_quoted_assignment_denied():
    assert denied('OUT="/tmp/run1" ./build.sh')


def test_long_option_value_denied():
    assert denied('uv run python -m gf180tcad.tcad meshconv --resume '
                  '/tmp/claude-1000/a/b/scratchpad/p2-11/meshconv2d/run')


def test_long_option_equals_value_denied():
    assert denied('uv run tool --progress-dir=/tmp/claude-1000/a/progress')


def test_short_option_value_denied():
    assert denied('gcc -o /tmp/a.out main.c')


def test_docker_bind_mount_denied():
    assert denied('docker run --rm -v /tmp/claude-1000/a/level3:/work/out:rw img')


def test_docker_mount_flag_denied():
    assert denied('docker run --mount type=bind,src=/tmp/out,dst=/out img')


def test_cd_into_tmp_denied():
    assert denied('cd /tmp/claude-1000/a/scratchpad && git clone https://x/y.git')


# --- Write/Edit tool paths ---

def test_write_to_harness_scratchpad_denied():
    assert block_tmp_creation.check_file_path(
        {'file_path': '/tmp/claude-1000/-home-tim-x/sess/scratchpad/a.py'}
    ) is not None


def test_write_outside_tmp_allowed():
    assert block_tmp_creation.check_file_path(
        {'file_path': '/home/tim/.claude-tmp/claude-1000/x/scratchpad/a.py'}
    ) is None


# --- Deny message explains the real reason ---

def test_deny_message_names_scratchpad():
    assert 'scratchpad' in block_tmp_creation.DENY_MESSAGE


def test_deny_message_names_tmpfs():
    assert 'tmpfs' in block_tmp_creation.DENY_MESSAGE


# --- End-to-end through stdin/stdout ---

def run_hook(payload):
    result = subprocess.run(
        [sys.executable, HOOK], input=json.dumps(payload),
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_main_denies_bash():
    out = run_hook({'tool_name': 'Bash',
                    'tool_input': {'command': 'P=/tmp/x; echo hi > $P/a'}})
    assert out['hookSpecificOutput']['permissionDecision'] == 'deny'


def test_main_allows_read_only_bash():
    out = run_hook({'tool_name': 'Bash',
                    'tool_input': {'command': 'du -sh /tmp'}})
    assert out == {}
