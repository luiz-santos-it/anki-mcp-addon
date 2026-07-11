"""Build the .ankiaddon zip for AnkiWeb submission (flat layout, no wrapping folder)."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "anki-mcp.ankiaddon"
FILES = [
    "__init__.py",
    "client_setup.py",
    "config.json",
    "config_ui.py",
    "desktop-extension.mcpb",
    "manifest.json",
    "protocol.py",
    "server.py",
    "tools/__init__.py",
    "tools/decks.py",
    "tools/insights.py",
    "tools/notes.py",
    "tools/search.py",
    "tools/study.py",
    "tools/sync.py",
]


def main() -> None:
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in FILES:
            zf.write(ROOT / rel, rel)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
