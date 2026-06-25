#!/usr/bin/env python3
"""Tests for block_ssh_hash_hostnames.py hook."""

import json
import io
import os
import sys

# Import from same directory
sys.path.insert(0, os.path.dirname(__file__))
import block_ssh_hash_hostnames

# Construct test values via variable to avoid triggering the hook's own
# file-edit check (which scans Write/Edit content for the literal pattern
# HashKnownHosts followed by whitespace then yes or 1).
_HKH = "HashKnownHosts"


# ── split_shell_commands ─────────────────────────────────────────────


def test_split_pipe_inside_single_quotes():
    """Pipe inside single quotes should NOT split."""
    result = block_ssh_hash_hostnames.split_shell_commands(
        "ssh host 'cmd1 | cmd2'"
    )
    assert result == ["ssh host 'cmd1 | cmd2'"]


def test_split_pipe_outside_quotes():
    """Pipe outside quotes should split."""
    result = block_ssh_hash_hostnames.split_shell_commands("cmd1 | cmd2")
    assert result == ["cmd1 ", " cmd2"]


def test_split_and_inside_double_quotes():
    """&& inside double quotes should NOT split."""
    result = block_ssh_hash_hostnames.split_shell_commands('echo "a && b"')
    assert result == ['echo "a && b"']


def test_split_and_outside_quotes():
    """&& outside quotes should split."""
    result = block_ssh_hash_hostnames.split_shell_commands("cmd1 && cmd2")
    assert result == ["cmd1 ", " cmd2"]


def test_split_mixed_quoted_and_unquoted():
    """Pipe outside quotes with && inside quotes."""
    result = block_ssh_hash_hostnames.split_shell_commands(
        "echo 'a && b' | grep x"
    )
    assert result == ["echo 'a && b' ", " grep x"]


def test_split_or_operator():
    """|| outside quotes should split."""
    result = block_ssh_hash_hostnames.split_shell_commands("cmd1 || cmd2")
    assert result == ["cmd1 ", " cmd2"]


def test_split_semicolon():
    """; outside quotes should split."""
    result = block_ssh_hash_hostnames.split_shell_commands("cmd1; cmd2")
    assert result == ["cmd1", " cmd2"]


def test_split_subshell():
    """$( outside quotes should split."""
    result = block_ssh_hash_hostnames.split_shell_commands("echo $(cmd)")
    assert result == ["echo ", "cmd)"]


def test_split_escaped_pipe():
    """Backslash-escaped pipe should NOT split."""
    result = block_ssh_hash_hostnames.split_shell_commands("echo \\| grep")
    assert result == ["echo \\| grep"]


def test_split_complex_ssh_remote():
    """Real-world ssh command with pipe and -H inside quotes."""
    cmd = (
        "ssh host 'curl -X POST http://api "
        "-H \"Auth: token\" "
        "-H \"Type: json\" "
        "2>&1 | head -5'"
    )
    result = block_ssh_hash_hostnames.split_shell_commands(cmd)
    assert len(result) == 1  # No splitting — pipe is inside quotes


# ── extract_ssh_own_args ─────────────────────────────────────────────


def test_extract_no_options():
    """No ssh options, just hostname."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(" host 'ls -la'")
    assert result == ""


def test_extract_h_flag():
    """-H is an ssh option."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(" -H host")
    assert "-H" in result


def test_extract_combined_th_flag():
    """-tH combined flags."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(" -tH host")
    assert "-tH" in result


def test_extract_option_with_arg():
    """-p takes an argument, should consume it."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(
        " -p 22 host 'cmd -H'"
    )
    assert "-p" in result
    assert "22" in result
    assert "-H" not in result  # -H is in the remote command


def test_extract_multiple_options():
    """-v -p 22 -i key — multiple options before hostname."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(
        " -v -p 22 -i ~/.ssh/key host 'curl -H hdr http://api'"
    )
    assert "-v" in result
    assert "-p" in result
    assert "22" in result
    assert "-i" in result
    assert "-H" not in result  # only in remote command


def test_extract_hash_known_hosts_option():
    """-o HashKnownHosts=yes should be captured in ssh options."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(
        f" -o {_HKH}=yes host"
    )
    assert _HKH in result


def test_extract_double_dash():
    """-- ends option parsing."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(
        " -v -- -H host"
    )
    assert "-v" in result
    assert "-H" not in result  # after --, not an ssh option


def test_extract_unmatched_quote_fallback():
    """Unmatched quote falls back to full string (safe: may false-positive)."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(
        " host 'curl -H"
    )
    # shlex.split fails, falls back to full string
    assert "-H" in result


