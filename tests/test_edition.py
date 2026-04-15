"""Tests for edition detection."""

import os
from unittest.mock import patch
import pytest
from zettelforge.edition import (
    Edition,
    EditionError,
    is_enterprise,
    is_community,
    get_edition,
    edition_name,
    reset_edition,
)
from zettelforge.extensions import reset_extensions


@pytest.fixture(autouse=True)
def clean_edition():
    reset_extensions()
    old_key = os.environ.pop("THREATENGRAM_LICENSE_KEY", None)
    yield
    reset_extensions()
    if old_key is not None:
        os.environ["THREATENGRAM_LICENSE_KEY"] = old_key
    else:
        os.environ.pop("THREATENGRAM_LICENSE_KEY", None)


def _force_community():
    """Reset extensions and block the enterprise package import."""
    reset_extensions()


class TestEditionDetection:
    def test_community_by_default(self):
        with patch("zettelforge.extensions.load_extensions") as mock_load:
            # Simulate no extensions loaded
            reset_extensions()
            mock_load.side_effect = lambda: None  # no-op, nothing loaded
            from zettelforge.extensions import _extensions

            # Force _loaded = False so has_extension calls load_extensions
            import zettelforge.extensions as ext_mod

            ext_mod._loaded = False
            ext_mod._extensions.clear()

            # Override load to be a no-op that sets _loaded
            def noop_load():
                ext_mod._loaded = True

            mock_load.side_effect = noop_load
            assert is_community() is True
            assert is_enterprise() is False

    def test_get_edition_returns_community(self):
        import zettelforge.extensions as ext_mod

        ext_mod._extensions.clear()
        ext_mod._loaded = True  # Prevent reload
        assert get_edition() == Edition.COMMUNITY

    def test_enterprise_with_valid_key(self):
        os.environ["THREATENGRAM_LICENSE_KEY"] = "TG-1234-5678-9abc-def0"
        reset_extensions()
        assert is_enterprise() is True
        assert get_edition() == Edition.ENTERPRISE

    def test_community_with_invalid_key(self):
        os.environ["THREATENGRAM_LICENSE_KEY"] = "invalid"
        import zettelforge.extensions as ext_mod

        ext_mod._extensions.clear()
        ext_mod._loaded = False
        # Block the enterprise package import by making it raise ImportError
        import builtins

        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "zettelforge_enterprise":
                raise ImportError("blocked for test")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocked_import):
            ext_mod._loaded = False
            ext_mod._extensions.clear()
            from zettelforge.extensions import load_extensions

            load_extensions()
            assert is_enterprise() is False

    def test_reset_clears_cache(self):
        import zettelforge.extensions as ext_mod

        ext_mod._extensions.clear()
        ext_mod._loaded = True
        assert is_community() is True
        reset_edition()
        # After reset, _loaded is False; block enterprise import
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            ext_mod._loaded = False
            ext_mod._extensions.clear()
            # load_extensions will fail to import and no env var set
            assert is_community() is True


class TestEditionName:
    def test_community_name(self):
        import zettelforge.extensions as ext_mod

        ext_mod._extensions.clear()
        ext_mod._loaded = True
        assert edition_name() == "ZettelForge"

    def test_enterprise_name(self):
        os.environ["THREATENGRAM_LICENSE_KEY"] = "TG-1234-5678-9abc-def0"
        reset_extensions()
        assert edition_name() == "ZettelForge + Extensions"


class TestEditionError:
    def test_edition_error_exists(self):
        assert issubclass(EditionError, Exception)
