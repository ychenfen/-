"""主流程：分享口令 → 作品 ID → 下载（降级）→ 抽音频 → 转写 → 落盘。

每条视频一个目录 <data_dir>/<aweme_id>/：
  meta.json       标题、作者、时长、用了哪个后端、哪些后端失败了
  transcript.txt  逐字稿
  audio.wav       16k 单声道音频（留着方便换模型重转）
  video.mp4       默认转写完删掉，DOUYIN_KEEP_VIDEO=1 保留
同一个作品再次请求时直接读缓存，不再访问抖音。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from .config import Settings, get_settings
from .downloaders import AllBackendsFailed, DownloadChain, UnsupportedContent, build_backends
from .share import ShareParseError, resolve
from .transcribe import TranscribeError, extract_audio, transcribe

log = logging.getLogger(__name__)

_chain: DownloadChain | None = None


def _get_chain(settings: Settings) -> DownloadChain:
    # 进程内共用一条链，限速才对跨请求生效
    global _chain
    if _chain is None:
        _chain = DownloadChain(build_backends(settings), settings.min_interval)
    return _chain


def load_cached(item_dir: Path) -> dict | None:
    meta, txt = item_dir / "meta.json", item_dir / "transcript.txt"
    if not (meta.exists() and txt.exists()):
        return None
    data = json.loads(meta.read_text(encoding="utf-8"))
    data["transcript"] = txt.read_text(encoding="utf-8")
    data["cached"] = True
    return data


def douyin_to_text(share_text: str, force: bool = False, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    url, aweme_id = resolve(share_text, timeout=settings.timeout)
    item_dir = settings.data_dir / aweme_id

    if not force and (cached := load_cached(item_dir)):
        log.info("命中缓存 %s", aweme_id)
        return cached

    t0 = time.monotonic()
    info, fallback_errors = _get_chain(settings).download(url, aweme_id, item_dir)
    t_dl = time.monotonic() - t0

    wav = extract_audio(info.video_path, item_dir / "audio.wav")
    text = transcribe(wav, settings.asr_model, settings.asr_device)
    t_asr = time.monotonic() - t0 - t_dl

    if not settings.keep_video and info.video_path and info.video_path.exists():
        info.video_path.unlink()
        info.video_path = None

    meta = {
        **info.to_dict(),
        "share_url": url,
        "asr_model": settings.asr_model,
        "fallback_errors": fallback_errors,
        "timing_s": {"download": round(t_dl, 1), "transcribe": round(t_asr, 1)},
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dir": str(item_dir),
    }
    (item_dir / "transcript.txt").write_text(text, encoding="utf-8")
    (item_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**meta, "transcript": text, "cached": False}


def run_safe(share_text: str, force: bool = False, settings: Settings | None = None) -> dict:
    """douyin_to_text 的不抛异常版本：已知错误转成 {"error", "message"}，给 MCP / HTTP 用。"""
    try:
        return douyin_to_text(share_text, force=force, settings=settings)
    except ShareParseError as e:
        return {"error": "bad_share_text", "message": str(e)}
    except UnsupportedContent as e:
        return {"error": "unsupported_content", "message": str(e)}
    except AllBackendsFailed as e:
        return {
            "error": "download_failed",
            "message": "所有下载后端都失败了，可能是 cookie 过期或被风控，先跑 healthcheck 排查",
            "backends": e.errors,
        }
    except TranscribeError as e:
        return {"error": "transcribe_failed", "message": str(e)}
    except requests.RequestException as e:
        return {"error": "network", "message": f"网络出错：{e}"}


def list_local(limit: int = 20, settings: Settings | None = None) -> list[dict]:
    """最近处理过的作品（不含逐字稿正文），给 Claude 翻素材库用。"""
    settings = settings or get_settings()
    if not settings.data_dir.exists():
        return []
    metas = sorted(settings.data_dir.glob("*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in metas[:limit]:
        m = json.loads(p.read_text(encoding="utf-8"))
        out.append({k: m.get(k) for k in ("aweme_id", "title", "author", "duration_s", "created_at", "dir")})
    return out
