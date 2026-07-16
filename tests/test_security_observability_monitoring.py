"""Modules 5 & 6 tests — observability and monitoring.

Observability: logs, metrics, spans/traces and correlation. Monitoring: alert
rules across domains, evaluation, severity, notification hooks and resolution.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.security.common.models import Severity
from src.platform.security.monitoring import (
    Comparison,
    MonitorDomain,
    MonitoringService,
)
from src.platform.security.observability import (
    LogLevel,
    MetricType,
    ObservabilityService,
    SpanStatus,
)


# -- observability ----------------------------------------------------------


def test_logs_and_metrics_recorded():
    obs = ObservabilityService(clock=FrozenClock())
    obs.log("hello", level=LogLevel.INFO, source="api")
    obs.record_metric("requests", 1, metric_type=MetricType.COUNTER)
    assert len(obs.logs()) == 1
    assert len(obs.metrics(name="requests")) == 1


def test_span_builds_trace():
    obs = ObservabilityService(clock=FrozenClock())
    trace_id = obs.new_trace_id()
    with obs.span("op", trace_id=trace_id) as span:
        assert span.trace_id == trace_id
    trace = obs.trace(trace_id)
    assert len(trace.spans) == 1
    assert trace.spans[0].status == SpanStatus.OK


def test_span_records_error_status():
    obs = ObservabilityService(clock=FrozenClock())
    trace_id = obs.new_trace_id()
    try:
        with obs.span("op", trace_id=trace_id):
            raise ValueError("boom")
    except ValueError:
        pass
    assert obs.trace(trace_id).spans[0].status == SpanStatus.ERROR


def test_correlation_ties_logs_and_spans():
    obs = ObservabilityService(clock=FrozenClock())
    cid = obs.new_correlation_id()
    tid = obs.new_trace_id()
    obs.log("start", correlation_id=cid, trace_id=tid)
    with obs.span("op", trace_id=tid):
        pass
    correlated = obs.correlate(cid)
    assert len(correlated["logs"]) == 1
    assert len(correlated["spans"]) == 1


# -- monitoring -------------------------------------------------------------


def test_alert_rule_triggers_with_severity():
    svc = MonitoringService(clock=FrozenClock())
    svc.add_rule("t1", "o1", "High CPU", "cpu", domain=MonitorDomain.RUNTIME,
                 comparison=Comparison.GT, threshold=80, severity=Severity.HIGH)
    alerts = svc.evaluate("t1", "o1", {"cpu": 95})
    assert len(alerts) == 1
    assert alerts[0].severity == Severity.HIGH


def test_alert_not_triggered_below_threshold():
    svc = MonitoringService(clock=FrozenClock())
    svc.add_rule("t1", "o1", "High CPU", "cpu", comparison=Comparison.GT, threshold=80)
    assert svc.evaluate("t1", "o1", {"cpu": 50}) == []


def test_notification_hooks_fire():
    svc = MonitoringService(clock=FrozenClock())
    fired = []
    svc.add_notification_hook(lambda a: fired.append(a.name))
    svc.add_rule("t1", "o1", "Disk full", "disk", comparison=Comparison.GTE, threshold=90)
    svc.evaluate("t1", "o1", {"disk": 90})
    assert fired == ["Disk full"]


def test_resolve_clears_active_alert():
    svc = MonitoringService(clock=FrozenClock())
    svc.add_rule("t1", "o1", "High CPU", "cpu", comparison=Comparison.GT, threshold=80)
    alert = svc.evaluate("t1", "o1", {"cpu": 95})[0]
    assert len(svc.active_alerts("t1")) == 1
    svc.resolve("t1", alert.id)
    assert svc.active_alerts("t1") == []
