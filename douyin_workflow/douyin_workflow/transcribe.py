"""FunASR 中文转写。模型只加载一次，常驻在 MCP 进程里。

注意：MCP 走 stdio，FunASR/modelscope 会往 stdout print，必须重定向到 stderr，
否则会把 JSON-RPC 流打坏。
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path

log = logging.getLogger(__name__)

_MODEL_KWARGS = {
    "paraformer-zh": dict(model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc"),
    "SenseVoiceSmall": dict(
        model="iic/SenseVoiceSmall", vad_model="fsmn-vad", vad_kwargs={"max_single_segment_time": 30000}
    ),
}

_models: dict[tuple[str, str], object] = {}
_lock = threading.Lock()


class TranscribeError(RuntimeError):
    pass


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except ImportError:
        pass
    return "cpu"


def extract_audio(video: Path, wav: Path) -> Path:
    """转成 16kHz 单声道 wav，FunASR 的标准输入。"""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise TranscribeError("找不到 ffmpeg，请先安装并加入 PATH")
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not wav.exists():
        raise TranscribeError(f"ffmpeg 抽音频失败：{proc.stderr.strip()[-300:]}")
    return wav


def _load(model_name: str, device: str):
    key = (model_name, device)
    with _lock:
        if key not in _models:
            if model_name not in _MODEL_KWARGS:
                raise TranscribeError(f"不支持的模型 {model_name}，可选 {list(_MODEL_KWARGS)}")
            try:
                from funasr import AutoModel
            except ImportError as e:
                raise TranscribeError("未安装 funasr（pip install funasr modelscope torch torchaudio）") from e
            log.info("加载 FunASR 模型 %s @ %s（首次会下载模型）", model_name, device)
            with contextlib.redirect_stdout(sys.stderr):
                _models[key] = AutoModel(
                    **_MODEL_KWARGS[model_name], device=device, disable_update=True, disable_pbar=True
                )
        return _models[key]


def transcribe(wav: Path, model_name: str = "paraformer-zh", device: str = "auto") -> str:
    device = resolve_device(device)
    model = _load(model_name, device)
    # 同一个模型不并发推理，GPU 显存也扛不住
    with _lock, contextlib.redirect_stdout(sys.stderr):
        if model_name == "SenseVoiceSmall":
            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            res = model.generate(
                input=str(wav), language="zh", use_itn=True, batch_size_s=60, merge_vad=True, merge_length_s=15
            )
            text = "".join(rich_transcription_postprocess(r["text"]) for r in res)
        else:
            res = model.generate(input=str(wav), batch_size_s=300)
            text = "".join(r.get("text", "") for r in res)
    return text.strip()
