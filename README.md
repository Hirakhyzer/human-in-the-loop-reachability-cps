# Human-in-the-Loop Reachability CPS

Reachability-based analysis of **human intervention timing, recoverability, and safety** in cyber-physical systems.

This project studies a question that ordinary human-in-the-loop controllers often leave implicit:

> If a human operator responds after a realistic delay, does a safe recovery trajectory still exist?

The framework combines conservative forward reachability, an unsafe-state set, an operator response model, and candidate recovery actions. It reports whether the human can still recover the system, when the reachable set first becomes unsafe, and the latest time at which intervention can safely be requested.

## Research pipeline

```text
Current CPS state interval
        ↓
Forward reachable-set propagation
        ↓
Unsafe-set intersection prediction
        ↓
Human response latency model
        ↓
Reachable state at human arrival
        ↓
Certified recovery-action search
        ↓
Latest safe intervention window
```

## Core concepts

- **Reachable set** — conservative interval of states the CPS can occupy after each time step.
- **Unsafe set** — region representing unacceptable physical states.
- **Human arrival time** — operator latency adjusted by workload and fatigue, rounded up to the configured discrete-time step for conservative analysis.
- **Recoverability** — whether the entire reachable interval at human arrival can be moved outside the unsafe set by a candidate recovery action.
- **Latest safe request time** — latest intervention-request point that still leaves enough time for the operator to respond before unsafe entry. If even a request at time zero cannot beat the first predicted unsafe step, no latest-safe request exists and the result reports `None` rather than incorrectly returning time zero.
- **Intervention slack** — time remaining between effective operator response and first predicted unsafe entry. Negative slack means the modeled operator response is already slower than the predicted safety deadline.

### Analysis-horizon semantics

Recoverability is only certified within the supplied finite reachability trace. If the conservative operator-arrival step lies beyond the analyzed horizon, the analyzer returns `human-arrival-outside-analysis-horizon` and does **not** clamp the human to the final simulated step. In that case `recoverable=False` means *not certified by the available horizon*, not proof that recovery is impossible after the horizon.

The trace timing must also match the supplied `ReachabilityConfig`; mismatched step durations are rejected so operator latency cannot accidentally be interpreted against a different time grid.

## Example

```python
from hitl_reachability_cps import (
    HumanResponseModel,
    LinearIntervalDynamics,
    ReachabilityConfig,
    RecoveryAction,
    StateInterval,
    analyze_human_recoverability,
    propagate_reachable_set,
)

config = ReachabilityConfig(step_duration_s=1.0, horizon_steps=10)
unsafe = StateInterval(0.8, 2.0)

trace = propagate_reachable_set(
    StateInterval(0.0, 0.1),
    LinearIntervalDynamics(0.1, 0.2),
    unsafe,
    config=config,
)

result = analyze_human_recoverability(
    trace,
    unsafe,
    HumanResponseModel(nominal_latency_s=2.0, workload=0.2, fatigue=0.1),
    (RecoveryAction("reduce-load", -0.4, -0.3),),
    config=config,
)

print(result.status)
print(result.latest_safe_request_time_s)
```

## Why this is different from simple intervention timing

A timing-only policy can say that the operator should be contacted before a deadline. This project additionally evaluates the **reachable state when the operator actually arrives** and asks whether a complete interval can still be returned to safety.

That distinction separates:

1. **warning time** — danger is predicted,
2. **response time** — the human can still arrive before danger,
3. **recoverability** — the human still has an action that certifiably returns the reachable state to safety.

## Initial scope

Version 0.1 uses transparent one-dimensional interval dynamics so the semantics are easy to inspect and test. The architecture is intended to grow toward multidimensional linear systems, bounded disturbances, backward-reachable recovery sets, control-invariant safe sets, and runtime-assurance integration.

The current interval implementation also validates that lower/upper effect bounds are ordered and finite. This prevents a wide state interval from masking semantically invalid reversed action or disturbance bounds.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## License

MIT
