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

    learn_counts = {}
    for row in mw.col.db.all(
        "SELECT did, count() FROM cards WHERE queue IN (1,3) GROUP BY did"
    ):
        learn_counts[row[0]] = row[1]

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
