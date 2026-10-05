"""Roles read their audio from samples/<name>/; anonymous roles accept any audio."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock
from fastapi.testclient import TestClient
from backend import audio as audio_module, library as library_module
from backend.app import create_app


class Engine:
    def status(self):
        return {"state": "unloaded", "error": None}


class RoleTest(unittest.TestCase):
    def setUp(self):
        temp = Path(tempfile.mkdtemp())
        self.samples = (temp / "samples").resolve()
        for relative in ("卡维/a.wav", "卡维/sub/b.wav", "新卡维/a.wav", "_other/x.wav"):
            (self.samples / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.samples / relative).write_bytes(relative.encode())
        for module in (audio_module, library_module):
            patch = mock.patch.object(module, "SAMPLES", self.samples)
            patch.start()
            self.addCleanup(patch.stop)
        self.client = TestClient(create_app(temp / "data", Engine()))

    def request(self, method, path, body=None, status=200):
        response = self.client.request(method, "/api" + path, json=body)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def preset(self, role, audio_id, status=200):
        binding = {"speaker": "s", "role_id": role["id"], "audio_id": audio_id}
        return self.request("POST", "/presets", {"name": "p", "bindings": [binding]}, status)

    def test_audio_comes_from_folder(self):
        role = self.request("POST", "/roles", {"name": "卡维"})
        names = [self.request("GET", f"/audio/{i}")["name"] for i in role["audio_ids"]]
        self.assertEqual(sorted(names), ["卡维/a.wav", "卡维/sub/b.wav"])
        self.assertEqual(self.request("GET", "/roles")[0]["audio_ids"], role["audio_ids"])

    def test_only_anonymous_roles_take_other_audio(self):
        other = self.request("POST", "/audio/import", {"path": "_other/x.wav"})["id"]
        role = self.request("POST", "/roles", {"name": "卡维"})
        self.preset(role, other, status=400)
        anonymous = self.request("POST", "/roles", {"name": "旁白", "anonymous": True})
        self.preset(anonymous, other)
        # Removing the mark would orphan that binding.
        self.request("PUT", f"/roles/{anonymous['id']}", {"name": "旁白"}, status=400)

    def test_rename_follows_moved_folder(self):
        role = self.request("POST", "/roles", {"name": "卡维"})
        old = next(i for i in role["audio_ids"] if self.request("GET", f"/audio/{i}")["name"] == "卡维/a.wav")
        preset = self.preset(role, old)
        # 新卡维/ lacks sub/b.wav, but only a.wav is bound.
        renamed = self.request("PUT", f"/roles/{role['id']}", {"name": "新卡维"})
        bound = self.request("GET", f"/presets/{preset['id']}")["bindings"][0]["audio_id"]
        self.assertIn(bound, renamed["audio_ids"])
        self.assertEqual(self.request("GET", f"/audio/{bound}")["name"], "新卡维/a.wav")

    def upload(self, content, name):
        response = self.client.post("/api/audio/upload", files={"file": (name, content, "audio/wav")})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_upload_never_stores_the_same_audio_twice(self):
        first = self.upload(b"same bytes", "a.wav")
        self.assertEqual(self.upload(b"same bytes", "b.wav")["id"], first["id"])
        self.assertNotEqual(self.upload(b"other bytes", "c.wav")["id"], first["id"])
        files = self.samples.parent / "data/audio/files"
        self.assertEqual(len(list(files.iterdir())), 2)
        # A file already in samples/ is referenced in place, not copied.
        known = self.upload("_other/x.wav".encode(), "copy.wav")
        self.assertEqual((known["source"], known["path"]), ("samples", "_other/x.wav"))
        self.assertEqual(len(list(files.iterdir())), 2)

    def test_rename_refuses_missing_file(self):
        role = self.request("POST", "/roles", {"name": "卡维"})
        sub = next(i for i in role["audio_ids"] if self.request("GET", f"/audio/{i}")["name"] == "卡维/sub/b.wav")
        self.preset(role, sub)
        self.request("PUT", f"/roles/{role['id']}", {"name": "新卡维"}, status=400)
        self.assertEqual(self.request("GET", "/roles")[0]["name"], "卡维")


if __name__ == "__main__":
    unittest.main()
