# Manual smoke test

Run against real Anki before every release. The unit suite mocks `aqt`/`anki` entirely, so nothing below is covered by `pytest`.

## Setup

1. Copy (or symlink) the add-on's repo root — `C:\dev\anki_mcp_addon`, the folder containing `__init__.py` and `manifest.json` — into Anki's add-ons21 directory. On Windows that's `%APPDATA%\Anki2\addons21\` (or Tools → Add-ons → View Files from inside Anki, which opens the same directory). The copied folder can be named anything (e.g. keep it `anki_mcp_addon`); Anki uses the folder name as the add-on's internal module name, and no other renaming is required.
2. Restart Anki.
3. Open a profile with a throwaway collection (not your real one — several steps below delete data).
4. `claude mcp add anki --transport sse http://127.0.0.1:8766/sse` (or configure any MCP client against that URL).

## Core tools

- [ ] `create_notes` — Basic and Cloze, single and batch. Verify cards appear in the target deck (auto-created if new).
- [ ] `search_notes` — plain query, `deck:`, `tag:`, field search. Check `limit`/`offset` paging.
- [ ] `update_note` — edit a field, confirm scheduling (due/interval) unchanged in the browser.
- [ ] `add_tags` / `remove_tags` — including a `::` hierarchical tag.
- [ ] `move_notes` — cards land in the new deck.
- [ ] `delete_notes` — cards actually gone from the browser.
- [ ] `create_deck` / `delete_decks` — including a `Parent::Child` subdeck.
- [ ] `list_decks` — new/due/learn counts match what Anki's deck list shows. Specifically check **learnCount** against a deck with both intraday (relearning today) and day-learning (relearning tomorrow+) cards — should match Anki's own "learning" count.
- [ ] `get_due_cards` → `submit_answer` for all four eases (Again/Hard/Good/Easy). Confirm the card's next due date matches what Anki would show after answering manually.
- [ ] Interleave: `get_due_cards` for deck A, then deck B, then go back and `submit_answer` an A card — should still work (regression check for the `_queued_states` merge fix).
- [ ] `reschedule_cards`, `suspend_cards` (and unsuspend), `forget_cards` — verify in the browser.
- [ ] `get_insights` — with and without a `deck` filter; sanity-check retention rate against a deck with known review history. Try a deck name containing a `"` character (escaping regression check).
- [ ] `sync` — triggers an actual AnkiWeb sync (watch Anki's sync indicator).

## Lifecycle / config

- [ ] Fresh install: server auto-starts on profile open (check `http://127.0.0.1:8766/sse` responds).
- [ ] Port conflict: start another process listening on 8766 first, then open Anki — should see a `showWarning` dialog, not a crash/traceback.
- [ ] Tools → Add-ons → anki-mcp → Config opens the custom dialog (spinbox + status label), not raw JSON.
- [ ] Change the port in the dialog, click "Save and restart" — status label flips to the new port, and the MCP client can reconnect on it without restarting Anki.
- [ ] Save the *same* port again (server already running on it) — should succeed, not report "port already in use" (regression check for the `server_close()` fix).
- [ ] Switch to a second Anki profile without quitting — tool calls should now operate on the second profile's collection.

## Security

- [ ] From a browser tab (not curl), try `fetch('http://127.0.0.1:8766/messages', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '...'})` — should get a 403, request must not reach any tool.
- [ ] Same for `new EventSource('http://127.0.0.1:8766/sse')` from a browser console — 403, no session created.
- [ ] Confirm a normal MCP client (Claude Code/Desktop) still works — those requests carry no `Origin` header and must not be blocked.
