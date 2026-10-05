"""Lazy inference adapters for IndexTTS and local Whisper."""

import gc
import subprocess
import wave
from threading import RLock
from .config import ROOT

WHISPER_MODELS = ("tiny", "base", "small", "medium")
# Old JSON may store whole-number floats as ints; transformers 4.36 needs floats.
FLOAT_OPTIONS = ("top_p", "temperature", "length_penalty", "repetition_penalty")


def whisper_path(model):
    return ROOT / "checkpoints/whisper" / f"whisper-{model}"


def free_cuda():
    gc.collect()
    import torch

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def srt_time(seconds):
    ms = max(0, round(float(seconds) * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def to_srt(chunks, duration):
    from opencc import OpenCC

    convert = OpenCC("t2s")
    blocks = []
    for number, chunk in enumerate(chunks, 1):
        start, end = chunk["timestamp"]
        end = duration if end is None else end
        text = convert.convert(chunk["text"].strip())
        blocks.append(f"{number}\n{srt_time(start or 0)} --> {srt_time(end)}\n{text}\n")
    return "\n".join(blocks)


class Engine:
    def __init__(self):
        self.tts = None
        self.state = "unloaded"
        self.error = None
        self.lock = RLock()

    def status(self):
        return {"state": self.state, "error": self.error}

    def load(self, progress):
        with self.lock:
            if self.tts is not None:
                return self.status()
            self.state, self.error = "loading", None
            try:
                progress(0.02, "加载 IndexTTS")
                from indextts.infer import IndexTTS

                self.tts = IndexTTS(
                    model_dir=str(ROOT / "checkpoints"),
                    cfg_path=str(ROOT / "checkpoints/config.yaml"),
                    use_cuda_kernel=False,
                )
                self.state = "loaded"
            except Exception as error:
                self.tts = None
                self.state, self.error = "error", str(error)
                raise
            return self.status()

    def unload(self, progress=None):
        with self.lock:
            self.state = "unloading"
            self.tts = None
            free_cuda()
            self.state, self.error = "unloaded", None
            return self.status()

    def infer(self, source, text, output, settings, progress):
        with self.lock:
            self.load(progress)
            options = dict(settings)
            for name in FLOAT_OPTIONS:
                options[name] = float(options[name])
            options["top_k"] = options["top_k"] or None
            fast = options.pop("mode") == "fast"
            if not fast:
                options.pop("sentences_bucket_max_size", None)
            self.tts.gr_progress = progress
            try:
                method = self.tts.infer_fast if fast else self.tts.infer
                method(str(source), text, str(output), **options)
            finally:
                self.tts.gr_progress = None

    def subtitles(self, source, output, model, language, progress):
        # Same worker as TTS: never keep both models on the GPU.
        self.unload()
        path = whisper_path(model)
        if not (path / "config.json").exists():
            raise ValueError(f"缺少本地 Whisper 模型：{path}")
        import torch
        from transformers import pipeline

        temporary = output.with_suffix(".input.wav")
        recognizer = None
        try:
            progress(0.1, "转换音频")
            command = ["ffmpeg", "-y", "-i", str(source), "-ac", "1", "-ar", "16000"]
            subprocess.run([*command, str(temporary)], check=True, capture_output=True)
            with wave.open(str(temporary), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
            progress(0.2, "加载 Whisper")
            recognizer = pipeline(
                "automatic-speech-recognition",
                model=str(path),
                device=0 if torch.cuda.is_available() else -1,
            )
            progress(0.3, "识别字幕")
            result = recognizer(
                str(temporary),
                return_timestamps=True,
                generate_kwargs={
                    "task": "transcribe",
                    "language": language,
                    "max_new_tokens": 450,
                    "num_beams": 5,
                },
                chunk_length_s=30,
                stride_length_s=[6, 3],
                batch_size=1,
            )
            output.write_text(to_srt(result["chunks"], duration), encoding="utf-8")
        finally:
            temporary.unlink(missing_ok=True)
            del recognizer
            free_cuda()
