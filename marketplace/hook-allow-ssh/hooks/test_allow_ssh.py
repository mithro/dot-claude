#!/usr/bin/env python3
"""Tests for allow_ssh.py hook."""

import json
import os
import sys
import tempfile

# Import from same directory
sys.path.insert(0, os.path.dirname(__file__))
import allow_ssh


# Test config
TEST_CONFIG = [
    {"host": "server.example.com", "user": "tim", "sudo": True},
    {"host": "workstation.local", "user": "root", "sudo": False},
    {"host": "anyuser.example.com"},  # no user restriction, no sudo
]


def test_parse_ssh_basic():
    """ssh user@host command."""
    result = allow_ssh.parse_ssh_command(
        ['tim@server.example.com', 'ls', '-la']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'
    assert remote_cmd == ['ls', '-la']


def test_parse_ssh_no_user():
    """ssh host command."""
    result = allow_ssh.parse_ssh_command(['server.example.com', 'uptime'])
    assert result is not None
    user, host, remote_cmd = result
    assert user is None
    assert host == 'server.example.com'
    assert remote_cmd == ['uptime']


def test_parse_ssh_with_flags():
    """ssh -t -o StrictHostKeyChecking=accept-new user@host cmd."""
    result = allow_ssh.parse_ssh_command(
        ['-t', '-o', 'StrictHostKeyChecking=accept-new',
         'tim@server.example.com', 'sudo', 'systemctl', 'restart', 'nginx']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'
    assert remote_cmd == ['sudo', 'systemctl', 'restart', 'nginx']


def test_parse_ssh_l_flag():
    """ssh -l user host command."""
    result = allow_ssh.parse_ssh_command(
        ['-l', 'tim', 'server.example.com', 'whoami']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'
    assert remote_cmd == ['whoami']


def test_parse_ssh_l_combined():
    """ssh -ltim host command."""
    result = allow_ssh.parse_ssh_command(
        ['-ltim', 'server.example.com', 'whoami']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'


def test_parse_ssh_port_flag():
    """ssh -p 2222 user@host cmd."""
    result = allow_ssh.parse_ssh_command(
        ['-p', '2222', 'tim@server.example.com', 'ls']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'


def test_parse_ssh_combined_no_arg_flags():
    """ssh -tt user@host cmd."""
    result = allow_ssh.parse_ssh_command(
        ['-tt', 'tim@server.example.com', 'sudo', 'bash']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'


def test_parse_ssh_identity_file():
    """ssh -i ~/.ssh/id_rsa user@host cmd."""
    result = allow_ssh.parse_ssh_command(
        ['-i', '/home/tim/.ssh/id_rsa', 'tim@server.example.com', 'ls']
    )
    assert result is not None
    user, host, remote_cmd = result
    assert user == 'tim'
    assert host == 'server.example.com'


def test_parse_ssh_no_host():
    """ssh -V (no host)."""
    result = allow_ssh.parse_ssh_command(['-V'])
    assert result is None


def test_parse_ssh_user_at_overrides_l():
    """user@ in host token should override -l."""
    result = allow_ssh.parse_ssh_command(
        ['-l', 'other', 'tim@server.example.com', 'ls']
    )
    assert result is not None
    user, host, remote_cmd = result
    # user@ takes precedence
    assert user == 'tim'
    assert host == 'server.example.com'


def test_parse_scp_remote_target():
    """scp file user@host:/tmp/file."""
    targets = allow_ssh.parse_scp_rsync_targets(
        ['localfile.txt', 'tim@server.example.com:/tmp/upload.txt']
    )
    assert len(targets) == 1
    user, host, path = targets[0]
    assert user == 'tim'
    assert host == 'server.example.com'
    assert path == '/tmp/upload.txt'


def test_parse_scp_no_user():
    """scp file host:/tmp/file."""
    targets = allow_ssh.parse_scp_rsync_targets(
        ['localfile.txt', 'server.example.com:/tmp/upload.txt']
    )
    assert len(targets) == 1
    user, host, path = targets[0]
    assert user is None
    assert host == 'server.example.com'
    assert path == '/tmp/upload.txt'


def test_parse_scp_with_flags():
    """scp -P 2222 file user@host:/tmp/file."""
    targets = allow_ssh.parse_scp_rsync_targets(
        ['-P', '2222', 'localfile.txt', 'tim@server.example.com:/tmp/upload.txt']
    )
    assert len(targets) == 1
    user, host, path = targets[0]
    assert user == 'tim'
    assert host == 'server.example.com'


def test_parse_scp_local_only():
    """scp file1 file2 (no remote target)."""
    targets = allow_ssh.parse_scp_rsync_targets(
        ['/local/file1.txt', '/local/file2.txt']
    )
    assert len(targets) == 0


def test_parse_rsync_remote():
    """rsync file user@host:/tmp/path."""
    targets = allow_ssh.parse_scp_rsync_targets(
        ['-avz', 'localdir/', 'tim@server.example.com:/tmp/backup/']
    )
    assert len(targets) == 1
    user, host, path = targets[0]
    assert user == 'tim'
    assert host == 'server.example.com'
    assert path == '/tmp/backup/'


def test_is_tmp_path():
    """Test tmp path detection."""
    assert allow_ssh.is_tmp_path('/tmp/foo') is True
    assert allow_ssh.is_tmp_path('/tmp') is True
    assert allow_ssh.is_tmp_path('tmp/foo') is True
    assert allow_ssh.is_tmp_path('tmp') is True
    assert allow_ssh.is_tmp_path('/var/tmp/foo') is True
    assert allow_ssh.is_tmp_path('/var/tmp') is True

    assert allow_ssh.is_tmp_path('') is False
    assert allow_ssh.is_tmp_path('/etc/config') is False
    assert allow_ssh.is_tmp_path('/home/user') is False
    assert allow_ssh.is_tmp_path('/tmpfoo') is False  # not /tmp/
    assert allow_ssh.is_tmp_path('tmpfoo') is False  # not tmp/


def test_check_command_ssh_allowed():
    """ssh to configured host should be allowed."""
    assert allow_ssh.check_command(
        'ssh tim@server.example.com ls -la', TEST_CONFIG
    ) is True


def test_check_command_ssh_sudo_allowed():
    """ssh sudo to host with sudo: true."""
    assert allow_ssh.check_command(
        'ssh tim@server.example.com sudo systemctl restart nginx', TEST_CONFIG
    ) is True


def test_check_command_ssh_sudo_denied():
    """ssh sudo to host with sudo: false."""
    assert allow_ssh.check_command(
        'ssh root@workstation.local sudo reboot', TEST_CONFIG
    ) is False


def test_check_command_ssh_wrong_user():
    """ssh with wrong user."""
    assert allow_ssh.check_command(
        'ssh root@server.example.com ls', TEST_CONFIG
    ) is False


def test_check_command_ssh_unknown_host():
    """ssh to host not in config."""
    assert allow_ssh.check_command(
        'ssh tim@unknown.host.com ls', TEST_CONFIG
    ) is False


def test_check_command_ssh_any_user():
    """ssh to host with no user restriction."""
    assert allow_ssh.check_command(
        'ssh anyone@anyuser.example.com ls', TEST_CONFIG
    ) is True
    assert allow_ssh.check_command(
        'ssh root@anyuser.example.com ls', TEST_CONFIG
    ) is True


def test_check_command_ssh_any_user_no_sudo():
    """ssh sudo to host with no user restriction but no sudo."""
    assert allow_ssh.check_command(
        'ssh tim@anyuser.example.com sudo reboot', TEST_CONFIG
    ) is False


def test_check_command_ssh_with_flags():
    """ssh with flags before host."""
    assert allow_ssh.check_command(
        'ssh -t -o StrictHostKeyChecking=accept-new tim@server.example.com sudo systemctl status nginx',
        TEST_CONFIG,
    ) is True


def test_check_command_ssh_l_syntax():
    """ssh -l user host command."""
    assert allow_ssh.check_command(
        'ssh -l tim server.example.com ls', TEST_CONFIG
    ) is True


def test_check_command_scp_tmp_allowed():
    """scp to /tmp/ on configured host."""
    assert allow_ssh.check_command(
        'scp localfile.txt tim@server.example.com:/tmp/upload.txt', TEST_CONFIG
    ) is True


def test_check_command_scp_tmp_relative_allowed():
    """scp to tmp/ (relative) on configured host."""
    assert allow_ssh.check_command(
        'scp localfile.txt tim@server.example.com:tmp/upload.txt', TEST_CONFIG
    ) is True


def test_check_command_scp_non_tmp_denied():
    """scp to non-tmp path."""
    assert allow_ssh.check_command(
        'scp localfile.txt tim@server.example.com:/etc/config', TEST_CONFIG
    ) is False


def test_check_command_scp_unknown_host():
    """scp to unknown host."""
    assert allow_ssh.check_command(
        'scp localfile.txt tim@unknown.host.com:/tmp/file', TEST_CONFIG
    ) is False


def test_check_command_rsync_tmp_allowed():
    """rsync to /tmp/ on configured host."""
    assert allow_ssh.check_command(
        'rsync -avz localdir/ tim@server.example.com:/tmp/backup/', TEST_CONFIG
    ) is True


def test_check_command_rsync_non_tmp_denied():
    """rsync to non-tmp path."""
    assert allow_ssh.check_command(
        'rsync -avz localdir/ tim@server.example.com:/var/www/', TEST_CONFIG
    ) is False


def test_check_command_not_ssh():
    """Non-SSH command should not be auto-allowed."""
    assert allow_ssh.check_command('ls -la', TEST_CONFIG) is False
    assert allow_ssh.check_command('git status', TEST_CONFIG) is False


def test_check_command_ssh_keygen():
    """ssh-keygen is not an SSH connection — should not match."""
    assert allow_ssh.check_command('ssh-keygen -t ed25519', TEST_CONFIG) is False


def test_check_command_ssh_keyscan():
    """ssh-keyscan is not an SSH connection — should not match."""
    assert allow_ssh.check_command(
        'ssh-keyscan server.example.com', TEST_CONFIG
    ) is False


def test_check_command_piped():
    """ssh piped with local command."""
    assert allow_ssh.check_command(
        'ssh tim@server.example.com cat /etc/hostname | grep server', TEST_CONFIG
    ) is True


def test_check_command_chained():
    """ssh chained with &&."""
    assert allow_ssh.check_command(
        'ssh tim@server.example.com uptime && echo done', TEST_CONFIG
    ) is True


def test_check_command_chained_mixed_hosts():
    """ssh to allowed host && ssh to unknown host."""
    assert allow_ssh.check_command(
        'ssh tim@server.example.com ls && ssh tim@unknown.host.com ls',
        TEST_CONFIG,
    ) is False


def test_check_command_empty():
    """Empty command."""
    assert allow_ssh.check_command('', TEST_CONFIG) is False


def test_check_command_sudo_ssh():
    """sudo ssh user@host cmd — sudo wrapping ssh."""
    assert allow_ssh.check_command(
        'sudo ssh tim@server.example.com ls', TEST_CONFIG
    ) is True


def test_check_command_scp_home_dir():
    """scp to home directory (host:) should NOT be allowed."""
    assert allow_ssh.check_command(
        'scp localfile.txt tim@server.example.com:', TEST_CONFIG
    ) is False


def test_find_allowed_host_basic():
    """Basic host lookup."""
    entry = allow_ssh.find_allowed_host(
        TEST_CONFIG, 'server.example.com', 'tim'
    )
    assert entry is not None
    assert entry['host'] == 'server.example.com'


def test_find_allowed_host_wrong_user():
    """Wrong user for host with user restriction."""
    entry = allow_ssh.find_allowed_host(
        TEST_CONFIG, 'server.example.com', 'root'
    )
    assert entry is None


def test_find_allowed_host_no_user_restriction():
    """Host with no user restriction should match any user."""
    entry = allow_ssh.find_allowed_host(
        TEST_CONFIG, 'anyuser.example.com', 'anyone'
    )
    assert entry is not None


def test_find_allowed_host_no_user_restriction_none():
    """Host with no user restriction should match None user."""
    entry = allow_ssh.find_allowed_host(
        TEST_CONFIG, 'anyuser.example.com', None
    )
    assert entry is not None


def test_find_allowed_host_not_found():
    """Unknown host."""
    entry = allow_ssh.find_allowed_host(
        TEST_CONFIG, 'unknown.host.com', 'tim'
    )
    assert entry is None


def test_strip_privilege_prefixes():
    """Test stripping sudo and env prefixes."""
    assert allow_ssh.strip_privilege_prefixes(['sudo', 'ls']) == ['ls']
    assert allow_ssh.strip_privilege_prefixes(['sudo', '-u', 'root', 'ls']) == ['ls']
    assert allow_ssh.strip_privilege_prefixes(['env', 'FOO=bar', 'ls']) == ['ls']
    assert allow_ssh.strip_privilege_prefixes(['ls']) == ['ls']
    assert allow_ssh.strip_privilege_prefixes([]) == []


def test_load_config_missing_file(monkeypatch):
    """Missing config file returns []."""
    monkeypatch.setattr(allow_ssh, 'CONFIG_PATH', '/nonexistent/path.json')
    assert allow_ssh.load_config() == []


def test_end_to_end_allow(monkeypatch, capsys):
    """Full end-to-end test: allowed command."""
    monkeypatch.setattr(allow_ssh, 'load_config', lambda: TEST_CONFIG)
    monkeypatch.setattr(
        'sys.stdin',
        __import__('io').StringIO(json.dumps({
            'tool_name': 'Bash',
            'tool_input': {'command': 'ssh tim@server.example.com ls'},
        })),
    )
    allow_ssh.main()
    output = json.loads(capsys.readouterr().out)
    assert output['hookSpecificOutput']['permissionDecision'] == 'allow'


def test_end_to_end_pass(monkeypatch, capsys):
    """Full end-to-end test: unknown host passes through."""
    monkeypatch.setattr(allow_ssh, 'load_config', lambda: TEST_CONFIG)
    monkeypatch.setattr(
        'sys.stdin',
        __import__('io').StringIO(json.dumps({
            'tool_name': 'Bash',
            'tool_input': {'command': 'ssh tim@unknown.host.com ls'},
        })),
    )
    allow_ssh.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


def test_end_to_end_non_bash(monkeypatch, capsys):
    """Non-Bash tool passes through."""
    monkeypatch.setattr(allow_ssh, 'load_config', lambda: TEST_CONFIG)
    monkeypatch.setattr(
        'sys.stdin',
        __import__('io').StringIO(json.dumps({
            'tool_name': 'Write',
            'tool_input': {'file_path': '/tmp/test'},
        })),
    )
    allow_ssh.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


def test_end_to_end_no_config(monkeypatch, capsys):
    """No config file passes through."""
    monkeypatch.setattr(allow_ssh, 'load_config', lambda: [])
    monkeypatch.setattr(
        'sys.stdin',
        __import__('io').StringIO(json.dumps({
            'tool_name': 'Bash',
            'tool_input': {'command': 'ssh tim@server.example.com ls'},
        })),
    )
    allow_ssh.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


def test_end_to_end_bad_json(monkeypatch, capsys):
    """Bad JSON input passes through."""
    monkeypatch.setattr('sys.stdin', __import__('io').StringIO('not json'))
    allow_ssh.main()
    output = json.loads(capsys.readouterr().out)
    assert output == {}


if __name__ == '__main__':
    # Simple test runner for quick verification without pytest
    test_funcs = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    # Skip tests that need pytest fixtures
    needs_fixtures = {'test_load_config_missing_file', 'test_end_to_end_allow',
                      'test_end_to_end_pass', 'test_end_to_end_non_bash',
                      'test_end_to_end_no_config', 'test_end_to_end_bad_json'}

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
