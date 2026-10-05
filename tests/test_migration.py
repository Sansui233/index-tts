import json
import tempfile
import unittest
from pathlib import Path
from scripts.migrate_outputs import migrate
from backend.storage import Store


class MigrationTests(unittest.TestCase):
    def test_copy_defaults_and_repeat_preserves_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "outputs/temp_dialog/chapter"
            old.mkdir(parents=True)
            (old / "audio.wav").write_bytes(b"original audio")
            payload = [
                {
                    "text": "[A] Hello",
                    "audio_path": "outputs/temp_dialog/chapter/audio.wav",
                }
            ]
            source = old / "temp_list.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            before = source.read_bytes()
            data = root / "webui3/data"
            migrate(root, data)
            store = Store(data)
            records = store.list("sessions")
            self.assertEqual(len(records), 1)
            session = records[0]
            line = session["lines"][0]
            self.assertEqual(line["index"], 0)
            self.assertEqual(line["next_take_index"], 2)
            self.assertEqual(line["current_take_id"], line["takes"][0]["id"])
            resource = store.get("audio", line["takes"][0]["audio_id"])
            self.assertEqual(
                store.path(resource["path"]).read_bytes(), b"original audio"
            )
            session["name"] = "edited in UI"
            store.save("sessions", session)
            migrate(root, data)
            self.assertEqual(store.list("sessions")[0]["name"], "edited in UI")
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((old / "audio.wav").read_bytes(), b"original audio")