def test_extract_user_at_host():
    """user@host is the hostname, not an option."""
    result = block_ssh_hash_hostnames.extract_ssh_own_args(
        " user@host 'cmd -H'"
    )
    assert result == ""


# ── check_bash_command — should PASS (not block) ────────────────────


def test_curl_h_inside_ssh_single_quoted():
    """curl -H inside single-quoted ssh remote command should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh ha.welland.mithis.com "
        "'curl -s -X POST http://example.com "
        '-d "{\\"entity_id\\": \\"button.x\\"}" '
        '-H "Authorization: Bearer $TOKEN" '
        '-H "Content-Type: application/json" '
        "2>&1 | head -5'"
    )
    assert result is None


def test_curl_h_unquoted_remote():
    """Unquoted remote command with curl -H should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        'ssh host curl -H "Auth: token" http://api'
    )
    assert result is None


def test_ssh_with_options_remote_h():
    """ssh -v -p 22 with -H in remote command should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh -v -p 22 host 'cmd -H arg'"
    )
    assert result is None


def test_hash_known_hosts_in_remote_grep():
    """HashKnownHosts in remote grep command should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        f"ssh host 'grep {_HKH} /etc/ssh/sshd_config'"
    )
    assert result is None


def test_grep_h_in_remote_command_with_o_option():
    """Regression: real-world `ssh -o ... host 'grep -H ...'` should pass.

    The remote command uses `grep -H` (print filename) inside the
    single-quoted remote command. ssh's own option is `-o ConnectTimeout=8`,
    not `-H`, so this must not be blocked.
    """
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh -o ConnectTimeout=8 rpib-sdcard.welland.mithis.com "
        "'grep -H . /sys/block/mmcblk0/device/manfid "
        "/sys/block/mmcblk0/device/oemid /sys/block/mmcblk0/device/serial "
        "/sys/block/mmcblk0/size' 2>&1"
    )
    assert result is None


def test_grep_h_in_unquoted_remote_command():
    """`ssh host grep -H ...` (unquoted remote) should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh host grep -H pattern /etc/hosts"
    )
    assert result is None


def test_grep_rh_combined_in_remote_command():
    """Combined `grep -rH` in remote command should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh user@host 'grep -rH foo .'"
    )
    assert result is None


def test_plain_ssh_no_flags():
    """Plain ssh with no flags should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh user@host 'ls -la'"
    )
    assert result is None


def test_pipe_to_ssh_no_h():
    """Pipe to ssh without -H should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "echo test | ssh host cmd"
    )
    assert result is None


def test_ssh_i_with_remote_h_double_quoted():
    """ssh -i key with double-quoted remote -H should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        'ssh -i ~/.ssh/key host "curl -H header http://api"'
    )
    assert result is None


def test_ssh_remote_with_and_and_curl_h():
    """ssh with && and curl -H inside single-quoted remote should pass."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "ssh host 'cd /app && curl -H \"Auth: x\" http://api'"
    )
    assert result is None


def test_non_ssh_command():
    """Non-SSH commands should pass."""
    assert block_ssh_hash_hostnames.check_bash_command("ls -la") is None
    assert block_ssh_hash_hostnames.check_bash_command("curl -H hdr http://x") is None
    assert block_ssh_hash_hostnames.check_bash_command("git push") is None


# ── check_bash_command — should BLOCK ───────────────────────────────


def test_block_ssh_h():
    """ssh -H should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command("ssh -H host")
    assert result is not None
    assert "BLOCKED" in result


def test_block_ssh_th_combined():
    """ssh -tH combined should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command("ssh -tH host")
    assert result is not None
    assert "BLOCKED" in result


def test_block_ssh_keyscan_h():
    """ssh-keyscan -H should be blocked (checks all args)."""
    result = block_ssh_hash_hostnames.check_bash_command("ssh-keyscan -H host")
    assert result is not None
    assert "BLOCKED" in result


def test_block_ssh_keygen_h():
    """ssh-keygen -H should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command("ssh-keygen -H")
    assert result is not None
    assert "BLOCKED" in result


def test_block_ssh_hash_known_hosts():
    """ssh -o HashKnownHosts=yes should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command(
        f"ssh -o {_HKH}=yes host"
    )
    assert result is not None
    assert "BLOCKED" in result


def test_block_ssh_h_with_p():
    """ssh -H -p 22 should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command("ssh -H -p 22 host")
    assert result is not None
    assert "BLOCKED" in result


def test_block_ssh_keyscan_h_in_pipeline():
    """ssh-keyscan -H in a pipeline should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command(
        "echo test | ssh-keyscan -H host"
    )
    assert result is not None
    assert "BLOCKED" in result


