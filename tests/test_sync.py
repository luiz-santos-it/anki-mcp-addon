from unittest.mock import MagicMock
import pytest
from tools.sync import sync


class TestSync:
    def test_uses_sync_collection_and_media_when_available(self, mw_mock):
        mw_mock.sync_collection_and_media.reset_mock()

        result = sync()

        assert result == {"status": "sync triggered"}
        mw_mock.sync_collection_and_media.assert_called_once()

    def test_falls_back_to_on_sync_button_clicked(self, mw_mock):
        del mw_mock.sync_collection_and_media
        try:
            result = sync()
            assert result == {"status": "sync triggered"}
            mw_mock.on_sync_button_clicked.assert_called_once()
        finally:
            mw_mock.sync_collection_and_media = MagicMock()

    def test_raises_when_no_sync_method_available(self, mw_mock):
        del mw_mock.sync_collection_and_media
        del mw_mock.on_sync_button_clicked
        try:
            with pytest.raises(RuntimeError, match="No sync method available"):
                sync()
        finally:
            mw_mock.sync_collection_and_media = MagicMock()
            mw_mock.on_sync_button_clicked = MagicMock()
