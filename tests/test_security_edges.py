import pytest
from ppm_edge import PPMRuntime, InputSample, Priority

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1


@pytest.mark.parametrize(
    "a,b,expected_protection",
    [
        (INT32_MIN, INT32_MIN, False),
        (INT32_MIN, INT32_MAX, True),
        (INT32_MAX, INT32_MIN, True),
        (0, 0, False),
    ],
)
def test_int32_extremes_and_transitions(a, b, expected_protection):
    r = PPMRuntime()
    r.configure(threshold=10)

    assert r.process(a) is not None
    assert r.process(b) is not None
    assert r.protection is expected_protection


def test_threshold_minus_one_is_safe():
    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(100)
    assert r.process(109) is not None
    assert r.protection is False


def test_threshold_exactly_triggers():
    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(100)
    assert r.process(110) is not None
    assert r.protection is True


def test_threshold_plus_one_triggers():
    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(100)
    assert r.process(111) is not None
    assert r.protection is True


def test_negative_delta_uses_absolute_difference():
    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(100)
    assert r.process(91) is not None
    assert r.protection is False

    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(100)
    assert r.process(90) is not None
    assert r.protection is True


def test_repeated_processing_updates_state():
    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(0)

    for value in [1, 2, 3, 4, 5]:
        assert r.process(value) is not None

    assert r.last_value == 5


def test_reset_clears_state():
    r = PPMRuntime()
    r.configure(threshold=10)

    r.process(0)
    r.process(100)

    r.reset()

    assert r.initialized is False
    assert r.protection is False


def test_negative_threshold_is_safe():
    r = PPMRuntime()
    r.configure(threshold=-100)

    assert r.threshold >= 0

    assert r.process(0) is not None
    assert r.process(0) is not None


def test_critical_priority_triggers_protection():
    r = PPMRuntime()
    r.configure(threshold=1_000_000)

    r.process(0)

    sample = InputSample(
        value=0,
        threshold=0,
        priority=Priority.CRITICAL,
    )

    assert r.process(sample) is not None
    assert r.protection is True


def test_large_sequence_remains_stable():
    r = PPMRuntime()
    r.configure(threshold=10_000)

    r.process(0)

    for i in range(10_000):
        value = (i * 1_234_567) % (2**31) - 2**30
        assert r.process(value) is not None

    assert isinstance(r.last_value, int)


@pytest.mark.parametrize(
    "a,b",
    [
        (INT32_MAX, INT32_MIN),
        (INT32_MIN, INT32_MAX),
        (INT32_MAX, 0),
        (INT32_MIN, 0),
    ],
)
def test_extreme_transitions_do_not_wrap(a, b):
    r = PPMRuntime()
    r.configure(threshold=1)

    r.process(a)
    result = r.process(b)

    assert result is not None
    assert r.protection is True
