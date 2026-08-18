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
