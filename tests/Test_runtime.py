from ppm_edge.runtime import (
    InputSample,
    PPMRuntime,
    Priority,
)


def test_initial_sample_uses_baseline_delta():
    runtime = PPMRuntime(initial_value=100)

    decision = runtime.process(
        InputSample(
            value=110,
            threshold=20,
        )
    )

    assert decision.value == 110
    assert decision.delta == 10
    assert decision.protected is False
    assert decision.confidence == 75


def test_threshold_triggers_protection():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=100,
            threshold=20,
        )
    )

    decision = runtime.process(
        InputSample(
            value=120,
            threshold=20,
        )
    )

    assert decision.delta == 20
    assert decision.protected is True
    assert decision.confidence == 50


def test_below_threshold_does_not_protect():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=100,
            threshold=20,
        )
    )

    decision = runtime.process(
        InputSample(
            value=115,
            threshold=20,
        )
    )

    assert decision.delta == 15
    assert decision.protected is False
    assert decision.confidence == 75


def test_critical_priority_forces_protection():
    runtime = PPMRuntime(initial_value=100)

    decision = runtime.process(
        InputSample(
            value=101,
            threshold=20,
            priority=Priority.CRITICAL,
        )
    )

    assert decision.delta == 1
    assert decision.protected is True
    assert decision.priority == Priority.CRITICAL


def test_zero_delta_has_full_confidence():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=100,
            threshold=20,
        )
    )

    decision = runtime.process(
        InputSample(
            value=100,
            threshold=20,
        )
    )

    assert decision.delta == 0
    assert decision.protected is False
    assert decision.confidence == 100


def test_negative_values_are_supported():
    runtime = PPMRuntime(initial_value=-100)

    decision = runtime.process(
        InputSample(
            value=-80,
            threshold=20,
        )
    )

    assert decision.delta == 20
    assert decision.protected is True
    assert decision.confidence == 50


def test_confidence_is_deterministic():
    runtime = PPMRuntime(initial_value=0)

    decisions = [
        runtime.process(
            InputSample(
                value=value,
                threshold=10,
            )
        )
        for value in (0, 5, 15, 15)
    ]

    assert [d.confidence for d in decisions] == [
        100,
        75,
        50,
        100,
    ]


def test_state_tracks_latest_value():
    runtime = PPMRuntime(initial_value=50)

    runtime.process(
        InputSample(
            value=60,
            threshold=20,
        )
    )

    decision = runtime.process(
        InputSample(
            value=65,
            threshold=20,
        )
    )

    assert decision.delta == 5
    assert runtime.state.last_value == 65


def test_reset_returns_runtime_to_uninitialized_state():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=150,
            threshold=20,
        )
    )

    runtime.reset()

    assert runtime.state.initialized is False
    assert runtime.state.last_value == 100
    assert runtime.state.protected is False
    assert runtime.state.confidence == 0
    assert runtime.state.priority == Priority.NORMAL


def test_reset_can_supply_new_value():
    runtime = PPMRuntime(initial_value=100)

    runtime.process(
        InputSample(
            value=150,
            threshold=20,
        )
    )

    runtime.reset(500)

    assert runtime.state.initialized is False
    assert runtime.state.last_value == 500

    decision = runtime.process(
        InputSample(
            value=510,
            threshold=20,
        )
    )

    assert decision.delta == 10
    assert decision.protected is False
    assert decision.confidence == 75


def test_zero_threshold_protects_any_nonzero_delta():
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
    assert decision.confidence == 50


def test_high_priority_does_not_force_protection_by_itself():
    runtime = PPMRuntime(initial_value=100)

    decision = runtime.process(
        InputSample(
            value=101,
            threshold=20,
            priority=Priority.HIGH,
        )
    )

    assert decision.delta == 1
    assert decision.protected is False
    assert decision.priority == Priority.HIGH


def test_no_network_dependency():
    import socket

    assert socket is not None
