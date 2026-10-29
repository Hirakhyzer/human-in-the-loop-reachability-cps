from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .model import StateInterval


@dataclass(frozen=True)
class RobustControlAction:
    """Bounded control effect applied before an additive disturbance."""

    name: str
    shift_lower: float
    shift_upper: float

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (self.shift_lower, self.shift_upper)):
            raise ValueError("control shifts must be finite")
        if self.shift_lower > self.shift_upper:
            raise ValueError("shift_lower must not exceed shift_upper")


@dataclass(frozen=True)
class BackwardReachabilityResult:
    """Robust predecessor sets for reaching a target while remaining safe."""

    target: StateInterval
    safe_set: StateInterval
    predecessor_sets: tuple[StateInterval | None, ...]

    def recoverable_in(self, interval: StateInterval, steps: int) -> bool:
        if steps < 0 or steps >= len(self.predecessor_sets):
            raise ValueError("steps must index a computed predecessor set")
        predecessor = self.predecessor_sets[steps]
        return predecessor is not None and predecessor.lower <= interval.lower and interval.upper <= predecessor.upper


def _intersection(left: StateInterval, right: StateInterval) -> StateInterval | None:
    lower = max(left.lower, right.lower)
    upper = min(left.upper, right.upper)
    return None if lower > upper else StateInterval(lower, upper)


def _robust_predecessor(
    target: StateInterval,
    action: RobustControlAction,
    disturbance: StateInterval,
) -> StateInterval:
    """States whose full one-step successor interval is contained in target.

    For x+ = x + u + w with u in the action interval and w in the
    disturbance interval, robust containment requires every possible successor
    to remain inside ``target``.
    """
    return StateInterval(
        target.lower - action.shift_lower - disturbance.lower,
        target.upper - action.shift_upper - disturbance.upper,
    )


def compute_backward_recoverable_sets(
    target: StateInterval,
    safe_set: StateInterval,
    action: RobustControlAction,
    disturbance: StateInterval,
    *,
    horizon_steps: int,
) -> BackwardReachabilityResult:
    """Compute conservative robust recoverable sets for a fixed control action.

    Set 0 is the target constrained to the safe set. Each later set contains
    states that can robustly enter the preceding set in one step while the
    current state remains inside ``safe_set``. ``None`` denotes an empty set.
    """
    if not isinstance(horizon_steps, int) or isinstance(horizon_steps, bool) or horizon_steps < 0:
        raise ValueError("horizon_steps must be a non-negative integer")

    current = _intersection(target, safe_set)
    sets: list[StateInterval | None] = [current]
    for _ in range(horizon_steps):
        if current is None:
            sets.append(None)
            continue
        current = _intersection(_robust_predecessor(current, action, disturbance), safe_set)
        sets.append(current)

    return BackwardReachabilityResult(
        target=target,
        safe_set=safe_set,
        predecessor_sets=tuple(sets),
    )
