"""Regression tests for the compressed-summary metadata flag (#38389).

The compressor marks summary messages with ``COMPRESSED_SUMMARY_METADATA_KEY``
so frontends (CLI, Desktop, gateway, TUI) can distinguish them from real
assistant/user messages without content-prefix heuristics.

Two invariants:
1. The flag is present on exactly the summary-bearing message after compress()
   (standalone insertion AND merge-into-tail).
2. The key is underscore-prefixed so the chat-completions wire sanitizer
   strips it — strict gateways (Fireworks, Mistral, Moonshot/Kimi,
   opencode-go) reject unknown message keys with "Extra inputs are not
   permitted", poisoning the session.
"""
from unittest.mock import MagicMock, patch
from typing import Any

from agent.context_compressor import (
    COMPRESSED_SUMMARY_METADATA_KEY,
    ContextCompressor,
)


def _make_compressor():
    with patch(
        "agent.context_compressor.get_model_context_length", return_value=8000
    ):
        return ContextCompressor(
            model="test-model", quiet_mode=True, config_context_length=8000
        )


def _make_messages(n_turns: int = 30) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = [{"role": "system", "content": "sys"}]
    for i in range(n_turns):
        msgs.append({"role": "user", "content": f"question {i} " + "x" * 400})
        msgs.append({"role": "assistant", "content": f"answer {i} " + "y" * 400})
    return msgs


def _compress(cc, msgs):
    resp = MagicMock()
    resp.choices[0].message.content = "## Active Task\nstuff"
    with patch("agent.context_compressor.call_llm", return_value=resp):
        return cc.compress(msgs, current_tokens=100_000, force=True)


class TestMetadataFlagSet:
    def test_exactly_one_flagged_message_after_compress(self):
        cc = _make_compressor()
        out = _compress(cc, _make_messages())
        flagged = [
            msg for msg in out
            if isinstance(msg, dict) and msg.get(COMPRESSED_SUMMARY_METADATA_KEY)
        ]
        assert len(flagged) == 1
        # The flagged message is the one carrying the compaction handoff.
        assert "[CONTEXT COMPACTION" in flagged[0]["content"]

    def test_helper_detects_flag(self):
        assert ContextCompressor._has_compressed_summary_metadata(
            {COMPRESSED_SUMMARY_METADATA_KEY: True}
        )
        assert not ContextCompressor._has_compressed_summary_metadata(
            {"role": "assistant", "content": "hi"}
        )
        assert not ContextCompressor._has_compressed_summary_metadata("not a dict")
        assert not ContextCompressor._has_compressed_summary_metadata(None)


class TestMetadataFlagNeverReachesWire:
    def test_key_is_underscore_prefixed(self):
        """The wire sanitizers strip every top-level message key starting
        with '_'. A bare key would reach strict gateways (Fireworks etc.)
        and 400 with 'Extra inputs are not permitted'."""
        assert COMPRESSED_SUMMARY_METADATA_KEY.startswith("_")

    def test_chat_completions_transport_strips_flag(self):
        from agent.transports.chat_completions import ChatCompletionsTransport

        cc = _make_compressor()
        out = _compress(cc, _make_messages())
        wire = ChatCompletionsTransport().convert_messages(out, model="some-model")
        assert not any(
            isinstance(msg, dict) and COMPRESSED_SUMMARY_METADATA_KEY in msg
            for msg in wire
        )
        # Sanitization must not destroy the in-process flag on the originals.
        assert any(
            isinstance(msg, dict) and msg.get(COMPRESSED_SUMMARY_METADATA_KEY)
            for msg in out
        )


class TestRepeatedCompactionCanonicalSummary:
    def test_fresh_compressor_replaces_prior_protected_summary(self):
        """A gateway turn creates a fresh compressor and resets protection decay."""
        first = _make_compressor()
        # Produce the dangerous persisted layout: system + summary at index 1.
        first.protect_first_n = 0
        once = _compress(first, _make_messages())
        expanded = list(once)
        expanded.extend(
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"newer {i} " + "z" * 400,
            }
            for i in range(30)
        )

        twice = _compress(_make_compressor(), expanded)

        summaries = [
            msg
            for msg in twice
            if isinstance(msg, dict)
            and (
                msg.get(COMPRESSED_SUMMARY_METADATA_KEY)
                or ContextCompressor._is_context_summary_content(msg.get("content"))
            )
        ]
        assert len(summaries) == 1

    def test_twenty_fresh_compressors_keep_one_summary_and_latest_user(self):
        messages = _make_messages()

        for generation in range(20):
            tool_call_id = f"call-{generation}"
            latest_instruction = f"LATEST HUMAN INSTRUCTION {generation}"
            messages.extend(
                [
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": "probe",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": "ok",
                    },
                    {"role": "user", "content": latest_instruction},
                    {"role": "assistant", "content": "acknowledged"},
                ]
            )

            compressor = _make_compressor()
            compressor.protect_first_n = 0
            compressor.protect_last_n = 6
            messages = _compress(compressor, messages)

            summaries = [
                msg
                for msg in messages
                if isinstance(msg, dict)
                and (
                    msg.get(COMPRESSED_SUMMARY_METADATA_KEY)
                    or ContextCompressor._is_context_summary_content(msg.get("content"))
                )
            ]
            assert len(summaries) == 1, f"generation {generation}"
            assert any(
                msg.get("role") == "user" and msg.get("content") == latest_instruction
                for msg in messages
                if isinstance(msg, dict)
            ), f"generation {generation}"

            call_ids = {
                call.get("id")
                for msg in messages
                if isinstance(msg, dict) and msg.get("role") == "assistant"
                for call in (msg.get("tool_calls") or [])
                if isinstance(call, dict)
            }
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "tool":
                    assert msg.get("tool_call_id") in call_ids, f"generation {generation}"
