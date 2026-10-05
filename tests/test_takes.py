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
            "PUT", self.base + "/text", {"text": "[A] Hello\n[A] World"}
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

    def test_reference_protects_unused_take(self):
        first = self.generate()
        old_audio = first["takes"][0]["audio_id"]
        self.generate()
        self.request("POST", "/roles", {"name": "reference", "audio_ids": [old_audio]})
        result = self.request("POST", self.linebase + "/takes/cleanup")
        self.assertEqual(result["deleted"], 0)
        self.assertEqual(len(result["failures"]), 1)


if __name__ == "__main__":
    unittest.main()
