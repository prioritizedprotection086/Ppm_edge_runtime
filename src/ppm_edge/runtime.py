"""
PPM Edge Runtime

Deterministic local regulation loop for resource-constrained systems.

The runtime deliberately operates on derived values rather than requiring
raw biometric data. It maintains bounded state and produces a decision
that can be consumed by an actuator, device policy, or edge-AI system.
"""

from dataclasses import dataclass
from enum import IntEnum


class Priority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class InputSample:
    value: int
    threshold: int
    priority: Priority = Priority.NORMAL
    confidence: int = 100


@dataclass(frozen=True)
class Decision:
    value: int
    delta: int
    protected: bool
    confidence: int
    priority: Priority


@dataclass
class RuntimeState:
    last_value: int = 0
    initialized: bool = False
    protected: bool = False
    confidence: int = 0
    priority: Priority = Priority.NORMAL


class PPMRuntime:
    """
    Small deterministic PPM decision engine.

    No network access.
    No persistence.
    No dynamic policy lookup.
    No dependency on an AI model.

    The caller supplies the signal-derived value and policy threshold.
    """

    __slots__ = ("state",)

    def __init__(self, initial_value: int = 0) -> None:
        self.state = RuntimeState(
            last_value=initial_value,
            initialized=False,
        )

    def reset(self, value: int = 0) -> None:
        self.state.last_value = value
        self.state.initialized = False
        self.state.protected = False
        self.state.confidence = 0
        self.state.priority = Priority.NORMAL

    def process(self, sample: InputSample) -> Decision:
        value = int(sample.value)
        threshold = max(0, int(sample.threshold))

        if not self.state.initialized:
            delta = 0
            self.state.initialized = True
        else:
            delta = abs(value - self.state.last_value)

        protected = (
            delta >= threshold
            or sample.priority == Priority.CRITICAL
        )

        confidence = max(
            0,
            min(100, int(sample.confidence))
        )

        self.state.last_value = value
        self.state.protected = protected
        self.state.confidence = confidence
        self.state.priority = sample.priority

        return Decision(
            value=value,
            delta=delta,
            protected=protected,
            confidence=confidence,
            priority=sample.priority,
        )
