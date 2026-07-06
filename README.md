# anki-mcp-addon

Python Anki add-on that exposes your Anki collection as MCP tools for Claude and other LLM clients. Runs an in-process MCP server (SSE transport) directly inside Anki — no AnkiConnect, no Node.js, no external dependencies.

## Prerequisites

- Anki 23.x or later (Python 3.9+ bundled)
- An MCP-compatible client (Claude Code, Claude Desktop, Cursor, Zed, etc.)

## Installation

1. Find your Anki add-ons directory: Anki → Tools → Add-ons → Open Add-ons Folder
2. Copy (or symlink) this entire folder into that directory
3. Restart Anki

The MCP server starts automatically when you open a profile. It listens on `http://127.0.0.1:8766`.

### Optional: change port

Tools → Add-ons → anki-mcp → Config → set `port` to any free port.

## Client setup

### Claude Code

```bash
claude mcp add anki --transport sse http://127.0.0.1:8766/sse
```

Restart Claude Code. Anki must be open whenever you use it.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "anki": {
      "url": "http://127.0.0.1:8766/sse"
    }
  }
}
```

### Other MCP-compatible clients

Use SSE transport URL: `http://127.0.0.1:8766/sse`

Refer to each client's MCP documentation for where to configure SSE servers.

## Available tools

| Tool | Description |
|---|---|
| `create_notes` | Create Basic or Cloze notes. Supports batch. |
| `search_notes` | Search with Anki browser syntax. Returns up to `limit` notes (default 50). |
| `update_note` | Edit note fields in place by note ID. Preserves scheduling data. |
| `add_tags` | Add tags to notes by note ID. Supports `::` hierarchy. |
| `remove_tags` | Remove tags from notes by note ID. |
| `delete_notes` | Delete notes by ID (also deletes associated cards). |
| `move_notes` | Move notes to another deck. |
| `create_deck` | Create deck or subdeck (`Parent::Child::Grandchild`). |
| `list_decks` | List all decks with due/new/learn counts. |
| `delete_decks` | Delete decks by name. |
| `get_due_cards` | Get cards due for review (default limit 20, max 100). |
| `submit_answer` | Record answer for a card: 1=Again, 2=Hard, 3=Good, 4=Easy. |
| `reschedule_cards` | Postpone cards by N days. |
| `suspend_cards` | Suspend or unsuspend cards. |
| `forget_cards` | Reset cards to new state. Preserves note content and tags. |
| `get_insights` | Retention stats, overdue count, mature/young cards for a deck or all decks. |
| `sync` | Trigger AnkiWeb sync. |

## Development

```bash
cd C:\dev\anki_mcp_addon
pip install pytest pytest-mock
pytest
```

Tests run without Anki. The `aqt` and `anki` modules are mocked via `tests/conftest.py`.

## License

MIT
