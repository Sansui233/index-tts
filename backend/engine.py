"""Lazy inference adapters; this module never imports Gradio."""

import gc
import subprocess
from threading import RLock
from .config import ROOT


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
            gc.collect()
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self.state, self.error = "unloaded", None
            return self.status()

    def infer(self, source, text, output, settings, progress):
        with self.lock:
            self.load(progress)
            options = dict(settings)
            # Existing/migrated JSON may encode whole-number floats as integers.
            # Transformers 4.36 requires float types for penalty parameters.
            for name in (
                "top_p",
                "temperature",
                "length_penalty",
                "repetition_penalty",
            ):
                options[name] = float(options[name])
            mode = options.pop("mode")
            if options["top_k"] == 0:
                options["top_k"] = None
            if mode == "normal":
                options.pop("sentences_bucket_max_size", None)
            self.tts.gr_progress = progress
            try:
                method = self.tts.infer_fast if mode == "fast" else self.tts.infer
                method(str(source), text, str(output), **options)
            finally:
                self.tts.gr_progress = None

    def subtitles(self, source, output, model, language, progress):
        # Same worker as TTS: do not keep both models on the GPU.
        self.unload()
        path = ROOT / "checkpoints/whisper" / f"whisper-{model}"
        if not (path / "config.json").exists():
            raise ValueError(f"缺少本地 Whisper 模型：{path}")
        from transformers import pipeline
        from opencc import OpenCC
        import torch

        temporary = output.with_suffix(".input.wav")
        recognizer = None
        try:
            progress(0.1, "转换音频")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(temporary),
                ],
                check=True,
                capture_output=True,
            )
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
            convert = OpenCC("t2s")
            lines = []

            def stamp(value):
                ms = max(0, round(float(value) * 1000))
                return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

            chunks = result["chunks"]
            import wave

            with wave.open(str(temporary), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
            for index, chunk in enumerate(chunks):
                start, end = chunk["timestamp"]
                start = start if start is not None else 0
                end = end if end is not None else duration
                lines.append(
                    f"{index + 1}\n{stamp(start)} --> {stamp(end)}\n{convert.convert(chunk['text'].strip())}\n"
                )
            output.write_text("\n".join(lines), encoding="utf-8")
        finally:
            temporary.unlink(missing_ok=True)
            del recognizer
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
