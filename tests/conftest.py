import sys
from unittest.mock import MagicMock
import pytest

# Inject fake aqt/anki before any add-on code imports them.
# Must happen at module level (before any tool imports in test files).
_fake_aqt = MagicMock()
_fake_anki = MagicMock()

sys.modules["aqt"] = _fake_aqt
sys.modules["aqt.qt"] = MagicMock()
sys.modules["anki"] = _fake_anki
sys.modules["anki.scheduler"] = MagicMock()
sys.modules["anki.scheduler.v3"] = MagicMock()


@pytest.fixture
def col():
    c = MagicMock()
    _fake_aqt.mw.col = c
    return c


@pytest.fixture
def mw_mock():
    return _fake_aqt.mw
