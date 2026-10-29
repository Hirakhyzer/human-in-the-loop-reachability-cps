import pytest

from hitl_reachability_cps.backward import RobustControlAction, compute_backward_recoverable_sets
from hitl_reachability_cps.model import StateInterval


def _assert_interval(interval: StateInterval | None, lower: float, upper: float) -> None:
    assert interval is not None
    assert interval.lower == pytest.approx(lower)
    assert interval.upper == pytest.approx(upper)


def test_backward_sets_shrink_under_uncertain_control_and_disturbance():
    result = compute_backward_recoverable_sets(
        target=StateInterval(0.0, 1.0),
        safe_set=StateInterval(-2.0, 2.0),
        action=RobustControlAction("hold", -0.1, 0.1),
        disturbance=StateInterval(-0.05, 0.05),
        horizon_steps=2,
    )

    _assert_interval(result.predecessor_sets[0], 0.0, 1.0)
    _assert_interval(result.predecessor_sets[1], 0.15, 0.85)
    _assert_interval(result.predecessor_sets[2], 0.3, 0.7)
    assert result.recoverable_in(StateInterval(0.4, 0.6), 2)
    assert not result.recoverable_in(StateInterval(0.2, 0.6), 2)


def test_backward_sets_are_clipped_to_safe_region():
    result = compute_backward_recoverable_sets(
        target=StateInterval(0.0, 0.5),
        safe_set=StateInterval(0.0, 1.0),
        action=RobustControlAction("decrease", -0.4, -0.4),
        disturbance=StateInterval(0.0, 0.0),
        horizon_steps=2,
    )

    _assert_interval(result.predecessor_sets[1], 0.4, 0.9)
    _assert_interval(result.predecessor_sets[2], 0.8, 1.0)


def test_empty_predecessor_propagates():
    result = compute_backward_recoverable_sets(
        target=StateInterval(0.0, 0.1),
        safe_set=StateInterval(0.0, 1.0),
        action=RobustControlAction("increase", 2.0, 2.0),
        disturbance=StateInterval(0.0, 0.0),
        horizon_steps=2,
    )

    assert result.predecessor_sets[1] is None
    assert result.predecessor_sets[2] is None


def test_horizon_requires_non_negative_integer():
    with pytest.raises(ValueError):
        compute_backward_recoverable_sets(
            StateInterval(0.0, 1.0),
            StateInterval(-1.0, 1.0),
            RobustControlAction("hold", 0.0, 0.0),
            StateInterval(0.0, 0.0),
            horizon_steps=True,
        )
