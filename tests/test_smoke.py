"""Smoke test: the fourseer package imports cleanly."""


def test_import_fourseer() -> None:
    """Importing fourseer must succeed and expose a version."""
    import fourseer

    assert hasattr(fourseer, "__version__")
    assert isinstance(fourseer.__version__, str)
    assert fourseer.__version__
