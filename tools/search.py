def quote_deck(name: str) -> str:
    """Quote a deck name for Anki's search syntax, escaping embedded quotes/backslashes."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
