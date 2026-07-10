import time

from aqt import mw


def create_deck(name: str) -> dict:
    deck_id = mw.col.decks.id(name, create=True)
    return {"deckId": deck_id, "name": name}


def list_decks() -> list:
    decks = mw.col.decks.all()
    today = mw.col.sched.today

    new_counts = {}
    for row in mw.col.db.all(
        "SELECT did, count() FROM cards WHERE queue=0 GROUP BY did"
    ):
        new_counts[row[0]] = row[1]

    due_counts = {}
    for row in mw.col.db.all(
        "SELECT did, count() FROM cards WHERE queue=2 AND due<=? GROUP BY did",
        today,
    ):
        due_counts[row[0]] = row[1]

    now_ts = int(time.time())
    learn_counts = {}
    # queue=1 (intraday learning): due is a unix timestamp.
    for row in mw.col.db.all(
        "SELECT did, count() FROM cards WHERE queue=1 AND due<=? GROUP BY did",
        now_ts,
    ):
        learn_counts[row[0]] = learn_counts.get(row[0], 0) + row[1]
    # queue=3 (day learning): due is a day number, like queue=2.
    for row in mw.col.db.all(
        "SELECT did, count() FROM cards WHERE queue=3 AND due<=? GROUP BY did",
        today,
    ):
        learn_counts[row[0]] = learn_counts.get(row[0], 0) + row[1]

    result = []
    for deck in decks:
        did = deck["id"]
        result.append({
            "name": deck["name"],
            "id": did,
            "newCount": new_counts.get(did, 0),
            "dueCount": due_counts.get(did, 0),
            "learnCount": learn_counts.get(did, 0),
        })
    return result


def delete_decks(deck_names: list) -> None:
    deck_ids = []
    for name in deck_names:
        did = mw.col.decks.id(name, create=False)
        if did is None:
            raise ValueError(f"Deck '{name}' not found")
        deck_ids.append(did)
    mw.col.decks.remove(deck_ids)
