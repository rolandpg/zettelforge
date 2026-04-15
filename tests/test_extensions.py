"""Tests for extension loader."""

import os
import sys
from unittest.mock import patch
import pytest
from zettelforge.extensions import has_extension, get_extension, load_extensions, reset_extensions


class TestExtensions:
    def setup_method(self):
        reset_extensions()
        os.environ.pop("THREATENGRAM_LICENSE_KEY", None)

    def teardown_method(self):
        reset_extensions()
        os.environ.pop("THREATENGRAM_LICENSE_KEY", None)

    def test_no_extensions_by_default(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            load_extensions()
            assert has_extension("enterprise") is False

    def test_get_missing_extension_returns_none(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            assert get_extension("enterprise") is None

    def test_has_extension_returns_bool(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            assert isinstance(has_extension("enterprise"), bool)

    def test_load_is_idempotent(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            load_extensions()
            load_extensions()
            assert has_extension("enterprise") is False

    def test_reset_clears_state(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            load_extensions()
        reset_extensions()
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            assert has_extension("enterprise") is False

    def test_legacy_env_var_activates_enterprise(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            os.environ["THREATENGRAM_LICENSE_KEY"] = "TG-1234-5678-9abc-def0"
            load_extensions()
            assert has_extension("enterprise") is True

    def test_invalid_env_var_does_not_activate(self):
        with patch.dict("sys.modules", {"zettelforge_enterprise": None}):
            os.environ["THREATENGRAM_LICENSE_KEY"] = "invalid-key"
            load_extensions()
            assert has_extension("enterprise") is False
