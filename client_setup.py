import json
import shutil
from pathlib import Path

_MCPB_ASSET_NAME = "desktop-extension.mcpb"


def sse_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/sse"


def claude_code_command(port: int) -> str:
    return f"claude mcp add anki --transport sse {sse_url(port)}"


def claude_desktop_manual_config(port: int) -> str:
    config = {
        "mcpServers": {
            "anki": {"command": "npx", "args": ["-y", "mcp-remote", sse_url(port)]}
        }
    }
    return json.dumps(config, indent=2)


def bundled_mcpb_path() -> Path:
    return Path(__file__).resolve().parent / _MCPB_ASSET_NAME


def export_mcpb(dest: str) -> None:
    shutil.copy(bundled_mcpb_path(), dest)
