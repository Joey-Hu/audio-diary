import os
from typing import Optional

from faster_whisper import WhisperModel

_model_cache: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    global _model_cache
    if _model_cache is None:
        model_size = os.getenv("WHISPER_MODEL", "tiny")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        _model_cache = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model_cache


def transcribe_audio(file_path: str) -> str:
    model = get_model()
    segments, info = model.transcribe(file_path, vad_filter=True)
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text)
    return " ".join(text_parts).strip()
