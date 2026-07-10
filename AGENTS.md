# anki-mcp-addon

Python Anki add-on that exposes Anki as MCP tools via an in-process SSE server. Zero external deps; calls Anki's internal Python APIs directly.

## Commands

```bash
pytest              # run all tests (no Anki required)
pytest -x           # stop on first failure
pytest tests/test_notes.py  # single file
```

## Architecture

```
__init__.py    ← Anki entry point: registers tools, starts server, wires config UI/hooks
config_ui.py   ← Qt settings dialog (port + status + restart button), via addonManager.setConfigAction
protocol.py    ← JSON-RPC 2.0 + MCP dispatch; tool registry (_tools dict)
server.py      ← ThreadingHTTPServer; GET /sse (SSE stream), POST /messages
tools/
  notes.py     ← 7 tools: create/search/update/delete/move notes + tag management
  decks.py     ← 3 tools: create/list/delete decks
  study.py     ← 5 tools: get_due_cards, submit_answer, reschedule, suspend, forget
  insights.py  ← 1 tool: retention stats via direct SQL (mw.col.db)
  sync.py      ← 1 tool: trigger AnkiWeb sync
  search.py    ← shared deck-name quoting for Anki search syntax
tests/
  conftest.py  ← fakes aqt/anki via sys.modules before any imports
```

## Key conventions

- **Thread safety**: tool functions call `mw.col` directly; `server.py` routes all tool execution to the Qt main thread via `mw.taskman.run_on_main()` + `concurrent.futures.Future`.
- **No auth, Origin check instead**: `server.py` rejects any request carrying an `Origin` header — only browsers send one, no legitimate MCP client does. This is the CSRF defense (there's no other auth), don't add CORS headers back.
- **Server lifecycle**: `server.stop()` must call both `shutdown()` and `server_close()`, or the port stays bound and a same-port restart fails.
- **Scheduler compat**: `study.py` checks `mw.col.v3_scheduler()` and branches between v3 `answer_card(CardAnswer(...))` and legacy `answerCard(card, ease)`.
- **v3 state cache**: `_queued_states` in `study.py` maps `card_id → QueuedCard`. Populated by `get_due_cards` (merged, not cleared, so concurrent decks don't clobber each other), consumed by `submit_answer`, and dropped via `reset_queue()` on profile open so stale state from a previous collection can't leak in.
- **Deck-name escaping**: build search queries with `tools/search.py:quote_deck()`, never raw f-string interpolation — deck names can contain `"`.
- **SQL in insights**: `mw.col.db.all(sql, *args)` — positional params, not list.
- **No external deps**: stdlib only (`http.server`, `threading`, `queue`, `json`, `uuid`, `concurrent.futures`).

## Testing

Tests mock the `aqt` and `anki` modules via `sys.modules` injection in `conftest.py`. Tool functions are called directly; no HTTP server needed. Protocol tests clear `_tools` registry between tests via `clean_registry` fixture. `server.py`/`config_ui.py` tests load fresh copies of the module via `importlib` (they use relative imports) to avoid needing the real add-on package.

## Client setup (after installing add-on)

```bash
claude mcp add anki --transport sse http://127.0.0.1:8766/sse
```

```json
{ "mcpServers": { "anki": { "url": "http://127.0.0.1:8766/sse" } } }
```
