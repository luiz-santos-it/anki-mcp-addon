import time
from aqt import mw


def get_insights(deck: str = None) -> dict:
    cutoff_ms = int((time.time() - 30 * 86400) * 1000)
    today = mw.col.sched.today

    if deck:
        deck_id = mw.col.decks.id(deck, create=False)
        if deck_id is None:
            raise ValueError(f"Deck '{deck}' not found")
        card_clause = "c.did = ?"
        card_params = [deck_id]
        plain_clause = "did = ?"
        plain_params = [deck_id]
    else:
        card_clause = "1=1"
        card_params = []
        plain_clause = "1=1"
        plain_params = []

    due_count = _scalar(
        f"SELECT count() FROM cards c WHERE {plain_clause} AND queue=2 AND due<=?",
        *plain_params,
        today,
    )
    overdue_count = _scalar(
        f"SELECT count() FROM cards c WHERE {plain_clause} AND queue=2 AND due<?",
        *plain_params,
        today,
    )
    new_count = _scalar(
        f"SELECT count() FROM cards c WHERE {plain_clause} AND queue=0",
        *plain_params,
    )

    if deck:
        note_ids = list(mw.col.find_notes(f'deck:"{deck}"'))
    else:
        note_ids = list(mw.col.find_notes(""))
    total_notes = len(note_ids)

    rev_rows = mw.col.db.all(
        f"SELECT r.ease FROM revlog r JOIN cards c ON r.cid=c.id "
        f"WHERE r.id >= ? AND r.type=1 AND {card_clause}",
        cutoff_ms,
        *card_params,
    )
    reviews_count = _scalar(
        f"SELECT count() FROM revlog r JOIN cards c ON r.cid=c.id "
        f"WHERE r.id >= ? AND {card_clause}",
        cutoff_ms,
        *card_params,
    )

    scheduled_eases = [r[0] for r in rev_rows]
    if scheduled_eases:
        passed = sum(1 for e in scheduled_eases if e >= 2)
        retention_rate = round(passed / len(scheduled_eases) * 100)
    else:
        retention_rate = 0

    card_rows = mw.col.db.all(
        f"SELECT ivl, queue FROM cards c WHERE {plain_clause} AND queue=2",
        *plain_params,
    )

    mature_cards = sum(1 for ivl, _ in card_rows if ivl >= 21)
    young_cards = sum(1 for ivl, _ in card_rows if 0 < ivl < 21)
    intervals = [ivl for ivl, _ in card_rows if ivl > 0]
    avg_interval = round(sum(intervals) / len(intervals)) if intervals else 0

    return {
        "dueCount": due_count,
        "overdueCount": overdue_count,
        "newCount": new_count,
        "totalNotes": total_notes,
        "retentionRate": retention_rate,
        "reviewsLast30Days": reviews_count,
        "matureCards": mature_cards,
        "youngCards": young_cards,
        "averageInterval": avg_interval,
    }


def _scalar(sql: str, *args) -> int:
    rows = mw.col.db.all(sql, *args)
    return rows[0][0] if rows else 0