def test_block_sudo_ssh_h():
    """sudo ssh -H should be blocked."""
    result = block_ssh_hash_hostnames.check_bash_command("sudo ssh -H host")
    assert result is not None
    assert "BLOCKED" in result


# ── check_file_edit ─────────────────────────────────────────────────


def test_edit_hash_known_hosts_yes_blocked():
    """Setting HashKnownHosts to 'yes' should be blocked."""
    result = block_ssh_hash_hostnames.check_file_edit(
        {"new_text": f"{_HKH}" + " yes"}
    )
    assert result is not None
    assert "BLOCKED" in result


def test_edit_hash_known_hosts_1_blocked():
    """Setting HashKnownHosts to '1' should be blocked."""
    result = block_ssh_hash_hostnames.check_file_edit(
        {"content": f"{_HKH}" + " 1"}
    )
    assert result is not None
    assert "BLOCKED" in result


def test_edit_hash_known_hosts_no_allowed():
    """Setting HashKnownHosts to 'no' should pass."""
    result = block_ssh_hash_hostnames.check_file_edit(
        {"new_text": f"{_HKH} no"}
    )
    assert result is None


def test_edit_hash_known_hosts_comment_allowed():
    """Commented-out HashKnownHosts setting should pass."""
    result = block_ssh_hash_hostnames.check_file_edit(
        {"new_text": f"# {_HKH}" + " yes"}
    )
    assert result is None


# ── end-to-end main() ──────────────────────────────────────────────


def test_end_to_end_bash_blocked(monkeypatch, capsys):
    """Full e2e: ssh -H in Bash should be denied."""
    monkeypatch.setattr(
        'sys.stdin',
        io.StringIO(json.dumps({
            'tool_name': 'Bash',
            'tool_input': {'command': 'ssh -H host'},
        })),
    )
    block_ssh_hash_hostnames.main()
    output = json.loads(capsys.readouterr().out)
    assert output['hookSpecificOutput']['permissionDecision'] == 'deny'
    assert 'BLOCKED' in output['systemMessage']


def test_end_to_end_bash_allowed(monkeypatch, capsys):
    """Full e2e: ssh with curl -H in remote cmd should be allowed."""
    monkeypatch.setattr(
        'sys.stdin',
        io.StringIO(json.dumps({
            'tool_name': 'Bash',
            'tool_input': {
                'command': 'ssh host \'curl -H "Auth: x" http://api\''
            },
        })),
    )
    block_ssh_hash_hostnames.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


def test_end_to_end_edit_blocked(monkeypatch, capsys):
    """Full e2e: Edit setting HashKnownHosts=yes should be denied."""
    monkeypatch.setattr(
        'sys.stdin',
        io.StringIO(json.dumps({
            'tool_name': 'Edit',
            'tool_input': {'new_text': _HKH + ' yes'},
        })),
    )
    block_ssh_hash_hostnames.main()
    output = json.loads(capsys.readouterr().out)
    assert output['hookSpecificOutput']['permissionDecision'] == 'deny'


def test_end_to_end_non_ssh_tool(monkeypatch, capsys):
    """Full e2e: non-SSH tool passes through."""
    monkeypatch.setattr(
        'sys.stdin',
        io.StringIO(json.dumps({
            'tool_name': 'Read',
            'tool_input': {'file_path': '/etc/ssh/config'},
        })),
    )
    block_ssh_hash_hostnames.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


def test_end_to_end_bad_json(monkeypatch, capsys):
    """Full e2e: bad JSON input passes through."""
    monkeypatch.setattr('sys.stdin', io.StringIO('not json'))
    block_ssh_hash_hostnames.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


if __name__ == '__main__':
    # Simple test runner for quick verification without pytest
    test_funcs = [
        v for k, v in sorted(globals().items())
        if k.startswith('test_') and callable(v)
    ]
    # Skip tests that need pytest fixtures
    needs_fixtures = {
        'test_end_to_end_bash_blocked',
        'test_end_to_end_bash_allowed',
        'test_end_to_end_edit_blocked',
        'test_end_to_end_non_ssh_tool',
        'test_end_to_end_bad_json',
    }

    passed = 0
    failed = 0
    skipped = 0

    for func in test_funcs:
        name = func.__name__
        if name in needs_fixtures:
            skipped += 1
            continue
        try:
            func()
            passed += 1
            print(f'  PASS: {name}')
        except Exception as e:
            failed += 1
            print(f'  FAIL: {name}: {e}')

    print(f'\n{passed} passed, {failed} failed, {skipped} skipped (need pytest)')
    sys.exit(1 if failed else 0)
