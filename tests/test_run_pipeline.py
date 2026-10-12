import pytest

import src.run_pipeline as pipeline


def test_pipeline_executes_stages_in_order(monkeypatch):
    events = []

    monkeypatch.setattr(
        pipeline,
        "extract_year",
        lambda year: events.append(("extract", year)),
    )
    monkeypatch.setattr(
        pipeline,
        "validate_year",
        lambda year: events.append(("validate", year)) or [],
    )
    monkeypatch.setattr(
        pipeline,
        "transform_year",
        lambda year: events.append(("transform", year)),
    )
    monkeypatch.setattr(
        pipeline,
        "create_warehouse",
        lambda: events.append(("warehouse",)),
    )
    monkeypatch.setattr(
        pipeline,
        "load_warehouse",
        lambda: events.append(("load",)),
    )
    monkeypatch.setattr(
        pipeline,
        "run_quality_monitor",
        lambda: events.append(("monitor",)) or 0,
    )

    pipeline.run_pipeline(years=[2026])

    assert events == [
        ("extract", 2026),
        ("validate", 2026),
        ("transform", 2026),
        ("warehouse",),
        ("load",),
        ("monitor",),
    ]


def test_pipeline_stops_when_validation_fails(monkeypatch):
    events = []

    monkeypatch.setattr(
        pipeline,
        "extract_year",
        lambda year: events.append(("extract", year)),
    )
    monkeypatch.setattr(
        pipeline,
        "validate_year",
        lambda year: ["Error de prueba"],
    )
    monkeypatch.setattr(
        pipeline,
        "transform_year",
        lambda year: events.append(("transform", year)),
    )

    with pytest.raises(pipeline.PipelineExecutionError):
        pipeline.run_pipeline(years=[2026])

    assert events == [("extract", 2026)]


def test_pipeline_fails_when_monitor_reports_critical_errors(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "extract_year",
        lambda year: None,
    )
    monkeypatch.setattr(
        pipeline,
        "validate_year",
        lambda year: [],
    )
    monkeypatch.setattr(
        pipeline,
        "transform_year",
        lambda year: None,
    )
    monkeypatch.setattr(
        pipeline,
        "create_warehouse",
        lambda: None,
    )
    monkeypatch.setattr(
        pipeline,
        "load_warehouse",
        lambda: None,
    )
    monkeypatch.setattr(
        pipeline,
        "run_quality_monitor",
        lambda: 1,
    )

    with pytest.raises(pipeline.PipelineExecutionError):
        pipeline.run_pipeline(years=[2026])