from unittest.mock import MagicMock, patch
import pytest
from tools.study import (
    get_due_cards, submit_answer, reschedule_cards, suspend_cards, forget_cards,
    reset_queue, _queued_states,
)


def _make_card(card_id=42, nid=1, did=1, due=100, ivl=7, factor=2500):
    card = MagicMock()
    card.id = card_id
    card.nid = nid
    card.did = did
    card.due = due
    card.ivl = ivl
    card.factor = factor
    note = MagicMock()
    note.note_type.return_value = {"name": "Basic"}
    note.items.return_value = [("Front", "Q"), ("Back", "A")]
    note.tags = []
    card.note.return_value = note
    return card


class TestGetDueCards:
    def test_returns_due_cards(self, col):
        col.v3_scheduler.return_value = False
        col.find_cards.return_value = [42]
        card = _make_card()
        col.get_card.return_value = card
        col.decks.name.return_value = "TestDeck"

        result = get_due_cards("TestDeck")

        assert len(result) == 1
        assert result[0]["cardId"] == 42
        assert result[0]["due"] == 100

    def test_returns_empty_when_no_cards(self, col):
        col.find_cards.return_value = []

        result = get_due_cards("TestDeck")

        assert result == []
        col.get_card.assert_not_called()

    def test_escapes_deck_name_in_query(self, col):
        col.v3_scheduler.return_value = False
        col.find_cards.return_value = []

        get_due_cards("Neuro::Cardio")

        col.find_cards.assert_called_once_with('deck:"Neuro::Cardio" is:due')

    def test_escapes_embedded_quote_in_deck_name(self, col):
        col.v3_scheduler.return_value = False
        col.find_cards.return_value = []

        get_due_cards('Weird "Deck"')

        col.find_cards.assert_called_once_with('deck:"Weird \\"Deck\\"" is:due')

    def test_raises_on_invalid_limit(self, col):
        with pytest.raises(ValueError):
            get_due_cards("D", limit=0)

        with pytest.raises(ValueError):
            get_due_cards("D", limit=101)

    def test_v3_scheduler_caches_queued_states(self, col):
        col.v3_scheduler.return_value = True
        col.find_cards.return_value = [42]
        card = _make_card(42)
        col.get_card.return_value = card
        col.decks.name.return_value = "D"

        qc = MagicMock()
        qc.card.id = 42
        col.sched.get_queued_cards.return_value = MagicMock(cards=[qc])

        _queued_states.clear()
        get_due_cards("D")

        assert 42 in _queued_states
        assert _queued_states[42] is qc

    def test_v3_scheduler_merges_instead_of_clearing_stale_queue(self, col):
        """A prior get_due_cards call (e.g. a different deck) may have left
        unanswered cards cached; a later call must not drop them."""
        col.v3_scheduler.return_value = True
        col.find_cards.return_value = [42]
        card = _make_card(42)
        col.get_card.return_value = card
        col.decks.name.return_value = "D"

        qc_new = MagicMock()
        qc_new.card.id = 42
        col.sched.get_queued_cards.return_value = MagicMock(cards=[qc_new])

        _queued_states.clear()
        stale_qc = MagicMock()
        _queued_states[999] = stale_qc

        get_due_cards("D")

        assert _queued_states[999] is stale_qc
        assert _queued_states[42] is qc_new


class TestSubmitAnswer:
    def test_v2_path_calls_answer_card(self, col):
        col.v3_scheduler.return_value = False
        card = _make_card()
        col.get_card.return_value = card

        submit_answer(42, 3)

        col.sched.answerCard.assert_called_once_with(card, 3)

    def test_v3_path_uses_cached_state(self, col):
        col.v3_scheduler.return_value = True

        qc = MagicMock()
        qc.states.current = MagicMock()
        qc.states.good = MagicMock()
        qc.states.again = MagicMock()
        qc.states.hard = MagicMock()
        qc.states.easy = MagicMock()
        _queued_states[42] = qc

        submit_answer(42, 3)

        col.sched.answer_card.assert_called_once()
        # cached state should be consumed
        assert 42 not in _queued_states

    def test_v3_raises_when_card_not_in_cache(self, col):
        col.v3_scheduler.return_value = True
        _queued_states.clear()

        with pytest.raises(ValueError, match="not in queue"):
            submit_answer(999, 3)

    def test_raises_on_invalid_ease(self, col):
        col.v3_scheduler.return_value = False
        with pytest.raises(ValueError, match="ease must be 1-4"):
            submit_answer(1, 5)

    def test_all_valid_ease_values(self, col):
        col.v3_scheduler.return_value = False
        col.get_card.return_value = _make_card()
        for ease in (1, 2, 3, 4):
            col.sched.answerCard.reset_mock()
            submit_answer(42, ease)
            col.sched.answerCard.assert_called_once()


class TestRescheduleCards:
    def test_calls_set_due_date_with_string_days(self, col):
        reschedule_cards([1, 2, 3], 7)
        col.sched.set_due_date.assert_called_once_with([1, 2, 3], "7")

    def test_zero_days_as_string(self, col):
        reschedule_cards([5], 0)
        col.sched.set_due_date.assert_called_once_with([5], "0")


class TestSuspendCards:
    def test_suspend_calls_suspend_cards(self, col):
        suspend_cards([1, 2], True)
        col.sched.suspend_cards.assert_called_once_with([1, 2])

    def test_unsuspend_calls_unsuspend_cards(self, col):
        suspend_cards([3], False)
        col.sched.unsuspend_cards.assert_called_once_with([3])


class TestForgetCards:
    def test_calls_schedule_cards_as_new(self, col):
        forget_cards([7, 8])
        col.sched.schedule_cards_as_new.assert_called_once_with([7, 8])


class TestResetQueue:
    def test_clears_cached_queue_states(self):
        _queued_states[1] = MagicMock()
        reset_queue()
        assert _queued_states == {}
