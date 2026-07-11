#!/usr/bin/env node
// Thin bridge: Claude Desktop spawns this over stdio, we forward to the
// anki-mcp-addon SSE server (running inside Anki) via mcp-remote.
const { spawn } = require("node:child_process");

const url = process.env.ANKI_MCP_URL || "http://127.0.0.1:8766/sse";

const child = spawn("npx", ["-y", "mcp-remote", url], {
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (err) => {
  console.error("Failed to start mcp-remote:", err);
  process.exit(1);
});
