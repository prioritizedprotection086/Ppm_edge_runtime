# tests/test_security_edges.py
import pytest
from ppm_edge import PPMRuntime, InputSample, Priority

INT32_MIN = -2**31
INT32_MAX = 2**31 - 1

@pytest.mark.parametrize("a,b,expected_protection", [
    (INT32_MIN, INT32_MIN, False),          # zero delta
    (INT32_MIN, INT32_MAX, True),           # extreme transition
    (INT32_MAX, INT32_MIN, True),
    (0, 0, False),
])
def test_int32_extremes_zero_and_transitions(a, b, expected_protection):
    r = PPMRuntime()
    r.configure(threshold=10)
    # Note: initial last_value == 0
    res1 = r.process(a)
    assert res1 is not None
    # After first process last_value == a
    res2 = r.process(b)
    assert res2 is not None
    # Protection is evaluated for the second step (delta between a and b)
    assert r.protection is expected_protection


def test_positive_and_negative_deltas_and_threshold_boundaries():
    threshold = 10

    # Case: threshold - 1 (safe)
    r = PPMRuntime()
    r.configure(threshold=threshold)
    r.process(100)                      # set last_value -> 100
    out = r.process(100 + (threshold - 1))  # 109, delta 9 < 10
    assert out is not None
    assert r.protection is False

    # Case: threshold (should trigger protection)
    r = PPMRuntime()
    r.configure(threshold=threshold)
    r.process(100)
    out = r.process(100 + threshold)    # 110, delta 10 == threshold
    assert out is not None
    assert r.protection is True

    # Case: threshold + 1 (should trigger)
    r = PPMRuntime()
    r.configure(threshold=threshold)
    r.process(100)
    out = r.process(100 + threshold + 1)  # 111, delta 11 > threshold
    assert out is not None
    assert r.protection is True


def test_repeated_processing_and_reset_behavior():
    r = PPMRuntime()
    r.configure(threshold=10)
    r.process(0)
    for v in [1, 2, 3, 4, 5]:
        r.process(v)
    assert r.last_value == 5
    r.reset()
    assert r.initialized is False
    assert r.protection is False


def test_critical_priority_overrides_threshold():
    r = PPMRuntime()
    r.configure(threshold=1_000_000)
    r.process(0)
    # critical priority always triggers protection regardless of delta
    sample = InputSample(value=0, threshold=0, priority=Priority.CRITICAL)
    out = r.process(sample)
    assert out is not None
    assert r.protection is True


def test_negative_threshold_clamped():
    r = PPMRuntime()
    r.configure(threshold=-100)
    assert r.threshold >= 0
    # process with integers should return a Decision (current implementation does)
    r.process(0)
    out = r.process(0)
    assert out is not None


def test_large_sequence_stability():
    r = PPMRuntime()
    r.configure(threshold=10000)
    r.process(0)
    for i in range(10000):  # fairly large but reasonable
        v = (i * 1234567) % (2**31) - 2**30
        out = r.process(v)
        assert out is not None
    # state should be consistent
    assert isinstance(r.last_value, int)


def test_delta_signed_behaviour_and_state_integrity():
    r = PPMRuntime()
    r.configure(threshold=100)
    r.process(-100)
    r.process(-95)  # small positive delta -> 5 < 100
    assert r.protection is False
    # make a change that actually reaches the threshold in a single step
    r.process(200)  # delta = abs(200 - (-95)) = 295 >= 100 -> triggers protection
    assert r.protection is True
