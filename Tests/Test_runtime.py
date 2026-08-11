    from ppm_edge import (
    InputSample,
    PPMRuntime,
    Priority,
)


def test_first_sample_has_zero_delta():
    runtime = PPMRuntime()

    decision = runtime.process(
        InputSample(
            value=500,
            threshold=100,
        )
    )

    assert decision.delta == 0
    assert decision.protected is False


def test_small_change_does_not_trigger_protection():
    runtime = PPMRuntime(initial_value=500)

    runtime.process(
        InputSample(
            value=500,
            threshold=100,
        )
    )

    decision = runtime.process(
        InputSample(
            value=520,
            threshold=100,
        )
    )

    assert decision.delta == 20
    assert decision.protected is False


def test_threshold_crossing_triggers_protection():
    runtime = PPMRuntime(initial_value=500)

    runtime.process(
        InputSample(
            value=500,
            threshold=100,
        )
    )

    decision = runtime.process(
        InputSample(
            value=650,
            threshold=100,
        )
    )

    assert decision.delta == 150
    assert decision.protected is True


def test_critical_priority_triggers_protection():
    runtime = PPMRuntime(initial_value=500)

    decision = runtime.process(
        InputSample(
            value=510,
            threshold=100,
            priority=Priority.CRITICAL,
        )
    )

    assert decision.protected is True
    assert decision.priority == Priority.CRITICAL


def test_confidence_is_bounded():
    runtime = PPMRuntime()

    high = runtime.process(
        InputSample(
            value=500,
            threshold=100,
            confidence=999,
        )
    )

    assert high.confidence == 100

    low = runtime.process(
        InputSample(
            value=500,
            threshold=100,
            confidence=-100,
        )
    )

    assert low.confidence == 0


def test_reset_clears_runtime_state():
    runtime = PPMRuntime(initial_value=500)

    runtime.process(
        InputSample(
            value=700,
            threshold=100,
        )
    )

    runtime.reset()

    assert runtime.state.last_value == 0
    assert runtime.state.initialized is False
    assert runtime.state.protected is False
    assert runtime.state.confidence == 0
    assert runtime.state.priority == Priority.NORMAL


def test_negative_signal_values_are_supported():
    runtime = PPMRuntime(initial_value=-100)

    runtime.process(
        InputSample(
            value=-100,
            threshold=50,
        )
    )

    decision = runtime.process(
        InputSample(
            value=-25,
            threshold=50,
        )
    )

    assert decision.delta == 75
    assert decision.protected is True


def test_runtime_does_not_require_network():
    """
    The runtime operates entirely on supplied values.
    No network or external service is required.
    """

    runtime = PPMRuntime()

    decision = runtime.process(
        InputSample(
            value=42,
            threshold=10,
        )
    )

    assert decision.value == 42


def test_priority_is_preserved():
    runtime = PPMRuntime()

    decision = runtime.process(
        InputSample(
            value=100,
            threshold=10,
            priority=Priority.HIGH,
        )
    )

    assert decision.priority == Priority.HIGH


def test_runtime_state_tracks_latest_value():
    runtime = PPMRuntime()

    runtime.process(
        InputSample(
            value=100,
            threshold=10,
        )
    )

    runtime.process(
        InputSample(
            value=125,
            threshold=10,
        )
    )

    assert runtime.state.last_value == 125


def test_zero_threshold_protects_on_any_change():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=100,
            threshold=0,
        )
    )

    decision = runtime.process(
        InputSample(
            value=101,
            threshold=0,
        )
    )

    assert decision.delta == 1
    assert decision.protected is True


def test_exact_threshold_triggers_protection():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=100,
            threshold=50,
        )
    )

    decision = runtime.process(
        InputSample(
            value=150,
            threshold=50,
        )
    )

    assert decision.delta == 50
    assert decision.protected is True

    assert decision.delta == 20
    assert decision.protected is False


def test_threshold_crossing_triggers_protection():
    runtime = PPMRuntime(initial_value=500)

    runtime.process(
        InputSample(
            value=500,
            threshold=100,
        )
    )

    decision = runtime.process(
        InputSample(
            value=650,
            threshold=100,
        )
    )

    assert decision.delta == 150
    assert decision.protected is True


def test_critical_priority_triggers_protection():
    runtime = PPMRuntime(initial_value=500)

    runtime.process(
        InputSample(
            value=510,
            threshold=100,
            priority=Priority.CRITICAL,
        )
    )

    assert decision.protected is True
    assert decision.priority == Priority.CRITICAL


def test_confidence_is_bounded():
    runtime = PPMRuntime()

    high = runtime.process(
        InputSample(
            value=500,
            threshold=100,
            confidence=999,
        )
    )

    assert high.confidence == 100

    low = runtime.process(
        InputSample(
            value=500,
            threshold=100,
            confidence=-100,
        )
    )

    assert low.confidence == 0


def test_reset_clears_runtime_state():
    runtime = PPMRuntime(initial_value=500)

    runtime.process(
        InputSample(
            value=700,
            threshold=100,
        )
    )

    runtime.reset()

    assert runtime.state.last_value == 0
    assert runtime.state.initialized is False
    assert runtime.state.protected is False
    assert runtime.state.confidence == 0
    assert runtime.state.priority == Priority.NORMAL


def test_negative_signal_values_are_supported():
    runtime = PPMRuntime(initial_value=-100)

    runtime.process(
        InputSample(
            value=-100,
            threshold=50,
        )
    )

    decision = runtime.process(
        InputSample(
            value=-25,
            threshold=50,
        )
    )

    assert decision.delta == 75
    assert decision.protected is True


def test_runtime_does_not_require_network():
    """
    Architectural test.

    The runtime API should operate entirely from supplied values.
    No network/service dependency is required.
    """

    runtime = PPMRuntime()

    decision = runtime.process(
        InputSample(
            value=42,
            threshold=10,
        )
    )

    assert decision.value == 42
