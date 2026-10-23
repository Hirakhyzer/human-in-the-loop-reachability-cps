from hitl_reachability_cps import (
    LinearIntervalDynamics,
    ReachabilityConfig,
    StateInterval,
    first_unsafe_step,
    propagate_reachable_set,
)


def test_reachable_interval_propagates_conservatively():
    trace = propagate_reachable_set(
        StateInterval(0.0, 0.1),
        LinearIntervalDynamics(0.1, 0.2),
        StateInterval(0.8, 2.0),
        config=ReachabilityConfig(step_duration_s=1.0, horizon_steps=5),
    )
    assert trace[0].interval == StateInterval(0.0, 0.1)
    assert trace[3].interval == StateInterval(0.3, 0.7)
    assert not trace[3].unsafe
    assert trace[4].unsafe


def test_first_unsafe_step_returns_none_when_horizon_is_safe():
    trace = propagate_reachable_set(
        StateInterval(0.0, 0.1),
        LinearIntervalDynamics(0.01, 0.02),
        StateInterval(1.0, 2.0),
        config=ReachabilityConfig(horizon_steps=3),
    )
    assert first_unsafe_step(trace) is None
