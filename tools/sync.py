from aqt import mw


def sync() -> dict:
    if hasattr(mw, "sync_collection_and_media"):
        mw.sync_collection_and_media(on_done=lambda future: None)
    elif hasattr(mw, "on_sync_button_clicked"):
        mw.on_sync_button_clicked()
    else:
        raise RuntimeError("No sync method available in this Anki version")
    return {"status": "sync triggered"}
