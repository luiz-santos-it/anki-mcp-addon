from unittest.mock import MagicMock, call
import pytest
from tools.notes import (
    search_notes, create_notes, update_note, delete_notes,
    move_notes, add_tags, remove_tags,
)


def _make_note(note_id=101, model="Basic", fields=None, tags=None, card_ids=None):
    n = MagicMock()
    n.note_type.return_value = {"name": model}
    n.items.return_value = list((fields or {"Front": "Q", "Back": "A"}).items())
    n.tags = tags or []
    n.card_ids.return_value = card_ids or []
    return n


class TestSearchNotes:
    def test_returns_notes_with_correct_shape(self, col):
        note = _make_note(101, fields={"Front": "Q", "Back": "A"}, card_ids=[1])
        col.find_notes.return_value = [101]
        col.get_note.return_value = note

        result = search_notes("deck:Default")

        assert result["total"] == 1
        assert result["offset"] == 0
        assert result["notes"][0]["noteId"] == 101
        assert result["notes"][0]["fields"] == {"Front": "Q", "Back": "A"}

    def test_returns_empty_when_no_results(self, col):
        col.find_notes.return_value = []

        result = search_notes("deck:Empty")

        assert result == {"total": 0, "offset": 0, "notes": []}
        col.get_note.assert_not_called()

    def test_applies_offset_and_limit(self, col):
        col.find_notes.return_value = [1, 2, 3, 4, 5]
        col.get_note.return_value = _make_note()

        result = search_notes("*", limit=2, offset=2)

        assert result["total"] == 5
        assert col.get_note.call_count == 2
        col.get_note.assert_any_call(3)
        col.get_note.assert_any_call(4)

    def test_passes_query_to_find_notes(self, col):
        col.find_notes.return_value = []
        search_notes("Front:*keyword*")
        col.find_notes.assert_called_once_with("Front:*keyword*")


class TestCreateNotes:
    def test_creates_basic_note(self, col):
        fake_note = MagicMock()
        fake_note.id = 200
        col.models.by_name.return_value = {"name": "Basic"}
        col.decks.id.return_value = 1
        col.new_note.return_value = fake_note

        result = create_notes([{"noteType": "Basic", "deck": "Default", "front": "F", "back": "B"}])

        assert result["created"] == [200]
        assert result["errors"] == []
        fake_note.__setitem__.assert_any_call("Front", "F")
        fake_note.__setitem__.assert_any_call("Back", "B")

    def test_creates_cloze_note(self, col):
        fake_note = MagicMock()
        fake_note.id = 201
        col.models.by_name.return_value = {"name": "Cloze"}
        col.decks.id.return_value = 1
        col.new_note.return_value = fake_note

        result = create_notes([{"noteType": "Cloze", "deck": "Default", "text": "{{c1::test}}"}])

        assert result["created"] == [201]
        assert result["errors"] == []
        fake_note.__setitem__.assert_any_call("Text", "{{c1::test}}")

    def test_records_error_when_model_not_found(self, col):
        col.models.by_name.return_value = None

        result = create_notes([{"noteType": "Basic", "deck": "Default"}])

        assert result["created"] == []
        assert len(result["errors"]) == 1
        assert "Note 1" in result["errors"][0]

    def test_unknown_note_type_produces_error(self, col):
        result = create_notes([{"noteType": "Unknown", "deck": "Default"}])

        assert result["created"] == []
        assert "Note 1" in result["errors"][0]
        assert "Unknown" in result["errors"][0]

    def test_partial_success(self, col):
        def by_name(name):
            return {"name": name} if name == "Basic" else None

        col.models.by_name.side_effect = by_name

        note1 = MagicMock()
        note1.id = 10
        col.decks.id.return_value = 1
        col.new_note.return_value = note1

        result = create_notes([
            {"noteType": "Basic", "deck": "D", "front": "F", "back": "B"},
            {"noteType": "Cloze", "deck": "D"},  # Cloze model not found in this mock
        ])

        assert result["created"] == [10]
        assert len(result["errors"]) == 1


class TestUpdateNote:
    def test_updates_fields(self, col):
        fake_note = MagicMock()
        col.get_note.return_value = fake_note

        update_note(101, {"Front": "new front"})

        col.get_note.assert_called_once_with(101)
        fake_note.__setitem__.assert_called_once_with("Front", "new front")
        col.update_note.assert_called_once_with(fake_note)

    def test_raises_on_empty_fields(self, col):
        with pytest.raises(ValueError, match="At least one field"):
            update_note(101, {})


class TestDeleteNotes:
    def test_calls_remove_notes(self, col):
        delete_notes([1, 2, 3])
        col.remove_notes.assert_called_once_with([1, 2, 3])


class TestMoveNotes:
    def test_resolves_notes_to_cards_and_moves(self, col):
        n1 = _make_note(card_ids=[10, 11])
        n2 = _make_note(card_ids=[12])
        col.get_note.side_effect = [n1, n2]
        col.decks.id.return_value = 42

        move_notes([1, 2], "TargetDeck")

        col.set_deck.assert_called_once_with([10, 11, 12], 42)
        col.decks.id.assert_called_once_with("TargetDeck", create=True)

    def test_raises_when_no_cards_found(self, col):
        col.get_note.return_value = _make_note(card_ids=[])

        with pytest.raises(ValueError, match="No cards found"):
            move_notes([99], "TargetDeck")


class TestAddTags:
    def test_calls_bulk_add_with_space_joined_tags(self, col):
        add_tags([1, 2], ["concurso", "direito::constitucional"])
        col.tags.bulk_add.assert_called_once_with(
            [1, 2], "concurso direito::constitucional"
        )

    def test_raises_when_tag_contains_space(self, col):
        with pytest.raises(ValueError, match="must not contain spaces"):
            add_tags([1], ["tag with space"])


class TestRemoveTags:
    def test_calls_bulk_remove_with_space_joined_tags(self, col):
        remove_tags([5], ["old-tag", "another"])
        col.tags.bulk_remove.assert_called_once_with([5], "old-tag another")
