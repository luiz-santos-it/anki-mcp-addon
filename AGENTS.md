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
__init__.py        ← Anki entry point: registers tools, starts server on profile open
protocol.py        ← JSON-RPC 2.0 + MCP dispatch; tool registry (_tools dict)
server.py          ← ThreadingHTTPServer; GET /sse (SSE stream), POST /messages
tools/
  notes.py         ← 7 tools: create/search/update/delete/move notes + tag management
  decks.py         ← 3 tools: create/list/delete decks
  study.py         ← 5 tools: get_due_cards, submit_answer, reschedule, suspend, forget
  insights.py      ← 1 tool: retention stats via direct SQL (mw.col.db)
  sync.py          ← 1 tool: trigger AnkiWeb sync
tests/
  conftest.py      ← fakes aqt/anki via sys.modules before any imports
```

## Key conventions

- **Thread safety**: tool functions call `mw.col` directly; `server.py` routes all tool execution to the Qt main thread via `mw.taskman.run_on_main()` + `concurrent.futures.Future`.
- **Scheduler compat**: `study.py` checks `mw.col.v3_scheduler()` and branches between v3 `answer_card(CardAnswer(...))` and legacy `answerCard(card, ease)`.
- **v3 state cache**: `_queued_states` in `study.py` maps `card_id → QueuedCard`. Populated by `get_due_cards`, consumed by `submit_answer`.
- **SQL in insights**: `mw.col.db.all(sql, *args)` — positional params, not list.
- **No external deps**: stdlib only (`http.server`, `threading`, `queue`, `json`, `uuid`, `concurrent.futures`).

## Testing

Tests mock the `aqt` and `anki` modules via `sys.modules` injection in `conftest.py`. Tool functions are called directly; no HTTP server needed. Protocol tests clear `_tools` registry between tests via `clean_registry` fixture.

## Client setup (after installing add-on)

```bash
claude mcp add anki --transport sse http://127.0.0.1:8766/sse
```

```json
{ "mcpServers": { "anki": { "url": "http://127.0.0.1:8766/sse" } } }
```
