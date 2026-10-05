"""Roles (name, tags, reference audio set) and multi-speaker presets."""


class Library:
    def __init__(self, store, audio):
        self.store, self.audio = store, audio

    def bindings_of(self, role_id):
        for entry in self.store.list("sessions") + self.store.list("presets"):
            for binding in entry["bindings"]:
                if binding.get("role_id") == role_id:
                    yield binding

    def validate_bindings(self, bindings):
        names = [b.speaker for b in bindings]
        if len(names) != len(set(names)):
            raise ValueError("说话人名称不能重复")
        for binding in bindings:
            if binding.role_id:
                role = self.store.get("roles", binding.role_id)
                if binding.audio_id and binding.audio_id not in role["audio_ids"]:
                    raise ValueError("参考音频不属于所选角色")
            if binding.audio_id:
                self.audio.path(binding.audio_id)

    def save_role(self, request, key=None):
        with self.store.lock:
            for audio_id in request.audio_ids:
                self.audio.path(audio_id)
            if key is None:
                return self.store.create("roles", request.model_dump())
            removed = set(self.store.get("roles", key)["audio_ids"]) - set(request.audio_ids)
            if any(b.get("audio_id") in removed for b in self.bindings_of(key)):
                raise ValueError("音频仍被 session 或预设引用，请先更换绑定")
            return self.store.update("roles", key, request.model_dump())

    def delete_role(self, key):
        with self.store.lock:
            if any(True for _ in self.bindings_of(key)):
                raise ValueError("角色仍被 session 或预设引用")
            self.store.delete("roles", key)

    def save_preset(self, request, key=None):
        with self.store.lock:
            self.validate_bindings(request.bindings)
            if key is None:
                return self.store.create("presets", request.model_dump())
            return self.store.update("presets", key, request.model_dump())
