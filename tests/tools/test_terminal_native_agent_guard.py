"""Regression tests for the native terminal agent CLI guard."""

import json

import pytest

import tools.terminal_tool as terminal_tool


@pytest.fixture(autouse=True)
def _guard_env(monkeypatch):
    monkeypatch.delenv("TERMINAL_NATIVE_AGENT_CLI_GUARD", raising=False)
    monkeypatch.delenv("HERMES_ALLOW_NATIVE_TERMINAL_AGENT", raising=False)
    terminal_tool._active_environments.clear()
    terminal_tool._last_activity.clear()
    yield
    terminal_tool._active_environments.clear()
    terminal_tool._last_activity.clear()


def test_guard_blocks_codex_before_environment_creation(monkeypatch):
    def _fail_create(*_args, **_kwargs):
        pytest.fail("native terminal agent guard must fire before environment creation")

    monkeypatch.setattr(terminal_tool, "_create_environment", _fail_create)

    result = json.loads(terminal_tool.terminal_tool("codex --doctor"))

    assert result["status"] == "blocked"
    assert result["exit_code"] == -1
    assert "codex" in result["error"]
    assert "tmux-agent-driving" in result["error"]
    assert "HERMES_ALLOW_NATIVE_TERMINAL_AGENT=1" in result["error"]


def test_guard_blocks_wrapped_claude_command():
    message = terminal_tool._native_terminal_agent_guard_message(
        "HOME=/home/perttu claude --resume abc123"
    )

    assert message is not None
    assert "claude" in message
    assert "tmux-agent-driving" in message


def test_guard_catches_bash_lc_inner_agent_command():
    message = terminal_tool._native_terminal_agent_guard_message(
        "bash -lc 'cd /srv/chrote && codex --doctor'"
    )

    assert message is not None
    assert "codex" in message


def test_guard_allows_explicit_command_escape():
    assert terminal_tool._native_terminal_agent_guard_message(
        "HERMES_ALLOW_NATIVE_TERMINAL_AGENT=1 codex --doctor"
    ) is None


def test_guard_can_be_disabled_by_terminal_config_env(monkeypatch):
    monkeypatch.setenv("TERMINAL_NATIVE_AGENT_CLI_GUARD", "false")

    assert terminal_tool._native_terminal_agent_guard_message("codex --doctor") is None


def test_guard_does_not_block_textual_mentions():
    assert terminal_tool._native_terminal_agent_guard_message(
        "grep -R codex /home/perttu/skills"
    ) is None
