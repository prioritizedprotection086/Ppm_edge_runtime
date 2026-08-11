"""PPM Edge Runtime reference implementation.

The Python implementation mirrors the deterministic C kernel semantics so it
can be used for development, testing, simulation, and integration work.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


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


@dataclass(frozen=True)
class Decision:
    value: int
    delta: int
    protected: bool
    confidence: int
    priority: Priority


@dataclass
class RuntimeState:
    baseline: int = 0
    last_value: int = 0
    initialized: bool = False
    protected: bool = False
    confidence: int = 0
    priority: Priority = Priority.NORMAL


class PPMRuntime:
    """Small deterministic local PPM decision engine.

    No network access, persistence, model dependency, or dynamic policy lookup.
    The caller supplies a derived signal, threshold, and priority.
    """

    __slots__ = ("state",)

    def __init__(self, initial_value: int = 0) -> None:
        initial_value = int(initial_value)

        self.state = RuntimeState(
            baseline=initial_value,
            last_value=initial_value,
            initialized=False,
        )

    def reset(self, value: Optional[int] = None) -> None:
        """Reset runtime state to the supplied value or the baseline."""

        reset_value = (
            self.state.baseline
            if value is None
            else int(value)
        )

        self.state.last_value = reset_value
        self.state.initialized = False
        self.state.protected = False
        self.state.confidence = 0
        self.state.priority = Priority.NORMAL

    def process(self, sample: InputSample) -> Decision:
        """Process one derived sample using deterministic kernel semantics."""

        value = int(sample.value)
        threshold = max(0, int(sample.threshold))

        delta = abs(value - self.state.last_value)

        self.state.initialized = True

        protected = (
            delta >= threshold
            or sample.priority == Priority.CRITICAL
        )

        if delta == 0:
            confidence = 100
        elif delta < threshold:
            confidence = 75
        else:
            confidence = 50

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
