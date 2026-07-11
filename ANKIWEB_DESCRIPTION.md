Point Claude (or any MCP client) at your Anki collection and study, edit, and analyze your deck in plain conversation. Runs an MCP server inside Anki itself. No AnkiConnect, no Node.js, no external dependencies.

**Examples of what you can ask:**

- "Quiz me on today's due cards, one at a time."
- "Turn these notes into 15 flashcards and put them in my Spanish deck."
- "How's my retention been this month? Which decks am I falling behind on?"
- "Find every card tagged hard, move them into a Review deck."
- "I got that one wrong, mark it Again."

Everything runs locally. Your collection never leaves your machine except through whatever MCP client you're already using.

**Setup**

Once enabled, the MCP server starts automatically whenever you open an Anki profile. Tools → Add-ons → anki-mcp → Config opens a settings dialog with a Client Setup tab: one-click copy for the Claude Code command, one-click export of the Claude Desktop extension, and the raw connection URL for any other MCP client.

Full docs, tool list, and source: https://github.com/luiz-santos-it/anki-mcp-addon
