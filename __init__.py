try:
    from aqt import gui_hooks, mw
    _IN_ANKI = True
except ImportError:
    _IN_ANKI = False

if _IN_ANKI:
    from . import protocol, server
    from .tools import decks as _decks
    from .tools import insights as _insights
    from .tools import notes as _notes
    from .tools import study as _study
    from .tools import sync as _sync


def _register_tools():
    p = protocol

    p.register_tool(
        "create_notes",
        "Create Basic or Cloze notes. Supports batch creation.",
        {
            "type": "object",
            "properties": {
                "notes": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "noteType": {"type": "string", "enum": ["Basic", "Cloze"]},
                            "deck": {"type": "string"},
                            "front": {"type": "string"},
                            "back": {"type": "string"},
                            "text": {"type": "string"},
                            "backExtra": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["noteType", "deck"],
                    },
                }
            },
            "required": ["notes"],
        },
        lambda a: _notes.create_notes(a["notes"]),
    )

    p.register_tool(
        "search_notes",
        "Search notes with Anki browser syntax. Returns up to `limit` notes (default 50). "
        "Field search: `Front:*keyword*`. Tag search: `tag:foo`. Deck: `deck:\"Name\"`.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
            },
            "required": ["query"],
        },
        lambda a: _notes.search_notes(a["query"], a.get("limit", 50), a.get("offset", 0)),
    )

    p.register_tool(
        "update_note",
        "Edit note fields in place by note ID. Preserves all card scheduling data.",
        {
            "type": "object",
            "properties": {
                "noteId": {"type": "integer"},
                "fields": {
                    "type": "object",
                    "description": "Field name → new value. Must supply at least one field.",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["noteId", "fields"],
        },
        lambda a: _notes.update_note(a["noteId"], a["fields"]),
    )

    p.register_tool(
        "add_tags",
        "Add tags to notes by note ID. Use '::' for hierarchy (e.g. 'subject::topic'). "
        "Tags must not contain spaces.",
        {
            "type": "object",
            "properties": {
                "noteIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            },
            "required": ["noteIds", "tags"],
        },
        lambda a: _notes.add_tags(a["noteIds"], a["tags"]),
    )

    p.register_tool(
        "remove_tags",
        "Remove tags from notes by note ID.",
        {
            "type": "object",
            "properties": {
                "noteIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            },
            "required": ["noteIds", "tags"],
        },
        lambda a: _notes.remove_tags(a["noteIds"], a["tags"]),
    )

    p.register_tool(
        "delete_notes",
        "Delete notes by ID. Also deletes all associated cards.",
        {
            "type": "object",
            "properties": {
                "noteIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
            },
            "required": ["noteIds"],
        },
        lambda a: _notes.delete_notes(a["noteIds"]),
    )

    p.register_tool(
        "move_notes",
        "Move notes to another deck. Resolves note IDs to card IDs internally.",
        {
            "type": "object",
            "properties": {
                "noteIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                "deck": {"type": "string", "description": "Target deck name. Created if it does not exist."},
            },
            "required": ["noteIds", "deck"],
        },
        lambda a: _notes.move_notes(a["noteIds"], a["deck"]),
    )

    p.register_tool(
        "create_deck",
        "Create a deck or subdeck. Use '::' for hierarchy, e.g. 'Parent::Child'.",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        lambda a: _decks.create_deck(a["name"]),
    )

    p.register_tool(
        "list_decks",
        "List all decks with due/new/learn counts.",
        {"type": "object", "properties": {}},
        lambda a: _decks.list_decks(),
    )

    p.register_tool(
        "delete_decks",
        "Delete decks by name. Also removes all cards inside them.",
        {
            "type": "object",
            "properties": {
                "deckNames": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            },
            "required": ["deckNames"],
        },
        lambda a: _decks.delete_decks(a["deckNames"]),
    )

    p.register_tool(
        "get_due_cards",
        "Get cards due for review. Returns up to `limit` cards (default 20, max 100). "
        "Omit deck to get due cards across all decks.",
        {
            "type": "object",
            "properties": {
                "deck": {"type": "string"},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
        },
        lambda a: _study.get_due_cards(a.get("deck", ""), a.get("limit", 20)),
    )

    p.register_tool(
        "submit_answer",
        "Record answer for a due card. 1=Again, 2=Hard, 3=Good, 4=Easy. "
        "Call get_due_cards before submit_answer.",
        {
            "type": "object",
            "properties": {
                "cardId": {"type": "integer"},
                "ease": {"type": "integer", "enum": [1, 2, 3, 4]},
            },
            "required": ["cardId", "ease"],
        },
        lambda a: _study.submit_answer(a["cardId"], a["ease"]),
    )

    p.register_tool(
        "reschedule_cards",
        "Postpone cards by N days. days=0 = due today.",
        {
            "type": "object",
            "properties": {
                "cardIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                "days": {"type": "integer", "minimum": 0},
            },
            "required": ["cardIds", "days"],
        },
        lambda a: _study.reschedule_cards(a["cardIds"], a["days"]),
    )

    p.register_tool(
        "suspend_cards",
        "Suspend or unsuspend cards. Suspended cards are hidden from scheduling indefinitely but not deleted.",
        {
            "type": "object",
            "properties": {
                "cardIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                "suspend": {"type": "boolean", "description": "true = suspend, false = unsuspend"},
            },
            "required": ["cardIds", "suspend"],
        },
        lambda a: _study.suspend_cards(a["cardIds"], a["suspend"]),
    )

    p.register_tool(
        "forget_cards",
        "Reset cards to new state. Wipes scheduling data but preserves note content and tags.",
        {
            "type": "object",
            "properties": {
                "cardIds": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
            },
            "required": ["cardIds"],
        },
        lambda a: _study.forget_cards(a["cardIds"]),
    )

    p.register_tool(
        "get_insights",
        "Retention stats: retention rate, overdue count, mature/young cards, average interval. "
        "Omit deck for collection-wide stats.",
        {
            "type": "object",
            "properties": {"deck": {"type": "string"}},
        },
        lambda a: _insights.get_insights(a.get("deck")),
    )

    p.register_tool(
        "sync",
        "Trigger AnkiWeb sync.",
        {"type": "object", "properties": {}},
        lambda a: _sync.sync(),
    )


def _on_profile_did_open():
    if mw.col is None:
        return
    _register_tools()
    cfg = mw.addonManager.getConfig(__name__) or {}
    port = cfg.get("port", 8766)
    server.start(port)


if _IN_ANKI:
    gui_hooks.profile_did_open.append(_on_profile_did_open)
