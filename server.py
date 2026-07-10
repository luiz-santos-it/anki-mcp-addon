import concurrent.futures
import http.server
import json
import queue
import threading
import uuid
from urllib.parse import parse_qs, urlparse

# session_id -> queue.Queue[str | None]
_sessions: dict = {}
_sessions_lock = threading.Lock()

_server: http.server.ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None

_MAX_BODY_BYTES = 10 * 1024 * 1024

# Assume taskman won't ever run the task (e.g. it's a mock) past this long.
_MAIN_THREAD_TIMEOUT = 30


class _MCPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        pass

    def do_OPTIONS(self):
        self.send_error(403)

    def do_GET(self):
        if self._is_browser_request():
            self.send_error(403)
            return
        if urlparse(self.path).path == "/sse":
            self._handle_sse()
        else:
            self.send_error(404)

    def do_POST(self):
        if self._is_browser_request():
            self.send_error(403)
            return
        if urlparse(self.path).path == "/messages":
            self._handle_post()
        else:
            self.send_error(404)

    def _is_browser_request(self) -> bool:
        # Native/CLI MCP clients never send Origin; only browsers do.
        return self.headers.get("Origin") is not None

    def _handle_sse(self):
        session_id = str(uuid.uuid4())
        q: queue.Queue = queue.Queue()
        with _sessions_lock:
            _sessions[session_id] = q

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        self._sse_event("endpoint", f"/messages?sessionId={session_id}")

        try:
            while True:
                try:
                    data = q.get(timeout=25)
                    if data is None:
                        break
                    self._sse_event("message", data)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with _sessions_lock:
                _sessions.pop(session_id, None)

    def _sse_event(self, event: str, data: str):
        self.wfile.write(f"event: {event}\ndata: {data}\n\n".encode())
        self.wfile.flush()

    def _handle_post(self):
        qs = parse_qs(urlparse(self.path).query)
        session_id = (qs.get("sessionId") or [None])[0]

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.send_error(400)
            return
        if length < 0 or length > _MAX_BODY_BYTES:
            self.send_error(413)
            return
        body = self.rfile.read(length)

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

        threading.Thread(
            target=_dispatch,
            args=(session_id, body),
            daemon=True,
        ).start()


def _dispatch(session_id: str, body: bytes):
    from . import protocol  # late import avoids circular dep at module load

    try:
        req = json.loads(body)
    except json.JSONDecodeError:
        return

    # Run on the Qt main thread so tools can safely call mw.col.
    from aqt import mw
    fut: concurrent.futures.Future = concurrent.futures.Future()

    def _run():
        try:
            fut.set_result(protocol.handle_request(req))
        except Exception as exc:
            fut.set_exception(exc)

    mw.taskman.run_on_main(_run)
    try:
        response = fut.result(timeout=_MAIN_THREAD_TIMEOUT)
    except concurrent.futures.TimeoutError:
        # _run never ran on the main thread; safe to run inline instead.
        response = protocol.handle_request(req)

    if response is None:
        return

    with _sessions_lock:
        q = _sessions.get(session_id)
    if q is not None:
        q.put(json.dumps(response))


def start(port: int = 8766) -> bool:
    """Start the server. Returns False (without raising) if the port is taken."""
    global _server, _server_thread
    if _server is not None:
        return True
    try:
        _server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _MCPHandler)
    except OSError:
        _server = None
        return False
    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()
    return True


def is_running() -> bool:
    return _server is not None


def stop():
    global _server, _server_thread
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None
        _server_thread = None
