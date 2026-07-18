"""Authority-ordering regression tests for in-place compression."""

from agent.context_compressor import (
    COMPRESSED_SUMMARY_METADATA_KEY,
    SUMMARY_PREFIX,
    _SUMMARY_END_MARKER,
)
from agent.conversation_compression import _attach_todo_snapshot_to_summary


def test_todo_snapshot_is_reference_inside_summary_not_newest_user_message():
    messages = [
        {
            "role": "user",
            "content": f"{SUMMARY_PREFIX}\n## Active Task\nPrior state.\n\n{_SUMMARY_END_MARKER}",
            COMPRESSED_SUMMARY_METADATA_KEY: True,
        },
        {"role": "assistant", "content": "Ready."},
        {"role": "user", "content": "LATEST REAL USER INSTRUCTION"},
    ]
    original_length = len(messages)

    attached = _attach_todo_snapshot_to_summary(messages, "- [>] finish the repair")

    assert attached is True
    assert len(messages) == original_length
    assert messages[-1]["content"] == "LATEST REAL USER INSTRUCTION"
    summary = messages[0]["content"]
    assert "finish the repair" in summary
    assert "reference only" in summary.lower()
    assert summary.index("finish the repair") < summary.index(_SUMMARY_END_MARKER)
