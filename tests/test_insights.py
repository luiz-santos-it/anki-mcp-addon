import pytest
from tools.insights import get_insights


def _db_seq(col, *sequences):
    """Set col.db.all to return each sequence in order."""
    col.db.all.side_effect = list(sequences)


class TestGetInsightsDeckScoped:
    def _setup(self, col, *, deck_id=10, today=100,
               due=0, overdue=0, new_=0, note_count=0,
               rev_eases=(), all_reviews=0,
               card_rows=()):
        col.decks.id.return_value = deck_id
        col.sched.today = today
        col.find_notes.return_value = list(range(note_count))
        _db_seq(
            col,
            [[due]],           # due count
            [[overdue]],       # overdue count
            [[new_]],          # new count
            [[e] for e in rev_eases],  # retention eases (type=1)
            [[all_reviews]],   # all reviews count
            list(card_rows),   # card intervals + queues
        )

    def test_retention_rate_from_type1_reviews(self, col):
        self._setup(col, rev_eases=(3, 1, 4), all_reviews=3)
        result = get_insights("TestDeck")
        # 2 passed (ease>=2) out of 3 → 67%
        assert result["retentionRate"] == 67
        assert result["reviewsLast30Days"] == 3

    def test_retention_rate_zero_when_no_reviews(self, col):
        self._setup(col, rev_eases=(), all_reviews=0)
        result = get_insights("TestDeck")
        assert result["retentionRate"] == 0

    def test_mature_and_young_card_classification(self, col):
        # mature = ivl >= 21, young = 0 < ivl < 21
        self._setup(col, card_rows=[(30, 2), (10, 2), (0, 2)])
        result = get_insights("TestDeck")
        assert result["matureCards"] == 1
        assert result["youngCards"] == 1

    def test_average_interval_excludes_zero(self, col):
        self._setup(col, card_rows=[(10, 2), (20, 2), (0, 2)])
        result = get_insights("TestDeck")
        assert result["averageInterval"] == 15  # (10+20)/2

    def test_counts_due_overdue_new_notes(self, col):
        self._setup(col, due=2, overdue=1, new_=3, note_count=4)
        result = get_insights("TestDeck")
        assert result["dueCount"] == 2
        assert result["overdueCount"] == 1
        assert result["newCount"] == 3
        assert result["totalNotes"] == 4

    def test_raises_when_deck_not_found(self, col):
        col.decks.id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            get_insights("GhostDeck")

    def test_all_zeros_for_empty_deck(self, col):
        self._setup(col)
        result = get_insights("EmptyDeck")
        assert result["retentionRate"] == 0
        assert result["matureCards"] == 0
        assert result["youngCards"] == 0
        assert result["averageInterval"] == 0

    def test_escapes_embedded_quote_in_deck_name(self, col):
        self._setup(col)
        get_insights('Weird "Deck"')
        col.find_notes.assert_called_once_with('deck:"Weird \\"Deck\\""')


class TestGetInsightsNoScope:
    def test_collection_wide_uses_no_deck_filter(self, col):
        col.sched.today = 100
        col.find_notes.return_value = []
        _db_seq(
            col,
            [[0]],  # due
            [[0]],  # overdue
            [[0]],  # new
            [],     # rev eases (empty)
            [[0]],  # all reviews
            [],     # card rows
        )

        result = get_insights()  # no deck arg

        assert result["dueCount"] == 0
        col.decks.id.assert_not_called()
        col.find_notes.assert_called_once_with("")
