from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, validate_default=True
    )


class Named(Input):
    name: str = Field(min_length=1, max_length=200)


class Role(Named):
    tags: list[str] = Field(default_factory=list)
    audio_ids: list[str] = Field(default_factory=list)


class Binding(Input):
    speaker: str = Field(min_length=1)
    role_id: str | None = None
    audio_id: str | None = None


class Generation(Input):
    mode: Literal["normal", "fast"] = "normal"
    do_sample: bool = True
    top_p: float = Field(default=0.8, gt=0, le=1)
    top_k: int = Field(default=30, ge=0)
    temperature: float = Field(default=1, gt=0, le=5)
    length_penalty: float = Field(default=0, ge=-10, le=10)
    num_beams: int = Field(default=3, ge=1, le=10)
    repetition_penalty: float = Field(default=10, gt=0, le=30)
    max_mel_tokens: int = Field(default=600, ge=10, le=3000)
    max_text_tokens_per_sentence: int = Field(default=120, ge=10, le=500)
    sentences_bucket_max_size: int = Field(default=4, ge=1, le=16)


class Preset(Named):
    bindings: list[Binding] = Field(default_factory=list)
    generation: Generation = Field(default_factory=Generation)


class SessionInput(Preset):
    project_id: str
    interval: float = Field(default=0.5, ge=0, le=30)


class TextInput(Input):
    text: str = Field(max_length=1000000)


class LineInput(Input):
    text: str = Field(min_length=1, max_length=20000)
    speaker: str = Field(min_length=1, max_length=200)


class Speech(Input):
    text: str = Field(min_length=1, max_length=20000)
    audio_id: str
    generation: Generation = Field(default_factory=Generation)


class Subtitle(Input):
    audio_id: str
    model: Literal["tiny", "base", "small", "medium"] = "base"
    language: str = Field(default="zh", min_length=2, max_length=30)


class Selection(Input):
    take_id: str


class Source(Input):
    path: str


class Order(Input):
    line_ids: list[str]
