from __future__ import annotations

from dataclasses import dataclass
from math import ceil, inf, isclose, isfinite

from .model import HumanResponseModel, ReachabilityConfig, StateInterval
from .reachability import ReachableStep


@dataclass(frozen=True)
class RecoveryAction:
    name: str
    shift_lower: float
    shift_upper: float

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (self.shift_lower, self.shift_upper)):
            raise ValueError("recovery-action shifts must be finite")
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
    latest_safe_request_time_s: float | None
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


def _validate_trace(
    trace: tuple[ReachableStep, ...], config: ReachabilityConfig
) -> None:
    if not trace:
        raise ValueError("trace must not be empty")

    for expected_step, item in enumerate(trace):
        if item.step != expected_step:
            raise ValueError("trace steps must be contiguous and start at step 0")
        expected_time = expected_step * config.step_duration_s
        if not isclose(item.time_s, expected_time, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("trace timing does not match the supplied reachability config")


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

    If the conservative human-arrival step lies beyond the analyzed trace, the
    function reports ``human-arrival-outside-analysis-horizon`` rather than
    clamping the arrival to the final reachable set. In that case recoverability
    is *not certified* by the available horizon.
    """
    _validate_trace(trace, config)

    unsafe_steps = [item.step for item in trace if item.unsafe]
    first_unsafe = min(unsafe_steps) if unsafe_steps else None

    latency_steps = int(ceil(human.effective_latency_s / config.step_duration_s))
    conservative_arrival_time_s = latency_steps * config.step_duration_s

    latest_safe_request_step: int | None = None
    latest_safe_request_time_s: float | None = inf
    if first_unsafe is not None:
        candidate_request_step = first_unsafe - latency_steps
        if candidate_request_step >= 0:
            latest_safe_request_step = candidate_request_step
            latest_safe_request_time_s = (
                candidate_request_step * config.step_duration_s
            )
        else:
            # Even an immediate request cannot make the conservative human
            # arrival precede the first predicted unsafe step.
            latest_safe_request_time_s = None

    intervention_slack = (
        inf
        if first_unsafe is None
        else first_unsafe * config.step_duration_s - human.effective_latency_s
    )

    if latency_steps > trace[-1].step:
        return RecoverabilityResult(
            human_arrival_step=latency_steps,
            human_arrival_time_s=conservative_arrival_time_s,
            recoverable=False,
            recovery_action=None,
            recovered_interval=None,
            first_unsafe_step=first_unsafe,
            latest_safe_request_step=latest_safe_request_step,
            latest_safe_request_time_s=latest_safe_request_time_s,
            intervention_slack_s=intervention_slack,
            status="human-arrival-outside-analysis-horizon",
        )

    arrival = trace[latency_steps]
    recovery = (
        None
        if arrival.unsafe
        else _find_recovery(arrival.interval, unsafe_set, recovery_actions)
    )
    recoverable = recovery is not None

    if arrival.unsafe:
        status = "human-arrives-after-unsafe-entry"
    elif recoverable:
        status = "recoverable"
    elif first_unsafe is None:
        status = "safe-within-horizon-no-recovery-needed"
    else:
        status = "safe-at-arrival-but-no-certified-recovery"

    return RecoverabilityResult(
        human_arrival_step=latency_steps,
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
