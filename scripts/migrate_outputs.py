"""One-time, repeatable copy migration. Never modifies the source outputs tree."""

import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from backend.audio import Audio
from backend.config import DATA, ROOT, AUDIO_EXTENSIONS
from backend.schemas import Generation
from backend.sessions import Sessions
from backend.storage import Store, uid


class Idle:
    def busy(self, ids):
        return False


def migrate(root=ROOT, destination=DATA):
    store = Store(destination)
    audio = Audio(store)
    sessions = Sessions(store, Idle(), audio)
    source = root / "outputs"
    report_path = store.path("migrations/outputs.json")
    report = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.exists()
        else {
            "sessions": {},
            "presets": {},
            "resources": {},
            "missing": [],
            "defaults": [],
            "duplicates": [],
            "invalid": [],
        }
    )
    by_filename = defaultdict(list)
    for path in source.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            by_filename[path.name.casefold()].append(path)
    sample_root = (root / "samples").resolve()
    samples = (
        sorted(
            (
                p
                for p in sample_root.rglob("*")
                if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
            ),
            key=lambda p: str(p).casefold(),
        )
        if sample_root.exists()
        else []
    )
    roles = {r["name"]: r for r in store.list("roles")}
    projects = {p["name"]: p for p in store.list("projects")}
    default_settings = Generation().model_dump()

    def persist():
        store.write_json(report_path, report)

    def import_reference(path):
        key = str(path.resolve())
        if key not in report["resources"]:
            report["resources"][key] = audio.register(path, copy=True)["id"]
            persist()
        return report["resources"][key]

    def role_for(name, preferred=None):
        if name in roles:
            return roles[name]
        reference = preferred if preferred and preferred.is_file() else None
        if reference is None:
            matching = [p for p in samples if name in p.parts or p.stem == name]
            reference = matching[0] if matching else samples[0] if samples else None
            report["defaults"].append(
                {
                    "role": name,
                    "reference": str(reference) if reference else None,
                    "review_required": True,
                }
            )
        record = store.create(
            "roles",
            {
                "name": name,
                "tags": ["待核验"]
                if preferred is None or not preferred.is_file()
                else [],
                "audio_ids": [import_reference(reference)] if reference else [],
            },
        )
        roles[name] = record
        return record

    # Convert old presets once, retaining actual per-preset reference choices.
    for path in sorted((root / "webui2/presets/multi_dialog").glob("*.json")):
        relative = path.relative_to(root).as_posix()
        if relative in report["presets"]:
            continue
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        speakers = payload.get("speakers", {})
        bindings = []
        for field, name in speakers.items():
            if not field.endswith("_name") or not name:
                continue
            raw = speakers.get(field.replace("_name", "_audio"))
            preferred = (root / raw).resolve() if raw else None
            if preferred and not preferred.is_relative_to(sample_root):
                preferred = None
            role = role_for(name, preferred)
            selected = (
                import_reference(preferred)
                if preferred and preferred.is_file()
                else next(iter(role["audio_ids"]), None)
            )
            if selected and selected not in role["audio_ids"]:
                role["audio_ids"].append(selected)
                store.save("roles", role)
            bindings.append(
                {"speaker": name, "role_id": role["id"], "audio_id": selected}
            )
        settings = {
            **default_settings,
            **{
                k: v
                for k, v in payload.get("advanced_params", {}).items()
                if k in default_settings
            },
        }
        try:
            settings = Generation(**settings).model_dump()
        except ValueError:
            settings = default_settings
        preset = store.create(
            "presets", {"name": path.stem, "bindings": bindings, "generation": settings}
        )
        report["presets"][relative] = preset["id"]
        store.write_json(f"migrations/source-presets/{path.name}", payload)
        persist()

    candidates = sorted(
        source.rglob("*.json"), key=lambda p: ("temp_dialog" in p.parts, str(p))
    )
    fingerprints = {}
    for old_path, info in report["sessions"].items():
        fingerprints[info["fingerprint"]] = info["id"]
    for path in candidates:
        relative = path.relative_to(source).as_posix()
        if relative in report["sessions"]:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError):
            report["invalid"].append(relative)
            continue
        if (
            not isinstance(payload, list)
            or not payload
            or not all(
                isinstance(x, dict) and "text" in x and "audio_path" in x
                for x in payload
            )
        ):
            continue
        fingerprint = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        if fingerprint in fingerprints:
            report["sessions"][relative] = {
                "id": fingerprints[fingerprint],
                "fingerprint": fingerprint,
            }
            report["duplicates"].append(relative)
            persist()
            continue
        group = path.parent.name if "temp_dialog" not in path.parts else "迁移项目"
        if group not in projects:
            projects[group] = store.create("projects", {"name": group})
        name = path.parent.name if path.name == "temp_list.json" else path.stem
        record = sessions.create(
            {
                "name": name,
                "project_id": projects[group]["id"],
                "bindings": [],
                "generation": default_settings,
                "interval": 0.5,
            }
        )
        stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        record["created_at"] = stamp
        record["migration"] = {
            "source": relative,
            "source_modified_at": stamp,
            "review_required": True,
        }
        speakers = set()
        for position, item in enumerate(payload):
            match = re.match(r"^\s*\[([^\]]+)\]\s*(.*)$", item["text"], re.S)
            speaker, text = (
                (match[1].strip(), match[2].strip())
                if match
                else ("旁白", item["text"])
            )
            role = role_for(speaker)
            binding = {
                "speaker": speaker,
                "role_id": role["id"],
                "audio_id": next(iter(role["audio_ids"]), None),
            }
            if speaker not in speakers:
                record["bindings"].append(binding)
                speakers.add(speaker)
            line = sessions.add_line(record, {"speaker": speaker, "text": text})
            raw = item.get("audio_path") or ""
            original = (root / raw).resolve() if raw else None
            found = (
                original
                if original
                and original.is_relative_to(source.resolve())
                and original.is_file()
                else None
            )
            if found is None and raw:
                basename = Path(raw.replace("\\", "/")).name
                local = path.parent / basename
                found = local if local.is_file() else None
                if found is None:
                    matches = by_filename[basename.casefold()]
                    found = matches[0] if len(matches) == 1 else None
            take = {
                "id": uid(),
                "take_index": 1,
                "created_at": stamp,
                "audio_id": None,
                "snapshot": {
                    "text": text,
                    "speaker": speaker,
                    "audio_id": binding["audio_id"],
                    "generation": default_settings,
                },
                "source_audio_path": raw,
            }
            if found:
                target = store.path(
                    f"projects/{record['project_id']}/sessions/{record['id']}/takes/{line['id']}/1_{take['id']}{found.suffix.lower()}"
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(found, target)
                take["audio_id"] = audio.register(target, f"{name} #{position} Take 1")[
                    "id"
                ]
            else:
                take["missing"] = True
                report["missing"].append(
                    {"session": relative, "index": position, "path": raw}
                )
            line.update(takes=[take], current_take_id=take["id"], next_take_index=2)
        sessions.save(record)
        store.write_json(f"migrations/source-outputs/{relative}", payload)
        report["sessions"][relative] = {"id": record["id"], "fingerprint": fingerprint}
        fingerprints[fingerprint] = record["id"]
        persist()
    persist()
    summary = {
        "sessions": len({s["id"] for s in report["sessions"].values()}),
        "source_files": len(report["sessions"]),
        "presets": len(report["presets"]),
        "missing_audio": len(report["missing"]),
        "default_bindings": len(report["defaults"]),
        "duplicates": len(report["duplicates"]),
        "report": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    migrate()
