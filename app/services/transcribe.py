import os
import subprocess
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

_model_cache: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    global _model_cache
    if _model_cache is None:
        model_size = os.getenv("WHISPER_MODEL", "tiny")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        try:
            _model_cache = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception:
            # 回退策略：CPU 优先 float32；CUDA 优先 float16
            fallback = "float16" if device == "cuda" else "float32"
            _model_cache = WhisperModel(model_size, device=device, compute_type=fallback)
    return _model_cache


def _ffmpeg_preprocess(input_path: str, work_dir: str) -> str:
    """使用 ffmpeg 将音频转为 16kHz 单声道 wav，输出到 work_dir 中，避免污染 uploads 列表。"""
    in_p = Path(input_path)
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    out_p = work / f"{in_p.stem}.proc.wav"

    cmd = [
        "ffmpeg", "-y", "-i", str(in_p),
        "-ac", "1", "-ar", "16000", "-f", "wav", str(out_p)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return str(out_p)
    except Exception:
        # 如果 ffmpeg 不可用或转码失败，则继续用原始文件
        return input_path


def transcribe_audio(file_path: str, work_dir: str = "data/processed") -> str:
    processed_path = _ffmpeg_preprocess(file_path, work_dir=work_dir)
    model = get_model()
    try:
        segments, info = model.transcribe(processed_path, vad_filter=True)
        text_parts = []
        for segment in segments:
            if segment and segment.text:
                text_parts.append(segment.text)
        text = " ".join(text_parts).strip()
        if not text:
            raise RuntimeError("未能从音频中获取有效文本，可能为静音或解码失败。")
        return text
    finally:
        # 清理临时文件（仅当确实生成了 proc 文件且不等于原始文件）
        try:
            if processed_path != file_path and processed_path.endswith(".proc.wav"):
                Path(processed_path).unlink(missing_ok=True)
        except Exception:
            pass
