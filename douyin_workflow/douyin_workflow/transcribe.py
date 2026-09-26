"""FunASR 中文转写。模型只加载一次，常驻在 MCP 进程里。

注意：MCP 走 stdio，FunASR/modelscope 会往 stdout print，必须重定向到 stderr，
否则会把 JSON-RPC 流打坏。
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import wave
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
    ffmpeg = os.getenv("DOUYIN_FFMPEG") or shutil.which("ffmpeg")
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


# ---- 轻量后端：sherpa-onnx + SenseVoice int8（纯 CPU，约 230MB，不需要 torch） ----
# 小内存云服务器用这个。模型目录里要有 model.int8.onnx 和 tokens.txt。
SHERPA_MODEL = "sherpa-sensevoice"
CHUNK_S = 25.0  # SenseVoice 适合 30 s 以内的片段
SEARCH_S = 5.0  # 在每个切点前后这么多秒里找最安静的位置下刀，避免切断词


def _sherpa_recognizer():
    key = (SHERPA_MODEL, "cpu")
    with _lock:
        if key not in _models:
            try:
                import sherpa_onnx
            except ImportError as e:
                raise TranscribeError("未安装 sherpa-onnx（pip install sherpa-onnx numpy）") from e
            d = Path(os.getenv("DOUYIN_SHERPA_MODEL_DIR", "~/dy2text/models/sensevoice")).expanduser()
            model, tokens = d / "model.int8.onnx", d / "tokens.txt"
            if not (model.exists() and tokens.exists()):
                raise TranscribeError(f"找不到 SenseVoice 模型文件：{d}")
            log.info("加载 sherpa-onnx SenseVoice：%s", d)
            _models[key] = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(model),
                tokens=str(tokens),
                num_threads=int(os.getenv("DOUYIN_ASR_THREADS", "2")),
                language="zh",
                use_itn=True,
            )
        return _models[key]


def split_points(samples, sr: int = 16000, chunk_s: float = CHUNK_S, search_s: float = SEARCH_S) -> list[int]:
    """返回切点（样本下标）。每个切点取目标位置 ±search_s 内 20 ms 帧能量最低处。"""
    import numpy as np

    n = len(samples)
    frame = int(sr * 0.02)
    cuts, start = [0], 0
    while n - start > int(sr * (chunk_s + search_s)):
        lo = start + int(sr * (chunk_s - search_s))
        hi = min(start + int(sr * (chunk_s + search_s)), n - frame)
        seg = samples[lo:hi]
        k = len(seg) // frame
        energy = (seg[: k * frame].reshape(k, frame) ** 2).mean(axis=1)
        start = lo + int(np.argmin(energy)) * frame
        cuts.append(start)
    cuts.append(n)
    return cuts


def _transcribe_sherpa(wav: Path) -> str:
    import numpy as np

    with wave.open(str(wav)) as f:
        sr = f.getframerate()
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    rec = _sherpa_recognizer()
    cuts = split_points(samples, sr)
    parts = []
    with _lock:
        for a, b in zip(cuts, cuts[1:]):
            st = rec.create_stream()
            st.accept_waveform(sr, samples[a:b])
            rec.decode_stream(st)
            parts.append(st.result.text.strip())
    return "".join(parts).strip()


def transcribe(wav: Path, model_name: str = "paraformer-zh", device: str = "auto") -> str:
    if model_name == SHERPA_MODEL:
        return _transcribe_sherpa(wav)
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
