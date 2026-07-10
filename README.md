# anki-mcp-addon

**Talk to your Anki collection.** Point Claude (or any MCP client) at your flashcards and study, edit, and analyze your deck in plain conversation. No AnkiConnect, no Node.js, no external dependencies. It's a small Python add-on that runs an MCP server inside Anki itself.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) ![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg) ![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)

## Why

Anki is powerful but manual: browsing, tagging, and reviewing all happen through the desktop UI. This add-on turns your collection into something an LLM can actually work with, so you can ask for things instead of clicking through them:

- *"Quiz me on today's due cards, one at a time."*
- *"Turn these notes into 15 flashcards and put them in my Spanish deck."*
- *"How's my retention been this month? Which decks am I falling behind on?"*
- *"Find every card tagged `hard`, move them into a Review deck."*
- *"I got that one wrong, mark it Again."*

Everything runs locally. Your collection never leaves your machine except through whatever MCP client you're already using.

## Prerequisites

- Anki 23.10 or later (Python 3.9+ bundled)
- An MCP-compatible client (Claude Code, Claude Desktop, Cursor, Zed, etc.)

## Installation

### Via AnkiWeb (recommended)

1. Anki → Tools → Add-ons → Get Add-ons
2. Paste this code: `593632040`
3. Restart Anki

[Add-on page on AnkiWeb](https://ankiweb.net/shared/info/593632040)

### Manual (for development or the latest unreleased code)

1. Find your Anki add-ons directory: Anki → Tools → Add-ons → View Files (opens `%APPDATA%\Anki2\addons21\` on Windows)
2. Copy (or symlink) this repo's root folder (the one containing `__init__.py` and `manifest.json`) into that add-ons directory
3. Restart Anki

Either way, the MCP server starts automatically when you open a profile. It listens on `http://127.0.0.1:8766`.

### Optional: change port

Tools → Add-ons → anki-mcp → Config opens a settings dialog. Change the port and click "Save and restart"; no need to restart Anki.

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

**Notes**

| Tool | Description |
|---|---|
| `create_notes` | Create Basic or Cloze notes. Supports batch. |
| `search_notes` | Search with Anki browser syntax. Returns up to `limit` notes (default 50). |
| `update_note` | Edit note fields in place by note ID. Preserves scheduling data. |
| `add_tags` / `remove_tags` | Tag notes by ID. Supports `::` hierarchy. |
| `delete_notes` | Delete notes by ID (also deletes associated cards). |
| `move_notes` | Move notes to another deck. |

**Decks**

| Tool | Description |
|---|---|
| `create_deck` | Create deck or subdeck (`Parent::Child::Grandchild`). |
| `list_decks` | List all decks with due/new/learn counts. |
| `delete_decks` | Delete decks by name. |

**Study**

| Tool | Description |
|---|---|
| `get_due_cards` | Get cards due for review (default limit 20, max 100). |
| `submit_answer` | Record answer for a card: 1=Again, 2=Hard, 3=Good, 4=Easy. |
| `reschedule_cards` | Postpone cards by N days. |
| `suspend_cards` | Suspend or unsuspend cards. |
| `forget_cards` | Reset cards to new state. Preserves note content and tags. |

**Insights & sync**

| Tool | Description |
|---|---|
| `get_insights` | Retention stats, overdue count, mature/young cards for a deck or all decks. |
| `sync` | Trigger AnkiWeb sync. |

## Development

```bash
pip install pytest
pytest
```

Tests run without Anki. The `aqt` and `anki` modules are mocked via `tests/conftest.py`.

## License

MIT
