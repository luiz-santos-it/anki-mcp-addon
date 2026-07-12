import importlib.util
import socket
import sys
import types
from email.message import Message
from pathlib import Path

import pytest

# server.py's relative import needs a real package; build a throwaway one
# pointing at the repo root instead of importing the real add-on __init__.py.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PKG_NAME = "_server_under_test"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{_PKG_NAME}.{name}", _REPO_ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{_PKG_NAME}.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def server_mod(mw_mock):
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_REPO_ROOT)]
    sys.modules[_PKG_NAME] = pkg
    proto = _load("protocol")
    srv = _load("server")
    srv._MAIN_THREAD_TIMEOUT = 0.05
    yield srv, proto
    for name in (f"{_PKG_NAME}.protocol", f"{_PKG_NAME}.server", _PKG_NAME):
        sys.modules.pop(name, None)


def _req(rpc_id=1):
    return b'{"jsonrpc": "2.0", "id": 1, "method": "initialize"}'


class TestDispatchMainThreadPath:
    def test_runs_handler_once_when_taskman_executes_inline(self, server_mod, mw_mock):
        srv, proto = server_mod
        calls = []
        original = proto.handle_request

        def counting(req):
            calls.append(req)
            return original(req)

        proto.handle_request = counting
        mw_mock.taskman.run_on_main = lambda fn: fn()

        srv._sessions["sid"] = __import__("queue").Queue()
        srv._dispatch("sid", _req())

        assert len(calls) == 1
        result = srv._sessions["sid"].get_nowait()
        assert "protocolVersion" in result


class TestDispatchFallbackPath:
    def test_falls_back_when_taskman_never_runs_the_task(self, server_mod, mw_mock):
        srv, proto = server_mod
        calls = []
        original = proto.handle_request

        def counting(req):
            calls.append(req)
            return original(req)

        proto.handle_request = counting
        mw_mock.taskman.run_on_main = lambda fn: None

        srv._sessions["sid"] = __import__("queue").Queue()
        srv._dispatch("sid", _req())

        assert len(calls) == 1
        result = srv._sessions["sid"].get_nowait()
        assert "protocolVersion" in result


class TestDispatchExceptionPath:
    def test_real_handler_exception_propagates_without_double_execution(self, server_mod, mw_mock):
        srv, proto = server_mod
        calls = []

        def boom(req):
            calls.append(req)
            raise RuntimeError("protocol bug")

        proto.handle_request = boom
        mw_mock.taskman.run_on_main = lambda fn: fn()

        with pytest.raises(RuntimeError, match="protocol bug"):
            srv._dispatch("sid", _req())

        assert len(calls) == 1


def _make_handler(srv, path="/sse", origin=None):
    handler = srv._MCPHandler.__new__(srv._MCPHandler)
    handler.headers = Message()
    if origin is not None:
        handler.headers["Origin"] = origin
    handler.path = path
    return handler


class TestBrowserOriginRejection:
    def test_is_browser_request_true_when_origin_header_present(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, origin="https://evil.example")
        assert handler._is_browser_request() is True

    def test_is_browser_request_false_when_origin_header_absent(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv)
        assert handler._is_browser_request() is False

    def test_do_get_rejects_request_carrying_origin_header(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, path="/sse", origin="https://evil.example")
        errors = []
        handled = []
        handler.send_error = lambda code, *a, **k: errors.append(code)
        handler._handle_sse = lambda: handled.append(True)

        handler.do_GET()

        assert errors == [403]
        assert handled == []

    def test_do_post_rejects_request_carrying_origin_header(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, path="/messages", origin="https://evil.example")
        errors = []
        handled = []
        handler.send_error = lambda code, *a, **k: errors.append(code)
        handler._handle_post = lambda: handled.append(True)

        handler.do_POST()

        assert errors == [403]
        assert handled == []

    def test_do_options_always_rejected(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, path="/messages")
        errors = []
        handler.send_error = lambda code, *a, **k: errors.append(code)

        handler.do_OPTIONS()

        assert errors == [403]

    def test_do_get_without_origin_reaches_sse_handler(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, path="/sse")
        handled = []
        handler._handle_sse = lambda: handled.append(True)

        handler.do_GET()

        assert handled == [True]


