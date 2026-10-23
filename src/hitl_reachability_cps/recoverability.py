from __future__ import annotations

from dataclasses import dataclass
from math import ceil, inf

from .model import HumanResponseModel, ReachabilityConfig, StateInterval
from .reachability import ReachableStep


@dataclass(frozen=True)
class RecoveryAction:
    name: str
    shift_lower: float
    shift_upper: float

    def __post_init__(self) -> None:
        if self.shift_lower > self.shift_upper:
            raise ValueError("shift_lower must not exceed shift_upper")


@dataclass(frozen=True)
class RecoverabilityResult:
    human_arrival_step: int
    human_arrival_time_s: float
    recoverable: bool
    recovery_action: str | None
    recovered_interval: StateInterval | None
    first_unsafe_step: int | None
    latest_safe_request_step: int | None
    latest_safe_request_time_s: float
    intervention_slack_s: float
    status: str


def _is_safe(interval: StateInterval, unsafe_set: StateInterval) -> bool:
    return not interval.intersects(unsafe_set)


def _find_recovery(
    interval: StateInterval,
    unsafe_set: StateInterval,
    recovery_actions: tuple[RecoveryAction, ...],
) -> tuple[RecoveryAction, StateInterval] | None:
    for action in recovery_actions:
        candidate = interval.shifted(action.shift_lower, action.shift_upper)
        if _is_safe(candidate, unsafe_set):
            return action, candidate
    return None


def analyze_human_recoverability(
    trace: tuple[ReachableStep, ...],
    unsafe_set: StateInterval,
    human: HumanResponseModel,
    recovery_actions: tuple[RecoveryAction, ...],
    *,
    config: ReachabilityConfig = ReachabilityConfig(),
) -> RecoverabilityResult:
    """Determine whether a delayed human intervention can still recover the CPS.

    Human response latency is converted to a conservative discrete arrival step.
    A state is considered recoverable only if the reachable interval at arrival is
    still safe and at least one supplied recovery action moves the full interval
    outside the unsafe set.
    """
    if not trace:
        raise ValueError("trace must not be empty")
    if trace[0].step != 0:
        raise ValueError("trace must start at step 0")

    unsafe_steps = [item.step for item in trace if item.unsafe]
    first_unsafe = min(unsafe_steps) if unsafe_steps else None

    latency_steps = int(ceil(human.effective_latency_s / config.step_duration_s))
    arrival_step = min(latency_steps, trace[-1].step)
    arrival = trace[arrival_step]

    recovery = None if arrival.unsafe else _find_recovery(arrival.interval, unsafe_set, recovery_actions)
    recoverable = recovery is not None

    latest_safe_request_step: int | None = None
    latest_safe_request_time_s = inf
    if first_unsafe is not None:
        latest_safe_request_step = max(0, first_unsafe - latency_steps)
        latest_safe_request_time_s = latest_safe_request_step * config.step_duration_s

    intervention_slack = (
        inf
        if first_unsafe is None
        else first_unsafe * config.step_duration_s - human.effective_latency_s
    )

    if arrival.unsafe:
        status = "human-arrives-after-unsafe-entry"
    elif recoverable:
        status = "recoverable"
    elif first_unsafe is None:
        status = "safe-within-horizon-no-recovery-needed"
    else:
        status = "safe-at-arrival-but-no-certified-recovery"

    return RecoverabilityResult(
        human_arrival_step=arrival_step,
        human_arrival_time_s=arrival.time_s,
        recoverable=recoverable,
        recovery_action=recovery[0].name if recovery else None,
        recovered_interval=recovery[1] if recovery else None,
        first_unsafe_step=first_unsafe,
        latest_safe_request_step=latest_safe_request_step,
        latest_safe_request_time_s=latest_safe_request_time_s,
        intervention_slack_s=intervention_slack,
        status=status,
    )
