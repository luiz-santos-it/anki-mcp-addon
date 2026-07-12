#!/usr/bin/env node
// Thin bridge: Claude Desktop spawns this over stdio, we forward to the
// anki-mcp-addon SSE server (running inside Anki) via a bundled mcp-remote
// (no npx/PATH dependency — Claude Desktop's Node environment may not have it).
const { spawn } = require("node:child_process");
const path = require("node:path");

const url = process.env.ANKI_MCP_URL || "http://127.0.0.1:8766/sse";
const mcpRemoteEntry = require.resolve("mcp-remote/dist/proxy.js");

const child = spawn(process.execPath, [mcpRemoteEntry, url], {
  stdio: "inherit",
  cwd: path.dirname(mcpRemoteEntry),
});

child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (err) => {
  console.error("Failed to start mcp-remote:", err);
  process.exit(1);
});
