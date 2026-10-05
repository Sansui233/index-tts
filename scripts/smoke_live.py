"""Create an explicit demo session and exercise real inference through the API."""

import json
import time
import wave
import io
import httpx
from backend.config import DATA


def run():
    client = httpx.Client(
        base_url="http://127.0.0.1:7863/api", timeout=30, trust_env=False
    )

    def request(method, path, body=None):
        result = client.request(method, path, json=body)
        result.raise_for_status()
        return result.json()

    def finish(task):
        for _ in range(300):
            result = request("GET", "/tasks/" + task["id"])
            if result["status"] not in {"running", "queued"}:
                if result["status"] != "succeeded":
                    raise RuntimeError(result.get("error") or result["status"])
                return result
            time.sleep(1)
        raise TimeoutError("Live inference exceeded 5 minutes")

    roles = request("GET", "/roles")
    role = next(r for r in roles if r["audio_ids"])
    project = request("POST", "/projects", {"name": "功能验证"})
    session = request(
        "POST",
        "/sessions",
        {
            "name": "Take 验证示例",
            "project_id": project["id"],
            "bindings": [
                {
                    "speaker": "测试",
                    "role_id": role["id"],
                    "audio_id": role["audio_ids"][0],
                }
            ],
            "generation": {"num_beams": 1, "max_mel_tokens": 300},
        },
    )
    base = "/sessions/" + session["id"]
    session = request(
        "PUT", base + "/text", {"text": "[测试] 你好，这是一次声音测试。"}
    )
    line_id = session["lines"][0]["id"]
    line_base = base + "/lines/" + line_id
    generated = []
    for _ in range(2):
        generated.append(finish(request("POST", line_base + "/generate"))["id"])
    session = request("GET", base)
    line = session["lines"][0]
    assert len(line["takes"]) == 2
    assert line["current_take_id"] == line["takes"][1]["id"]
    request("PUT", line_base + "/current-take", {"take_id": line["takes"][0]["id"]})
    merge = finish(request("POST", base + "/merge"))
    response = client.get("/audio/" + merge["result"]["id"] + "/file")
    response.raise_for_status()
    with wave.open(io.BytesIO(response.content), "rb") as wav:
        duration = wav.getnframes() / wav.getframerate()
        assert duration > 0
    result = {
        "project_id": project["id"],
        "session_id": session["id"],
        "generated_tasks": generated,
        "takes": 2,
        "current_take_index": 1,
        "merged_seconds": duration,
    }
    try:
        subtitle = finish(
            request(
                "POST",
                "/subtitles",
                {"audio_id": merge["result"]["id"], "model": "base", "language": "zh"},
            )
        )
        result["subtitle"] = subtitle["result"]
    except Exception as error:
        result["subtitle_error"] = str(error)
    finish(request("POST", "/models/unload"))
    result["final_model_state"] = request("GET", "/models")["state"]
    (DATA / "migrations/live-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    client.close()


if __name__ == "__main__":
    run()
