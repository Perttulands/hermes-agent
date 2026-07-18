"""Targeted stale-child cancellation regression tests."""

from concurrent.futures import Future
import threading
import time
from unittest.mock import MagicMock

import pytest

from tools.delegate_tool import _StaleChildError, _wait_for_child_result


def test_unbounded_wait_exits_when_only_this_child_is_marked_stale():
    future = Future()
    stale = threading.Event()
    timer = threading.Timer(0.05, stale.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(_StaleChildError):
            _wait_for_child_result(future, hard_timeout=None, stale_event=stale, poll_interval=0.01)
    finally:
        timer.cancel()

    assert time.monotonic() - started < 0.5
    assert not future.cancelled()  # the daemon child may unwind after interrupt


def test_unbounded_wait_returns_healthy_child_result():
    future = Future()
    future.set_result({"final_response": "done"})

    result = _wait_for_child_result(
        future,
        hard_timeout=None,
        stale_event=threading.Event(),
        poll_interval=0.01,
    )

    assert result == {"final_response": "done"}


def test_stale_heartbeat_cancels_child_not_parent(monkeypatch):
    from tests.tools.test_delegate_subagent_timeout_diagnostic import _StubChild
    from tools import delegate_tool

    monkeypatch.setattr(delegate_tool, "_HEARTBEAT_INTERVAL", 0.01)
    monkeypatch.setattr(delegate_tool, "_HEARTBEAT_STALE_CYCLES_IDLE", 2)
    monkeypatch.setattr(delegate_tool, "_get_child_timeout", lambda: None)

    child = _StubChild(hang_seconds=10.0)
    parent = MagicMock()
    parent._current_task_id = None

    result = delegate_tool._run_single_child(
        task_index=0,
        goal="targeted stale cancellation",
        child=child,
        parent_agent=parent,
    )

    assert result["status"] == "stale"
    assert result["exit_reason"] == "stale"
    assert "healthy sibling" in result["error"]
    parent.interrupt.assert_not_called()
