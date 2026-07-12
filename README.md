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

Tools → Add-ons → anki-mcp → Config opens a settings dialog. Change the port and click "Save and restart MCP server" (restarts the add-on's server, not Anki); no need to restart Anki. "Restore default" resets the field back to 8766.

## Client setup

Tools → Add-ons → anki-mcp → Config → **Client Setup** tab has one-click copy for the Claude Code command and the manual Claude Desktop config, plus an **Export Extension...** button for the Claude Desktop `.mcpb`, all using whatever port you've actually got configured. The steps below are the same actions done by hand, for reference or scripting.

### Claude Code

```bash
claude mcp add anki --transport sse http://127.0.0.1:8766/sse
```

Restart Claude Code. Anki must be open whenever you use it.

### Claude Desktop

Claude Desktop installs local MCP servers as [Desktop Extensions](https://github.com/modelcontextprotocol/mcpb) (`.mcpb` files) rather than through manual JSON config. Easiest path: Tools → Add-ons → anki-mcp → Config → Client Setup tab → **Export Extension...**, save `anki-mcp.mcpb` anywhere.

Then in Claude Desktop: Settings → Extensions → Install Extension..., pick that file. It prompts for the Anki MCP server URL (defaults to `http://127.0.0.1:8766/sse`, only change it if you changed the add-on's port). Anki must be open.

<details>
<summary>Rebuilding the .mcpb from source (maintainers only)</summary>

The exported file is a pre-built copy of `desktop-extension.mcpb`, checked into this repo. `mcp-remote` is bundled as a real dependency (not resolved via `npx` at runtime, which isn't reliably on PATH inside Claude Desktop's Node environment), so a rebuild needs `npm install` first. If you change `desktop-extension/manifest.json`, `desktop-extension/server/index.js`, or `desktop-extension/server/package.json`, rebuild and commit it:

```bash
cd desktop-extension/server
npm install
cd ..
npx -y @anthropic-ai/mcpb pack . ../desktop-extension.mcpb
```
</details>

<details>
<summary>Manual config (older Claude Desktop versions without Extensions support)</summary>

Add to `claude_desktop_config.json` (Windows: `%APPDATA%\Claude\claude_desktop_config.json`). A bare `url` isn't supported in older versions, so bridge through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote):

```json
{
  "mcpServers": {
    "anki": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:8766/sse"]
    }
  }
}
```

If Claude Desktop can't find `npx` on its own, use the absolute path (e.g. `C:\\nvm4w\\nodejs\\npx.cmd` on Windows) instead of `"npx"`.
</details>

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

### Building the AnkiWeb package

```bash
python scripts/build_ankiaddon.py
```

Produces `anki-mcp.ankiaddon` (flat zip, no wrapping folder) for upload to the [AnkiWeb listing](https://ankiweb.net/shared/info/593632040). Must be re-run and re-uploaded whenever a runtime file changes, including `desktop-extension.mcpb`.

## License

MIT
