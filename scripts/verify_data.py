"""Read-only verification of migrated indexes and source JSON snapshots."""

import json
from backend.config import DATA, ROOT
from backend.storage import Store


def verify():
    store = Store(DATA)
    report = json.loads(
        store.path("migrations/outputs.json").read_text(encoding="utf-8")
    )
    failures = []
    takes = 0
    for source, entry in report["sessions"].items():
        original = json.loads(
            (ROOT / "outputs" / source).read_text(encoding="utf-8-sig")
        )
        snapshot_path = store.path("migrations/source-outputs/" + source)
        if snapshot_path.exists() and original != json.loads(
            snapshot_path.read_text(encoding="utf-8")
        ):
            failures.append({"source": source, "error": "源 JSON 与迁移快照不同"})
        session = store.get("sessions", entry["id"])
        indices = [line["index"] for line in session["lines"]]
        if len(indices) != len(set(indices)):
            failures.append({"source": source, "error": "重复句子 index"})
        for line in session["lines"]:
            takes += len(line["takes"])
            ids = {t["id"] for t in line["takes"]}
            if line["current_take_id"] not in ids:
                failures.append(
                    {
                        "source": source,
                        "index": line["index"],
                        "error": "当前 Take 无效",
                    }
                )
            for take in line["takes"]:
                if take.get("audio_id"):
                    resource = store.get("audio", take["audio_id"])
                    path = store.path(resource["path"])
                    if not path.is_file():
                        failures.append(
                            {
                                "source": source,
                                "index": line["index"],
                                "error": "Take 文件缺失",
                            }
                        )
    result = {
        "source_records": len(report["sessions"]),
        "takes": takes,
        "failures": failures,
    }
    store.write_json("migrations/verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    verify()
