from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateInterval:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("lower must not exceed upper")

    @property
    def width(self) -> float:
        return self.upper - self.lower

    def shifted(self, delta_lower: float, delta_upper: float) -> "StateInterval":
        return StateInterval(self.lower + delta_lower, self.upper + delta_upper)

    def intersects(self, other: "StateInterval") -> bool:
        return self.lower <= other.upper and other.lower <= self.upper


@dataclass(frozen=True)
class LinearIntervalDynamics:
    """One-dimensional interval dynamics used for transparent reachability studies."""

    drift_lower: float
    drift_upper: float

    def __post_init__(self) -> None:
        if self.drift_lower > self.drift_upper:
            raise ValueError("drift_lower must not exceed drift_upper")


@dataclass(frozen=True)
class HumanResponseModel:
    nominal_latency_s: float
    workload: float = 0.0
    fatigue: float = 0.0

    def __post_init__(self) -> None:
        if self.nominal_latency_s < 0:
            raise ValueError("nominal_latency_s must be non-negative")
        if not 0.0 <= self.workload <= 1.0:
            raise ValueError("workload must be within [0, 1]")
        if not 0.0 <= self.fatigue <= 1.0:
            raise ValueError("fatigue must be within [0, 1]")

    @property
    def effective_latency_s(self) -> float:
        return self.nominal_latency_s * (1.0 + 0.5 * self.workload + 0.5 * self.fatigue)


@dataclass(frozen=True)
class ReachabilityConfig:
    step_duration_s: float = 1.0
    horizon_steps: int = 30

    def __post_init__(self) -> None:
        if self.step_duration_s <= 0:
            raise ValueError("step_duration_s must be positive")
        if self.horizon_steps < 1:
            raise ValueError("horizon_steps must be positive")