class TestStartPortConflict:
    def test_start_returns_false_and_does_not_raise_when_port_taken(self, server_mod):
        srv, _ = server_mod
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        try:
            assert srv.start(port) is False
            assert srv.is_running() is False
        finally:
            blocker.close()

    def test_start_stop_lifecycle_on_free_port(self, server_mod):
        srv, _ = server_mod
        assert srv.is_running() is False
        assert srv.start(0) is True  # port 0 -> OS picks a free port
        assert srv.is_running() is True
        srv.stop()
        assert srv.is_running() is False

    def test_stop_closes_the_listening_socket(self, server_mod):
        srv, _ = server_mod
        assert srv.start(0) is True
        closed = []
        srv._server.server_close = lambda: closed.append(True)

        srv.stop()

        assert closed == [True]  # shutdown() alone doesn't release the socket fd


class TestHandlePostBodyLimits:
    def test_rejects_malformed_content_length(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, path="/messages")
        handler.headers["Content-Length"] = "not-a-number"
        errors = []
        handler.send_error = lambda code, *a, **k: errors.append(code)

        handler._handle_post()

        assert errors == [400]

    def test_rejects_content_length_over_cap(self, server_mod):
        srv, _ = server_mod
        handler = _make_handler(srv, path="/messages")
        handler.headers["Content-Length"] = str(srv._MAX_BODY_BYTES + 1)
        errors = []
        handler.send_error = lambda code, *a, **k: errors.append(code)

        handler._handle_post()

        assert errors == [413]


class TestHandleSseClientDisconnect:
    def _make_sse_handler(self, srv):
        handler = _make_handler(srv, path="/sse")
        handler.send_response = lambda *a, **k: None
        handler.send_header = lambda *a, **k: None
        handler.end_headers = lambda *a, **k: None
        return handler

    def _install_immediately_empty_queue(self, srv, monkeypatch):
        class _ImmediateEmptyQueue:
            def get(self, timeout=None):
                raise srv.queue.Empty

        monkeypatch.setattr(srv.queue, "Queue", _ImmediateEmptyQueue)

    def test_connection_aborted_error_during_ping_is_swallowed(self, server_mod, monkeypatch):
        srv, _ = server_mod
        self._install_immediately_empty_queue(srv, monkeypatch)
        handler = self._make_sse_handler(srv)

        writes = []

        class _FakeWfile:
            def write(self, data):
                writes.append(data)
                if len(writes) > 1:  # first write is the "endpoint" event, second is the ping
                    raise ConnectionAbortedError("simulated WinError 10053")

            def flush(self):
                pass

        handler.wfile = _FakeWfile()

        handler._handle_sse()  # must not raise

        assert len(writes) == 2

    def test_broken_pipe_and_connection_reset_still_swallowed(self, server_mod, monkeypatch):
        srv, _ = server_mod
        self._install_immediately_empty_queue(srv, monkeypatch)

        for exc_type in (BrokenPipeError, ConnectionResetError):
            handler = self._make_sse_handler(srv)
            writes = []

            class _FakeWfile:
                def write(self, data, _exc=exc_type):
                    writes.append(data)
                    if len(writes) > 1:
                        raise _exc("simulated")

                def flush(self):
                    pass

            handler.wfile = _FakeWfile()

            handler._handle_sse()  # must not raise

    def test_session_is_cleaned_up_after_client_disconnect(self, server_mod, monkeypatch):
        srv, _ = server_mod
        self._install_immediately_empty_queue(srv, monkeypatch)
        handler = self._make_sse_handler(srv)

        class _FakeWfile:
            def write(self, data):
                raise ConnectionAbortedError("simulated")

            def flush(self):
                pass

        handler.wfile = _FakeWfile()

        handler._handle_sse()

        assert srv._sessions == {}


class TestMCPServerHandleError:
    def _trigger_handle_error(self, srv, exc_type):
        server = srv._MCPServer.__new__(srv._MCPServer)
        try:
            raise exc_type("simulated")
        except exc_type:
            server.handle_error(request=None, client_address=("127.0.0.1", 1))
        return server

    def test_swallows_benign_connection_errors_silently(self, server_mod, monkeypatch):
        srv, _ = server_mod
        called = []
        monkeypatch.setattr(
            srv.http.server.HTTPServer, "handle_error", lambda self, *a: called.append(True)
        )

        for exc_type in (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self._trigger_handle_error(srv, exc_type)

        assert called == []

    def test_delegates_unexpected_errors_to_default_handling(self, server_mod, monkeypatch):
        srv, _ = server_mod
        called = []
        monkeypatch.setattr(
            srv.http.server.HTTPServer, "handle_error", lambda self, *a: called.append(True)
        )

        self._trigger_handle_error(srv, ValueError)

        assert called == [True]
