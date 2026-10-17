import base64

from aqt import mw


def add_audio(note_id: int, field: str, audio_base64: str, filename: str) -> dict:
    note = mw.col.get_note(note_id)
    if field not in note.keys():
        raise ValueError(f"Field '{field}' not found on note {note_id}")

    data = base64.b64decode(audio_base64)
    stored_filename = mw.col.media.write_data(filename, data)
    note[field] = note[field] + f" [sound:{stored_filename}]"
    mw.col.update_note(note)
    return {"filename": stored_filename}
