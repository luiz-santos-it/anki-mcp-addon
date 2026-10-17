import base64

import pytest
from tools.media import add_audio


def _make_note(field_value="Front text", keys=("Front", "Back")):
    from unittest.mock import MagicMock

    note = MagicMock()
    note.keys.return_value = list(keys)
    store = {k: field_value for k in keys}

    def getitem(k):
        return store[k]

    def setitem(k, v):
        store[k] = v

    note.__getitem__.side_effect = getitem
    note.__setitem__.side_effect = setitem
    return note, store


class TestAddAudio:
    def test_appends_sound_tag_to_field(self, col):
        note, store = _make_note()
        col.get_note.return_value = note
        col.media.write_data.return_value = "word.mp3"

        result = add_audio(101, "Front", base64.b64encode(b"fakeaudio").decode(), "word.mp3")

        col.media.write_data.assert_called_once_with("word.mp3", b"fakeaudio")
        assert store["Front"] == "Front text [sound:word.mp3]"
        col.update_note.assert_called_once_with(note)
        assert result == {"filename": "word.mp3"}

    def test_uses_dedup_filename_from_media_manager(self, col):
        note, store = _make_note()
        col.get_note.return_value = note
        col.media.write_data.return_value = "word-1.mp3"

        result = add_audio(101, "Front", base64.b64encode(b"x").decode(), "word.mp3")

        assert result == {"filename": "word-1.mp3"}
        assert store["Front"] == "Front text [sound:word-1.mp3]"

    def test_raises_when_field_not_found(self, col):
        note, _ = _make_note()
        col.get_note.return_value = note

        with pytest.raises(ValueError, match="Field 'Audio' not found"):
            add_audio(101, "Audio", base64.b64encode(b"x").decode(), "word.mp3")

        col.media.write_data.assert_not_called()
