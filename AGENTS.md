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
config_ui.py   ← Qt settings dialog: Server tab (port/status/restart) + Client Setup tab
                 (one-click Claude Code/Desktop connection helpers + .mcpb export)
client_setup.py ← pure port→command/JSON/URL string builders + .mcpb copy; no Qt/Anki
                 imports, tested directly without mocking aqt.qt
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
desktop-extension/    ← Claude Desktop .mcpb SOURCE (manifest.json + server/index.js, runs a
                         bundled mcp-remote IN-PROCESS via dynamic import); packed via `mcpb pack`
desktop-extension.mcpb ← pre-built, tracked binary — the actual file client_setup.py's
                         export_mcpb() copies; rebuild+commit whenever the source above changes
scripts/build_ankiaddon.py ← builds the AnkiWeb .ankiaddon zip; must include client_setup.py
                              and desktop-extension.mcpb alongside the other runtime files
```

## Key conventions

- **Thread safety**: tool functions call `mw.col` directly; `server.py` routes all tool execution to the Qt main thread via `mw.taskman.run_on_main()` + `concurrent.futures.Future`.
- **No auth, Origin check instead**: `server.py` rejects any request carrying an `Origin` header — only browsers send one, no legitimate MCP client does. This is the CSRF defense (there's no other auth), don't add CORS headers back.
- **Server lifecycle**: `server.stop()` must call both `shutdown()` and `server_close()`, or the port stays bound and a same-port restart fails.
- **Benign connection errors**: `_MCPServer.handle_error()` and the `except _BENIGN_CONNECTION_ERRORS` in `_handle_sse` both swallow `BrokenPipeError`/`ConnectionResetError`/`ConnectionAbortedError` — a client disconnecting mid-transport-negotiation is routine (confirmed with real Claude Desktop/mcp-remote traffic), not a bug worth a traceback in Anki's console.
- **Scheduler compat**: `study.py` checks `mw.col.v3_scheduler()` and branches between v3 `answer_card(CardAnswer(...))` and legacy `answerCard(card, ease)`.
- **v3 state cache**: `_queued_states` in `study.py` maps `card_id → QueuedCard`. Populated by `get_due_cards` (merged, not cleared, so concurrent decks don't clobber each other), consumed by `submit_answer`, and dropped via `reset_queue()` on profile open so stale state from a previous collection can't leak in.
- **Deck-name escaping**: build search queries with `tools/search.py:quote_deck()`, never raw f-string interpolation — deck names can contain `"`.
- **SQL in insights**: `mw.col.db.all(sql, *args)` — positional params, not list.
- **No external deps**: stdlib only (`http.server`, `threading`, `queue`, `json`, `uuid`, `concurrent.futures`).

## Testing

Tests mock the `aqt` and `anki` modules via `sys.modules` injection in `conftest.py`. Tool functions are called directly; no HTTP server needed. Protocol tests clear `_tools` registry between tests via `clean_registry` fixture. `server.py`/`config_ui.py` tests load fresh copies of the module via `importlib` (they use relative imports) to avoid needing the real add-on package. `client_setup.py` has zero Qt/Anki imports, so `tests/test_client_setup.py` imports it directly — no mocking needed.

## Packaging

`desktop-extension.mcpb` is a pre-built binary checked into git (see the `.gitignore` exception for it). `mcp-remote` is bundled as a real dependency under `desktop-extension/server/node_modules/` (gitignored, reinstall with `npm install` from `desktop-extension/server/`) and run **in-process** via `process.argv` rewrite + dynamic `import()` — never spawn a child with `process.execPath`: under Claude Desktop's built-in Node that path is the Electron binary (claude.exe), and spawning it launches a second app instance that dies on the single-instance lock with zero stderr. The bridge also forces `--transport sse-only`, since mcp-remote's default http-first probe always 404s against this SSE-only server and the wasted round-trip can blow Claude Desktop's initialize timeout. Rebuild via `npm install` (in `desktop-extension/server/`) then `npx -y @anthropic-ai/mcpb pack desktop-extension desktop-extension.mcpb`, and commit the result, whenever `desktop-extension/manifest.json`, `desktop-extension/server/index.js`, or `desktop-extension/server/package.json` change. `scripts/build_ankiaddon.py` builds the AnkiWeb submission zip; its file list must be kept in sync with any new runtime file (it's an explicit list, not a glob).

## Client setup (after installing add-on)

The add-on's own Config dialog (Tools → Add-ons → anki-mcp → Config → Client Setup tab) generates all of this for the user already, using their actual configured port. Manually:

Claude Code:

```bash
claude mcp add anki --transport sse http://127.0.0.1:8766/sse
```

Claude Desktop: install `desktop-extension.mcpb` (Settings → Extensions), not manual JSON — see README for the older manual-config fallback and why a bare `"url"` doesn't work in every Desktop version.
