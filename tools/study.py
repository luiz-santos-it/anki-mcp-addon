import time
from aqt import mw

# Cache queued card states from get_due_cards for use in submit_answer (v3 scheduler).
# Maps card_id -> QueuedCard protobuf object.
_queued_states: dict = {}


def get_due_cards(deck: str, limit: int = 20) -> list:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    query = f'deck:"{deck}" is:due' if deck else "is:due"
    card_ids = list(mw.col.find_cards(query))[:limit]

    if not card_ids:
        return []

    use_v3 = _is_v3()
    if use_v3:
        queued = mw.col.sched.get_queued_cards(fetch_limit=max(limit, 100))
        _queued_states.clear()
        for qc in queued.cards:
            _queued_states[qc.card.id] = qc

    cards = []
    for cid in card_ids:
        card = mw.col.get_card(cid)
        note = card.note()
        cards.append({
            "cardId": cid,
            "noteId": card.nid,
            "deckName": mw.col.decks.name(card.did),
            "modelName": note.note_type()["name"],
            "fields": dict(note.items()),
            "tags": list(note.tags),
            "due": card.due,
            "interval": card.ivl,
            "ease": card.factor,
        })

    return cards


def submit_answer(card_id: int, ease: int) -> None:
    if ease not in (1, 2, 3, 4):
        raise ValueError(f"ease must be 1-4, got {ease}")

    if _is_v3():
        qc = _queued_states.pop(card_id, None)
        if qc is None:
            raise ValueError(
                f"Card {card_id} not in queue. Call get_due_cards first."
            )
        ease_to_state = {
            1: qc.states.again,
            2: qc.states.hard,
            3: qc.states.good,
            4: qc.states.easy,
        }
        from anki.scheduler.v3 import CardAnswer, Rating

        rating_map = {
            1: Rating.Again,
            2: Rating.Hard,
            3: Rating.Good,
            4: Rating.Easy,
        }
        answer = CardAnswer(
            card_id=card_id,
            current_state=qc.states.current,
            new_state=ease_to_state[ease],
            rating=rating_map[ease],
            answered_at_millis=int(time.time() * 1000),
            milliseconds_taken=0,
        )
        mw.col.sched.answer_card(answer)
    else:
        card = mw.col.get_card(card_id)
        mw.col.sched.answerCard(card, ease)


def reschedule_cards(card_ids: list, days: int) -> None:
    mw.col.sched.set_due_date(card_ids, str(days))


def suspend_cards(card_ids: list, suspend: bool) -> None:
    if suspend:
        mw.col.sched.suspend_cards(card_ids)
    else:
        mw.col.sched.unsuspend_cards(card_ids)


def forget_cards(card_ids: list) -> None:
    mw.col.sched.schedule_cards_as_new(card_ids)


def _is_v3() -> bool:
    return bool(
        hasattr(mw.col, "v3_scheduler") and mw.col.v3_scheduler()
    )
