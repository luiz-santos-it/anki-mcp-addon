#!/usr/bin/env node
// Runs the bundled mcp-remote in-process. Claude Desktop's "built-in Node"
// is the Electron binary, where process.execPath is claude.exe — spawning it
// launches a second app instance that dies on the single-instance lock, so a
// child process is not an option here.
const { pathToFileURL } = require("node:url");

const url = process.env.ANKI_MCP_URL || "http://127.0.0.1:8766/sse";
const entry = require.resolve("mcp-remote/dist/proxy.js");

// sse-only skips mcp-remote's http-first probe (always 404s against our
// SSE-only server) that otherwise blows past Claude Desktop's init timeout.
process.argv = [process.argv[0], entry, url, "--transport", "sse-only"];
import(pathToFileURL(entry).href);
