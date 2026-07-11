import json
from pathlib import Path
import pytest
import client_setup


class TestSseUrl:
    def test_builds_localhost_url_from_port(self):
        assert client_setup.sse_url(8766) == "http://127.0.0.1:8766/sse"

    def test_reflects_custom_port(self):
        assert client_setup.sse_url(9999) == "http://127.0.0.1:9999/sse"


class TestClaudeCodeCommand:
    def test_includes_transport_flag_and_current_port(self):
        cmd = client_setup.claude_code_command(9999)
        assert cmd == "claude mcp add anki --transport sse http://127.0.0.1:9999/sse"


class TestClaudeDesktopManualConfig:
    def test_produces_json_with_mcp_remote_bridge_and_current_port(self):
        text = client_setup.claude_desktop_manual_config(9999)
        parsed = json.loads(text)
        assert parsed == {
            "mcpServers": {
                "anki": {
                    "command": "npx",
                    "args": ["-y", "mcp-remote", "http://127.0.0.1:9999/sse"],
                }
            }
        }


class TestBundledMcpbPath:
    def test_resolves_next_to_this_module(self):
        path = client_setup.bundled_mcpb_path()
        assert path.parent == Path(client_setup.__file__).resolve().parent
        assert path.name == "desktop-extension.mcpb"


class TestExportMcpb:
    def test_copies_bundled_asset_bytes_to_destination(self, tmp_path, monkeypatch):
        source = tmp_path / "source.mcpb"
        source.write_bytes(b"fake mcpb contents")
        monkeypatch.setattr(client_setup, "bundled_mcpb_path", lambda: source)

        dest = tmp_path / "out" / "anki-mcp.mcpb"
        dest.parent.mkdir()
        client_setup.export_mcpb(str(dest))

        assert dest.read_bytes() == b"fake mcpb contents"

    def test_propagates_oserror_when_bundled_asset_missing(self, tmp_path, monkeypatch):
        missing = tmp_path / "does-not-exist.mcpb"
        monkeypatch.setattr(client_setup, "bundled_mcpb_path", lambda: missing)

        with pytest.raises(OSError):
            client_setup.export_mcpb(str(tmp_path / "out.mcpb"))


class TestBundledAssetIsCommitted:
    def test_real_desktop_extension_mcpb_exists_and_is_nonempty(self):
        path = client_setup.bundled_mcpb_path()
        assert path.exists(), "desktop-extension.mcpb must stay tracked in git (see .gitignore exception)"
        assert path.stat().st_size > 0
