from aqt import mw


def search_notes(query: str, limit: int = 50, offset: int = 0) -> dict:
    note_ids = list(mw.col.find_notes(query))
    total = len(note_ids)
    page_ids = note_ids[offset : offset + limit]
    notes = []
    for nid in page_ids:
        note = mw.col.get_note(nid)
        notes.append({
            "noteId": nid,
            "modelName": note.note_type()["name"],
            "fields": dict(note.items()),
            "tags": list(note.tags),
            "cards": list(note.card_ids()),
        })
    return {"total": total, "offset": offset, "notes": notes}


def create_notes(notes_input: list) -> dict:
    created = []
    errors = []
    for i, n in enumerate(notes_input):
        label = f"Note {i + 1}"
        note_type_key = n.get("noteType", "Basic")
        deck = n.get("deck", "Default")

        if note_type_key == "Basic":
            model_name = "Basic"
            fields = {"Front": n.get("front", ""), "Back": n.get("back", "")}
        elif note_type_key == "Cloze":
            model_name = "Cloze"
            fields = {"Text": n.get("text", ""), "Back Extra": n.get("backExtra", "")}
        else:
            errors.append(f"{label}: unknown noteType '{note_type_key}'")
            continue

        model = mw.col.models.by_name(model_name)
        if model is None:
            errors.append(f"{label}: model '{model_name}' not found in collection")
            continue

        deck_id = mw.col.decks.id(deck, create=True)
        note = mw.col.new_note(model)
        try:
            for fname, val in fields.items():
                note[fname] = val
            note.tags = n.get("tags", [])
            mw.col.add_note(note, deck_id)
            created.append(note.id)
        except Exception as e:
            errors.append(f"{label}: {e}")

    return {"created": created, "errors": errors}


def update_note(note_id: int, fields: dict) -> None:
    if not fields:
        raise ValueError("At least one field must be provided")
    note = mw.col.get_note(note_id)
    for fname, val in fields.items():
        note[fname] = val
    mw.col.update_note(note)


def delete_notes(note_ids: list) -> None:
    mw.col.remove_notes(note_ids)


def move_notes(note_ids: list, deck: str) -> None:
    card_ids = []
    for nid in note_ids:
        note = mw.col.get_note(nid)
        card_ids.extend(note.card_ids())
    if not card_ids:
        raise ValueError("No cards found for the given note IDs")
    deck_id = mw.col.decks.id(deck, create=True)
    mw.col.set_deck(card_ids, deck_id)


def add_tags(note_ids: list, tags: list) -> None:
    for t in tags:
        if " " in t:
            raise ValueError(f"Tag '{t}' must not contain spaces")
    mw.col.tags.bulk_add(note_ids, " ".join(tags))


def remove_tags(note_ids: list, tags: list) -> None:
    for t in tags:
        if " " in t:
            raise ValueError(f"Tag '{t}' must not contain spaces")
    mw.col.tags.bulk_remove(note_ids, " ".join(tags))
