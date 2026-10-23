from __future__ import annotations

from dataclasses import dataclass

from .model import LinearIntervalDynamics, ReachabilityConfig, StateInterval


@dataclass(frozen=True)
class ReachableStep:
    step: int
    time_s: float
    interval: StateInterval
    unsafe: bool


def propagate_reachable_set(
    initial: StateInterval,
    dynamics: LinearIntervalDynamics,
    unsafe_set: StateInterval,
    *,
    config: ReachabilityConfig = ReachabilityConfig(),
) -> tuple[ReachableStep, ...]:
    """Propagate a conservative interval reachable set over a finite horizon."""
    steps: list[ReachableStep] = [
        ReachableStep(0, 0.0, initial, initial.intersects(unsafe_set))
    ]
    current = initial
    for step in range(1, config.horizon_steps + 1):
        current = current.shifted(dynamics.drift_lower, dynamics.drift_upper)
        steps.append(
            ReachableStep(
                step=step,
                time_s=step * config.step_duration_s,
                interval=current,
                unsafe=current.intersects(unsafe_set),
            )
        )
    return tuple(steps)


def first_unsafe_step(trace: tuple[ReachableStep, ...]) -> ReachableStep | None:
    for item in trace:
        if item.unsafe:
            return item
    return None
