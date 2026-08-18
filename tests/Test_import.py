from ppm_edge import (
    Decision,
    InputSample,
    PPMRuntime,
    Priority,
    RuntimeState,
)


def test_public_api_imports():
    assert PPMRuntime is not None
    assert InputSample is not None
    assert Decision is not None
    assert RuntimeState is not None
    assert Priority is not None


def test_runtime_can_be_created():
    runtime = PPMRuntime()

    assert runtime.state.initialized is False


def test_runtime_produces_decision():
    runtime = PPMRuntime()

    result = runtime.process(
        InputSample(
            value=100,
            threshold=10,
        )
    )

    assert isinstance(result, Decision)
    assert result.value == 100
