"""Smoke test: the fourseer package imports cleanly and exposes its public API."""


def test_import_fourseer() -> None:
    """Importing fourseer must succeed and expose a version."""
    import fourseer

    assert hasattr(fourseer, "__version__")
    assert isinstance(fourseer.__version__, str)
    assert fourseer.__version__


def test_public_api_reexports() -> None:
    """Run and load_run are importable from the package root and in __all__."""
    from fourseer import Run, load_run

    assert Run is not None
    assert load_run is not None
    import fourseer

    assert "Run" in fourseer.__all__
    assert "load_run" in fourseer.__all__


def test_public_api_reexports_validation() -> None:
    """ConsistencyIssue and validate_run are importable and in __all__."""
    from fourseer import ConsistencyIssue, validate_run

    assert ConsistencyIssue is not None
    assert validate_run is not None
    import fourseer

    assert "ConsistencyIssue" in fourseer.__all__
    assert "validate_run" in fourseer.__all__


def test_public_api_reexports_report() -> None:
    """CycleMetrics and build_cycle_metrics are importable and in __all__."""
    from fourseer import CycleMetrics, build_cycle_metrics

    assert CycleMetrics is not None
    assert build_cycle_metrics is not None
    import fourseer

    assert "CycleMetrics" in fourseer.__all__
    assert "build_cycle_metrics" in fourseer.__all__


def test_public_api_reexports_report_render() -> None:
    """render_report and extract_tokens_cost are importable and in __all__."""
    from fourseer import extract_tokens_cost, render_report

    assert render_report is not None
    assert extract_tokens_cost is not None
    import fourseer

    assert "render_report" in fourseer.__all__
    assert "extract_tokens_cost" in fourseer.__all__

def test_public_api_reexports_run_summary() -> None:
    """RunSummary, summarize_run, render_summary are importable and in __all__."""
    from fourseer import RunSummary, render_summary, summarize_run

    assert RunSummary is not None
    assert summarize_run is not None
    assert render_summary is not None
    import fourseer

    assert "RunSummary" in fourseer.__all__
    assert "summarize_run" in fourseer.__all__
    assert "render_summary" in fourseer.__all__


def test_public_api_reexports_taxonomy() -> None:
    """CycleClassification, classify_cycle, classify_run are importable and in __all__."""
    from fourseer import CycleClassification, classify_cycle, classify_run

    assert CycleClassification is not None
    assert classify_cycle is not None
    assert classify_run is not None
    import fourseer

    assert "CycleClassification" in fourseer.__all__
    assert "classify_cycle" in fourseer.__all__
    assert "classify_run" in fourseer.__all__
