import json

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_NAME = "anki-mcp"
_SERVER_VERSION = "0.1.0"

# name -> {"name", "description", "inputSchema", "handler"}
_tools: dict = {}


def register_tool(name: str, description: str, input_schema: dict, handler) -> None:
    _tools[name] = {
        "name": name,
        "description": description,
        "inputSchema": input_schema,
        "handler": handler,
    }


def handle_request(req: dict):
    """Handle a JSON-RPC 2.0 request. Returns response dict, or None for notifications."""
    rpc_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": _SERVER_NAME, "version": _SERVER_VERSION},
            },
        }

    if method in ("notifications/initialized", "notifications/cancelled"):
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["inputSchema"],
                    }
                    for t in _tools.values()
                ]
            },
        }

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if tool_name not in _tools:
            return _ok(rpc_id, f"Unknown tool: {tool_name}", is_error=True)
        try:
            result = _tools[tool_name]["handler"](arguments)
            return _ok(rpc_id, json.dumps(result))
        except Exception as exc:
            return _ok(rpc_id, str(exc), is_error=True)

    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _ok(rpc_id, text: str, is_error: bool = False) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "content": [{"type": "text", "text": text}],
            "isError": is_error,
        },
    }
