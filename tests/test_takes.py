import tempfile
import time
import unittest
import wave
from unittest.mock import patch
from pathlib import Path
from threading import Event
from fastapi.testclient import TestClient
from backend.app import create_app


class FakeEngine:
    def __init__(self):
        self.loaded = False
        self.loads = 0
        self.fail = False
        self.wait = None

    def status(self):
        return {"state": "loaded" if self.loaded else "unloaded"}

    def load(self, progress):
        if not self.loaded:
            self.loads += 1
            self.loaded = True
        return self.status()

    def unload(self, progress=None):
        self.loaded = False
        return self.status()

    def infer(self, source, text, path, settings, progress):
        self.load(progress)
        if self.wait:
            self.wait.wait(5)
        if self.fail:
            raise ValueError("test failure")
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b"\0\0" * 240)


class TakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = FakeEngine()
        self.app = create_app(Path(self.temp.name), self.engine)
        self.client = TestClient(self.app).__enter__()
        self.project = self.request("POST", "/projects", {"name": "test"})
        self.audio = self.client.post(
            "/api/audio/upload",
            files={"file": ("reference.wav", b"reference", "audio/wav")},
        ).json()
        self.session = self.request(
            "POST",
            "/sessions",
            {
                "name": "chapter",
                "project_id": self.project["id"],
                "bindings": [{"speaker": "A", "audio_id": self.audio["id"]}],
            },
        )
        self.base = "/sessions/" + self.session["id"]
        self.session = self.request(
            "PUT",
            self.base + "/script",
            {"lines": [{"speaker": "A", "text": "Hello"}, {"speaker": "A", "text": "World"}]},
        )
        self.line = self.session["lines"][0]
        self.linebase = self.base + "/lines/" + self.line["id"]

    def tearDown(self):
        if self.engine.wait:
            self.engine.wait.set()
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def request(self, method, path, body=None):
        response = self.client.request(method, "/api" + path, json=body)
        self.assertLess(response.status_code, 300, response.text)
        return response.json()

    def finish(self, task):
        for _ in range(200):
            value = self.request("GET", "/tasks/" + task["id"])
            if value["status"] not in {"running", "queued"}:
                return value
            time.sleep(0.01)
        self.fail("task timeout")

    def generate(self, path=None):
        task = self.request("POST", (path or self.linebase) + "/generate")
        self.assertEqual(self.finish(task)["status"], "succeeded")
        return self.request("GET", self.base)["lines"][0]

    def test_history_selection_three_cleanup_scopes_and_monotonic_index(self):
        for scope in (self.linebase, self.base, "/projects/" + self.project["id"]):
            first = self.generate()
            chosen = first["current_take_id"]
            second = self.generate()
            self.request("PUT", self.linebase + "/current-take", {"take_id": chosen})
            maximum = second["next_take_index"]
            result = self.request("POST", scope + "/takes/cleanup")
            self.assertGreaterEqual(result["deleted"], 1)
            line = self.request("GET", self.base)["lines"][0]
            self.assertEqual(line["current_take_id"], chosen)
            self.assertEqual(len(line["takes"]), 1)
            self.assertEqual(line["next_take_index"], maximum)
        self.assertEqual(self.engine.loads, 1)

    def test_failure_keeps_current_and_next_task_runs(self):
        first = self.generate()
        self.engine.fail = True
        result = self.finish(self.request("POST", self.linebase + "/generate"))
        self.assertEqual(result["status"], "failed")
        line = self.request("GET", self.base)["lines"][0]
        self.assertEqual(line["current_take_id"], first["current_take_id"])
        self.engine.fail = False
        self.assertEqual(self.generate()["takes"][-1]["take_index"], 3)

    def test_cleanup_busy_and_edit_during_generation(self):
        first = self.generate()
        self.engine.wait = Event()
        task = self.request("POST", self.linebase + "/generate")
        for _ in range(100):
            if self.request("GET", "/tasks/" + task["id"])["status"] == "running":
                break
            time.sleep(0.01)
        self.assertEqual(
            self.client.post("/api" + self.base + "/takes/cleanup").status_code, 409
        )
        self.request("PUT", self.linebase, {"speaker": "A", "text": "changed"})
        self.engine.wait.set()
        self.finish(task)
        line = self.request("GET", self.base)["lines"][0]
        self.assertEqual(line["current_take_id"], first["current_take_id"])

    def test_path_traversal_and_input_validation(self):
        self.assertEqual(
            self.client.post(
                "/api/audio/import", json={"path": "../../AGENTS.md"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/speech",
                json={
                    "text": "hello",
                    "audio_id": self.audio["id"],
                    "generation": {"top_p": 20},
                },
            ).status_code,
            422,
        )

    def test_cleanup_file_failure_retains_index_for_retry(self):
        first = self.generate()
        old_id = first["takes"][0]["audio_id"]
        self.generate()
        record = self.app.state.store.get("audio", old_id)
        target = self.app.state.store.path(record["path"])
        original = Path.unlink

        def fail_one(path, *args, **kwargs):
            if path == target:
                raise PermissionError("file busy")
            return original(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_one):
            result = self.request("POST", self.linebase + "/takes/cleanup")
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(len(self.request("GET", self.base)["lines"][0]["takes"]), 2)
        self.assertEqual(
            self.request("POST", self.linebase + "/takes/cleanup")["deleted"], 1
        )

    def test_move_session_then_delete_project(self):
        line = self.generate()
        store = self.app.state.store
        audio_id = line["takes"][0]["audio_id"]
        other = self.request("POST", "/projects", {"name": "other"})
        body = {k: self.session[k] for k in ("name", "bindings", "generation", "interval")}
        self.request("PUT", self.base, {**body, "project_id": other["id"]})
        moved = store.path(store.get("audio", audio_id)["path"])
        self.assertTrue(moved.is_relative_to(store.path(f"projects/{other['id']}")))
        self.assertTrue(moved.exists())
        self.request("DELETE", "/projects/" + other["id"])
        self.assertFalse(moved.exists())
        self.assertEqual(self.client.get("/api" + self.base).status_code, 404)

    def test_script_keeps_modifies_adds_and_removes(self):
        line = self.generate()
        world = self.request("GET", self.base)["lines"][1]
        script = [
            {"line_id": world["id"], "speaker": "A", "text": "World"},
            {"line_id": line["id"], "speaker": "A", "text": "Hello!"},
            {"speaker": "A", "text": "New"},
        ]
        lines = self.request("PUT", self.base + "/script", {"lines": script})["lines"]
        self.assertEqual([l["index"] for l in lines], [1, 0, 2])
        self.assertEqual(lines[1]["takes"], line["takes"])
        self.assertEqual(lines[1]["revision"], line["revision"] + 1)
        self.assertEqual(lines[0]["revision"], world["revision"])
        # Removing a line keeps its take files until orphan cleanup.
        kept = [{"line_id": l["id"], "speaker": l["speaker"], "text": l["text"]} for l in lines[1:]]
        lines = self.request("PUT", self.base + "/script", {"lines": kept})["lines"]
        self.assertEqual([l["index"] for l in lines], [0, 2])
        added = self.request("PUT", self.base + "/script", {"lines": [*kept, {"speaker": "A", "text": "Later"}]})
        self.assertEqual(added["lines"][-1]["index"], 3)
        response = self.client.put("/api" + self.base + "/script", json={"lines": [kept[0], kept[0]]})
        self.assertEqual(response.status_code, 400)

    def test_orphan_cleanup_modes(self):
        self.generate()
        line = self.generate()
        store = self.app.state.store
        files = [store.path(store.get("audio", t["audio_id"])["path"]) for t in line["takes"]]
        other = self.request("GET", self.base)["lines"][1]
        self.generate(self.base + "/lines/" + other["id"])
        self.generate(self.base + "/lines/" + other["id"])
        script = [{"line_id": other["id"], "speaker": "A", "text": "World"}]
        self.request("PUT", self.base + "/script", {"lines": script})
        self.assertTrue(all(f.exists() for f in files))
        result = self.request("POST", self.base + "/takes/cleanup?mode=orphans")
        self.assertEqual((result["deleted"], result["failures"]), (2, []))
        self.assertFalse(files[0].parent.exists())
        records = {r["path"] for r in store.list("audio")}
        self.assertFalse({store.relative(f) for f in files} & records)
        # The remaining line's unused take is untouched until the "all" mode.
        self.assertEqual(len(self.request("GET", self.base)["lines"][0]["takes"]), 2)
        result = self.request("POST", self.base + "/takes/cleanup?mode=all")
        self.assertEqual(result["deleted"], 1)

    def test_generated_audio_has_display_name_and_real_download_name(self):
        self.generate()
        self.generate(self.base + "/lines/" + self.request("GET", self.base)["lines"][1]["id"])
        task = self.finish(self.request("POST", self.base + "/merge"))
        record = task["result"]
        self.assertEqual(record["name"], "chapter")
        response = self.client.get(f"/api/audio/{record['id']}/file?download=true")
        self.assertIn("chapter.wav", response.headers["content-disposition"])

    def test_selected_lines_download_cleanup_delete(self):
        import io, zipfile

        self.generate()
        line = self.generate()
        other = self.request("GET", self.base)["lines"][1]
        body = {"ids": [line["id"], other["id"]]}
        # Only lines with a current take go into the zip, in session order.
        response = self.client.post("/api" + self.base + "/lines/download", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("chapter.zip", response.headers["content-disposition"])
        names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
        self.assertEqual(names, ["001 #0 A Hello.wav"])
        self.assertEqual(self.request("POST", self.base + "/lines/takes/cleanup", body)["deleted"], 1)
        store = self.app.state.store
        current = store.path(store.get("audio", self.request("GET", self.base)["lines"][0]["takes"][0]["audio_id"])["path"])
        lines = self.request("POST", self.base + "/lines/delete", body)["lines"]
        self.assertEqual(lines, [])
        self.assertFalse(current.exists())

    def test_reference_protects_unused_take(self):
        first = self.generate()
        old_audio = first["takes"][0]["audio_id"]
        self.generate()
        self.request("POST", "/presets", {"name": "reference", "bindings": [{"speaker": "x", "audio_id": old_audio}]})
        result = self.request("POST", self.linebase + "/takes/cleanup")
        self.assertEqual(result["deleted"], 0)
        self.assertEqual(len(result["failures"]), 1)


if __name__ == "__main__":
    unittest.main()
