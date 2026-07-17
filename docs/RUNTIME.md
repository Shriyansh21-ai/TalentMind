# TalentMind — Runtime Platform

The runtime platform (`src/platform/runtime`) is a production-scale, **deterministic** runtime
infrastructure: background jobs, worker pools, task execution, distributed cache, health, load
management, resilience, and observability. It has **no real threads and no wall-clock sleeps** —
time is driven by an injected `Clock`, so behavior is fully reproducible and testable.

It is built by `build_runtime_platform(clock, event_bus)` into a `RuntimePlatform` dataclass with
its own DI container (keys `runtime.*`). Version `__version__ = "6.3.0"`.

```python
from src.platform.bootstrap import build_platform
p = build_platform()
rt = p.runtime            # RuntimePlatform
```

At construction it pre-wires a `HealthAggregator` (checks: platform, workers, queue, cache,
integration, ai_platform, database) and a `BackgroundServiceManager` (cache_cleanup 300s,
telemetry_cleanup 600s, health_polling 30s).

---

## Modules

| Module | Key types | Responsibility |
|---|---|---|
| `jobs/` | `JobManager`, `JobQueue`, `JobScheduler`, `JobRegistry`, `Job`, `JobStatus`, `JobDefinition` | Define, submit, schedule, claim, complete/fail/cancel jobs; priority queue (capacity 10k); dependency graphs. |
| `workers/` | `WorkerPool`, `Worker`, `WorkerStatus` | Register/scale workers, heartbeats, busy/idle, drain, shutdown, health, metrics. |
| `execution/` | `TaskExecutionEngine`, `Task`, `TaskResult`, `ExecutionReport` | Sequential / parallel / batch / chunk / priority / rate-controlled strategies; each task runs through the resilience engine; cooperative cancellation. |
| `cache/` | `CacheManager`, `CacheNamespace`, `TenantCacheNamespace` | Namespaced distributed cache (tenant / session / config / analytics). |
| `performance/` | `LazyLoader`, `ObjectPool`, `CacheWarmer`, `BatchLoader`, `PerformanceProfile` | Performance primitives; `ConnectionPool` / `QueryOptimizer` protocols. |
| `health/` | `HealthAggregator` + check factories | Aggregate component health (`static_check`, `worker_pool_check`, `queue_check`, `cache_check`, `database_check`). |
| `load/` | `ConcurrencyManager`, `Bulkhead`, `RateControl`, `BackpressureController` | Load management and backpressure. |
| `resilience/` | `ResilienceEngine`, `RetryPolicy`, `TimeoutPolicy`, `FallbackPolicy`, `CircuitBreaker` | Retry (with backoff), timeout, fallback, circuit breaking, failure categorization. |
| `resources/` | `ResourceMonitor`, `ApplicationMetrics` | Resource metrics. |
| `services/` | `BackgroundServiceManager` | Recurring maintenance tasks. |
| `events/` | `RuntimeEventPublisher` | Publishes onto the shared `EnterpriseEventBus` (from the integration platform). |
| `observability/` | `RuntimeTelemetry`, `LatencyStats`, `ExecutionCounter` | Logs, latency, execution counters, spans (OpenTelemetry-ready, currently no-op). |

---

## Execution strategies (`execution/`)

`TaskExecutionEngine` supports these strategies, each deterministic:

- **sequential** — one task at a time.
- **parallel** — logical concurrency (no real threads; deterministic interleave).
- **batch / chunk** — fixed-size batching.
- **priority** — highest priority first.
- **rate-controlled** — throttled via the API rate limiter (`api.ratelimit`).

Every task runs through the `ResilienceEngine`, so retries, timeouts, and circuit-breaking apply
uniformly. Cancellation is cooperative via `TaskContext`.

---

## Resilience (`resilience/`)

```python
from src.platform.runtime.resilience.policies import RetryPolicy, CircuitBreaker

# Retry with backoff, then open the circuit after repeated failures.
policy = RetryPolicy(max_attempts=3)   # backoff strategies configurable
```

`ResilienceEngine.execute(...)` composes `RetryPolicy`, `TimeoutPolicy`, `FallbackPolicy`, and a
`CircuitBreaker` (`CircuitState`), classifying failures via `FailureCategory`.

---

## Dependencies

The runtime platform depends on `common`, `container`, `api.ratelimit`, and
`integrations.events.bus` (it publishes runtime events onto the shared enterprise event bus). It
does **not** depend on the hiring business core.

See [`OPERATIONS.md`](OPERATIONS.md) for day-2 operational guidance and health monitoring, and
[`SECURITY.md`](SECURITY.md) for the security platform.
