import pytest

from ppm_edge import PPMRuntime


def make_runtime(threshold=10):
    runtime = PPMRuntime()
    runtime.configure(threshold=threshold)
    return runtime


def test_zero_delta_does_not_trigger_protection():
    runtime = make_runtime(10)

    result = runtime.process(100)

    assert result is not None
    assert runtime.last_value == 100


def test_delta_below_threshold_is_safe():
    runtime = make_runtime(10)

    runtime.process(100)
    result = runtime.process(109)

    assert result is not None
    assert runtime.protection is False


def test_delta_at_threshold_triggers_protection():
    runtime = make_runtime(10)

    runtime.process(100)
    runtime.process(110)

    assert runtime.protection is True


def test_delta_above_threshold_triggers_protection():
    runtime = make_runtime(10)

    runtime.process(100)
    runtime.process(1000)

    assert runtime.protection is True


def test_negative_threshold_is_rejected_or_clamped():
    runtime = PPMRuntime()
    runtime.configure(threshold=-100)

    assert runtime.threshold >= 0


def test_large_positive_values():
    runtime = make_runtime(100)

    runtime.process(2_000_000_000)
    runtime.process(2_000_000_100)

    assert runtime.protection is True


def test_large_negative_values():
    runtime = make_runtime(100)

    runtime.process(-2_000_000_000)
    runtime.process(-1_999_999_900)

    assert runtime.protection is True


def test_repeated_processing_updates_last_value():
    runtime = make_runtime(10)

    runtime.process(100)
    runtime.process(105)
    runtime.process(107)

    assert runtime.last_value == 107


def test_reset_clears_runtime_state():
    runtime = make_runtime(10)

    runtime.process(100)
    runtime.process(1000)

    runtime.reset()

    assert runtime.initialized is False
    assert runtime.protection is False


@pytest.mark.parametrize(
    "old_value,new_value,threshold,expected",
    [
        (0, 5, 10, False),
        (0, 10, 10, True),
        (0, 11, 10, True),
        (100, 90, 10, True),
        (-100, -95, 10, False),
        (-100, -90, 10, True),
    ],
)
def test_threshold_matrix(old_value, new_value, threshold, expected):
    runtime = make_runtime(threshold)

    runtime.process(old_value)
    runtime.process(new_value)

    assert runtime.protection is expected
