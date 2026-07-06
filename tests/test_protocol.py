import json
import pytest
import protocol as proto


@pytest.fixture(autouse=True)
def clean_registry():
    """Isolate tool registry between tests."""
    original = dict(proto._tools)
    yield
    proto._tools.clear()
    proto._tools.update(original)


class TestInitialize:
    def test_returns_protocol_version_and_capabilities(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = proto.handle_request(req)
        assert resp["id"] == 1
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["capabilities"] == {"tools": {}}
        assert resp["result"]["serverInfo"]["name"] == "anki-mcp"


class TestNotifications:
    def test_initialized_returns_none(self):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        assert proto.handle_request(req) is None

    def test_cancelled_returns_none(self):
        req = {"jsonrpc": "2.0", "method": "notifications/cancelled"}
        assert proto.handle_request(req) is None


class TestToolsList:
    def test_returns_registered_tools(self):
        proto.register_tool("my_tool", "does stuff", {"type": "object"}, lambda a: None)

        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = proto.handle_request(req)

        names = [t["name"] for t in resp["result"]["tools"]]
        assert "my_tool" in names

    def test_tool_entry_has_required_fields(self):
        proto.register_tool(
            "shaped",
            "desc",
            {"type": "object", "properties": {"x": {"type": "integer"}}},
            lambda a: None,
        )

        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        resp = proto.handle_request(req)

        tool = next(t for t in resp["result"]["tools"] if t["name"] == "shaped")
        assert "description" in tool
        assert "inputSchema" in tool


class TestToolsCall:
    def test_dispatches_to_handler_and_returns_json(self):
        proto.register_tool("echo", "echo", {"type": "object"},
                            lambda a: {"val": a.get("x")})

        req = {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
               "params": {"name": "echo", "arguments": {"x": 99}}}
        resp = proto.handle_request(req)

        text = resp["result"]["content"][0]["text"]
        assert json.loads(text) == {"val": 99}
        assert resp["result"]["isError"] is False

    def test_unknown_tool_returns_is_error(self):
        req = {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
               "params": {"name": "no_such_tool", "arguments": {}}}
        resp = proto.handle_request(req)

        assert resp["result"]["isError"] is True
        assert "no_such_tool" in resp["result"]["content"][0]["text"]

    def test_handler_exception_returns_is_error(self):
        proto.register_tool("boom", "boom", {"type": "object"},
                            lambda a: (_ for _ in ()).throw(RuntimeError("oops")))

        req = {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
               "params": {"name": "boom", "arguments": {}}}
        resp = proto.handle_request(req)

        assert resp["result"]["isError"] is True
        assert "oops" in resp["result"]["content"][0]["text"]

    def test_handler_returns_none_serialized_as_null(self):
        proto.register_tool("noop", "noop", {"type": "object"}, lambda a: None)

        req = {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
               "params": {"name": "noop", "arguments": {}}}
        resp = proto.handle_request(req)

        text = resp["result"]["content"][0]["text"]
        assert json.loads(text) is None
        assert resp["result"]["isError"] is False


class TestUnknownMethod:
    def test_returns_method_not_found_error(self):
        req = {"jsonrpc": "2.0", "id": 8, "method": "no/such/method"}
        resp = proto.handle_request(req)

        assert "error" in resp
        assert resp["error"]["code"] == -32601
