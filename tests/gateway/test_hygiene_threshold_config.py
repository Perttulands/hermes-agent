"""Gateway hygiene threshold configuration regression tests."""

import pytest

from gateway.run import _resolve_hygiene_threshold


def test_hygiene_threshold_accepts_explicit_ninety_percent():
    assert _resolve_hygiene_threshold({"hygiene_threshold": 0.90}) == pytest.approx(0.90)


@pytest.mark.parametrize("value", [None, "garbage", 0.49, 0.99, True])
def test_hygiene_threshold_rejects_invalid_or_unsafe_values(value):
    assert _resolve_hygiene_threshold({"hygiene_threshold": value}) == pytest.approx(0.85)
