import pytest

from hitl_reachability_cps import (
    HumanResponseModel,
    LinearIntervalDynamics,
    ReachabilityConfig,
    RecoveryAction,
    StateInterval,
    analyze_human_recoverability,
    propagate_reachable_set,
)


def _trace():
    config = ReachabilityConfig(step_duration_s=1.0, horizon_steps=6)
    trace = propagate_reachable_set(
        StateInterval(0.0, 0.1),
        LinearIntervalDynamics(0.1, 0.2),
        StateInterval(0.8, 2.0),
        config=config,
    )
    return config, trace


def test_fast_human_can_recover_before_unsafe_entry():
    config, trace = _trace()
    result = analyze_human_recoverability(
        trace,
        StateInterval(0.8, 2.0),
        HumanResponseModel(nominal_latency_s=2.0),
        (RecoveryAction("reduce-load", -0.4, -0.3),),
        config=config,
    )
    assert result.human_arrival_step == 2
    assert result.recoverable
    assert result.recovery_action == "reduce-load"
    assert result.first_unsafe_step == 4
    assert result.latest_safe_request_step == 2
    assert result.latest_safe_request_time_s == pytest.approx(2.0)
    assert result.status == "recoverable"


def test_burdened_human_arrives_too_late():
    config, trace = _trace()
    result = analyze_human_recoverability(
        trace,
        StateInterval(0.8, 2.0),
        HumanResponseModel(nominal_latency_s=2.0, workload=1.0, fatigue=1.0),
        (RecoveryAction("reduce-load", -0.4, -0.3),),
        config=config,
    )
    assert result.human_arrival_step == 4
    assert not result.recoverable
    assert result.status == "human-arrives-after-unsafe-entry"


def test_safe_arrival_can_still_lack_certified_recovery():
    config, trace = _trace()
    result = analyze_human_recoverability(
        trace,
        StateInterval(0.8, 2.0),
        HumanResponseModel(nominal_latency_s=2.0),
        (RecoveryAction("weak-action", 0.3, 0.4),),
        config=config,
    )
    assert not result.recoverable
    assert result.status == "safe-at-arrival-but-no-certified-recovery"


def test_arrival_beyond_horizon_is_not_clamped_to_final_trace_step():
    config, trace = _trace()
    result = analyze_human_recoverability(
        trace,
        StateInterval(0.8, 2.0),
        HumanResponseModel(nominal_latency_s=10.0),
        (RecoveryAction("reduce-load", -0.4, -0.3),),
        config=config,
    )

    assert result.human_arrival_step == 10
    assert result.human_arrival_time_s == pytest.approx(10.0)
    assert not result.recoverable
    assert result.recovered_interval is None
    assert result.status == "human-arrival-outside-analysis-horizon"


def test_no_latest_safe_request_exists_when_latency_exceeds_unsafe_deadline():
    config, trace = _trace()
    result = analyze_human_recoverability(
        trace,
        StateInterval(0.8, 2.0),
        HumanResponseModel(nominal_latency_s=5.0),
        (RecoveryAction("reduce-load", -0.4, -0.3),),
        config=config,
    )

    assert result.first_unsafe_step == 4
    assert result.latest_safe_request_step is None
    assert result.latest_safe_request_time_s is None
    assert result.intervention_slack_s < 0.0


def test_trace_timing_must_match_reachability_config():
    config, trace = _trace()
    mismatched_config = ReachabilityConfig(step_duration_s=0.5, horizon_steps=6)

    with pytest.raises(ValueError, match="trace timing"):
        analyze_human_recoverability(
            trace,
            StateInterval(0.8, 2.0),
            HumanResponseModel(nominal_latency_s=2.0),
            (RecoveryAction("reduce-load", -0.4, -0.3),),
            config=mismatched_config,
        )


def test_recovery_action_rejects_nonfinite_bounds():
    with pytest.raises(ValueError, match="finite"):
        RecoveryAction("bad", float("nan"), 0.0)
