import pytest
from tools.decks import create_deck, list_decks, delete_decks


class TestCreateDeck:
    def test_returns_deck_id_and_name(self, col):
        col.decks.id.return_value = 5

        result = create_deck("Physics::Mechanics")

        assert result == {"deckId": 5, "name": "Physics::Mechanics"}
        col.decks.id.assert_called_once_with("Physics::Mechanics", create=True)


class TestListDecks:
    def test_returns_decks_with_counts(self, col):
        col.decks.all.return_value = [{"id": 1, "name": "Default"}]
        col.sched.today = 100

        # new_counts query
        col.db.all.side_effect = [
            [[1, 3]],   # new (queue=0)
            [[1, 2]],   # due (queue=2 due<=today)
            [[1, 1]],   # learn (queue IN 1,3)
        ]

        result = list_decks()

        assert len(result) == 1
        assert result[0]["name"] == "Default"
        assert result[0]["newCount"] == 3
        assert result[0]["dueCount"] == 2
        assert result[0]["learnCount"] == 1

    def test_returns_zeros_for_missing_deck_ids(self, col):
        col.decks.all.return_value = [{"id": 99, "name": "NewDeck"}]
        col.sched.today = 100
        # No rows match deck id 99
        col.db.all.side_effect = [[], [], []]

        result = list_decks()

        assert result[0]["newCount"] == 0
        assert result[0]["dueCount"] == 0
        assert result[0]["learnCount"] == 0


class TestDeleteDecks:
    def test_resolves_names_to_ids_and_removes(self, col):
        col.decks.id.side_effect = [10, 20]

        delete_decks(["DeckA", "DeckB"])

        col.decks.remove.assert_called_once_with([10, 20])

    def test_raises_when_deck_not_found(self, col):
        col.decks.id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            delete_decks(["GhostDeck"])
