from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Protocol

from .chunker import TranscriptChunk, chunk_segments
from .schemas import TaskStatus, Transcript, TranscriptSegment
from .storage import Storage


class SubtitleProvider(Protocol):
    def fetch(self, url: str, platform: str | None) -> Transcript | None: ...


class AudioTranscriber(Protocol):
    def transcribe(self, url: str, platform: str | None) -> Transcript: ...


class Summarizer(Protocol):
    def summarize(
        self,
        chunks: list[TranscriptChunk],
        note_style: str,
        model: str | None,
    ) -> str: ...


class NoSubtitleProvider:
    def fetch(self, url: str, platform: str | None) -> Transcript | None:
        return None


class PlaceholderAudioTranscriber:
    def transcribe(self, url: str, platform: str | None) -> Transcript:
        raise RuntimeError("未配置音频下载或 ASR 转写；请接入 yt-dlp、FFmpeg 和 faster-whisper")


class ExtractiveSummarizer:
    def summarize(
        self,
        chunks: list[TranscriptChunk],
        note_style: str,
        model: str | None,
    ) -> str:
        lines = ["# 视频笔记", ""]
        for chunk in chunks:
            first = chunk.segments[0]
            lines.append(f"## 片段 {chunk.index + 1} ({first.start:.1f}s)")
            for segment in chunk.segments[:5]:
                lines.append(f"- [{segment.start:.1f}s] {segment.text}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"


class OpenAICompatibleSummarizer:
    def __init__(self, fallback: Summarizer | None = None) -> None:
        self.fallback = fallback or ExtractiveSummarizer()
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def summarize(
        self,
        chunks: list[TranscriptChunk],
        note_style: str,
        model: str | None,
    ) -> str:
        if not self.api_key:
            return self.fallback.summarize(chunks, note_style, model)

        partials = [self._complete(self._chunk_prompt(chunk, note_style), model) for chunk in chunks]
        return self._complete(self._merge_prompt(partials), model)

    def _complete(self, prompt: str, model: str | None) -> str:
        body = {
            "model": model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=__import__("json").dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except (KeyError, urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"LLM 总结失败：{exc}") from exc

    def _chunk_prompt(self, chunk: TranscriptChunk, note_style: str) -> str:
        return (
            "只基于以下 transcript 片段生成中文 Markdown 局部笔记，不要编造。"
            f"风格：{note_style}。保留关键时间点。\n\n{chunk.text}"
        )

    def _merge_prompt(self, partials: list[str]) -> str:
        return (
            "合并以下局部 Markdown 笔记，只能合并、去重和整理结构，不新增事实。\n\n"
            + "\n\n".join(partials)
        )


class YtDlpWhisperTranscriber:
    def __init__(self, cache_dir: Path | str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def transcribe(self, url: str, platform: str | None) -> Transcript:
        try:
            from faster_whisper import WhisperModel
            from yt_dlp import YoutubeDL
        except ImportError as exc:
            raise RuntimeError("音频转写依赖未安装：请安装 yt-dlp 和 faster-whisper") from exc

        with tempfile.TemporaryDirectory(dir=self.cache_dir) as tmp:
            if platform == "local":
                audio_files = [self._convert_local_media(url, Path(tmp))]
            elif platform == "bilibili":
                audio_files = [self._download_bilibili_audio(url, Path(tmp))]
            else:
                output = str(Path(tmp) / "audio.%(ext)s")
                with YoutubeDL(
                    {
                        "format": "bestaudio/best",
                        "outtmpl": output,
                        "quiet": True,
                        "noplaylist": True,
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "64",
                            }
                        ],
                    }
                ) as ydl:
                    ydl.download([url])

                audio_files = list(Path(tmp).glob("audio.*"))
            if not audio_files:
                raise RuntimeError("音频下载失败：未生成音频文件")

            model_name = os.environ.get("WHISPER_MODEL", "base")
            model = WhisperModel(model_name, device="auto", compute_type="int8")
            rows, info = model.transcribe(str(audio_files[0]), vad_filter=True)
            segments = [
                TranscriptSegment(start=float(row.start), end=float(row.end), text=row.text.strip())
                for row in rows
                if row.text.strip()
            ]
            if not segments:
                raise RuntimeError("音频转写失败：未识别出文本")
            return Transcript(language=getattr(info, "language", "unknown") or "unknown", segments=segments)

    def _convert_local_media(self, source: str, tmp: Path) -> Path:
        parsed = urllib.parse.urlparse(source)
        media = Path(urllib.parse.unquote(parsed.path if parsed.scheme == "file" else source)).expanduser().resolve()
        if not media.exists() or not media.is_file():
            raise RuntimeError("本地视频文件不存在")
        mp3 = tmp / "audio.mp3"
        subprocess.run(
            [self._ffmpeg(), "-y", "-i", str(media), "-vn", "-acodec", "libmp3lame", "-b:a", "64k", str(mp3)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return mp3

    def _download_bilibili_audio(self, url: str, tmp: Path) -> Path:
        bvid = self._bvid(url)
        if not bvid:
            raise RuntimeError("无法识别 Bilibili BV 号")
        page_url = f"https://www.bilibili.com/video/{bvid}/"
        headers = self._bilibili_headers(page_url)
        view = self._json("https://api.bilibili.com/x/web-interface/view", {"bvid": bvid}, headers)
        cid = view.get("data", {}).get("cid")
        if not cid:
            raise RuntimeError("无法获取 Bilibili cid")
        play = self._json(
            "https://api.bilibili.com/x/player/playurl",
            {"bvid": bvid, "cid": cid, "fnval": 16, "fourk": 1},
            headers,
        )
        audio = (play.get("data", {}).get("dash", {}).get("audio") or [{}])[0]
        audio_urls = [
            url
            for url in [audio.get("baseUrl") or audio.get("base_url")]
            + (audio.get("backupUrl") or audio.get("backup_url") or [])
            if url
        ]
        if not audio_urls:
            raise RuntimeError("无法获取 Bilibili 音频流")

        raw = tmp / "audio.m4s"
        mp3 = tmp / "audio.mp3"
        last_error = None
        for audio_url in audio_urls:
            req = urllib.request.Request(audio_url, headers={**headers, "Range": "bytes=0-"})
            try:
                with urllib.request.urlopen(req, timeout=60) as response, raw.open("wb") as output:
                    shutil.copyfileobj(response, output, 1024 * 1024)
                last_error = None
                break
            except urllib.error.URLError as exc:
                last_error = exc
        if last_error is not None:
            raise RuntimeError(f"Bilibili 音频下载失败：{last_error}") from last_error
        subprocess.run(
            [self._ffmpeg(), "-y", "-i", str(raw), "-vn", "-acodec", "libmp3lame", "-b:a", "64k", str(mp3)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return mp3

    def _bilibili_headers(self, referer: str) -> dict:
        headers = {
            "User-Agent": os.environ.get(
                "BILIREADER_USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            ),
            "Referer": referer,
            "Accept": "*/*",
        }
        cookie = os.environ.get("BILIREADER_BILIBILI_COOKIE")
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def _json(self, base_url: str, params: dict, headers: dict) -> dict:
        req = urllib.request.Request(base_url + "?" + urllib.parse.urlencode(params), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("code") != 0:
            raise RuntimeError(data.get("message") or "Bilibili API 请求失败")
        return data

    def _bvid(self, url: str) -> str | None:
        match = re.search(r"BV[0-9A-Za-z]+", url)
        return match.group(0) if match else None

    def _ffmpeg(self) -> str:
        bundled = Path(sys.executable).with_name("ffmpeg")
        if bundled.exists():
            return str(bundled)
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            return "ffmpeg"


def infer_platform(url: str, platform: str | None) -> str:
    if platform:
        if platform not in {"youtube", "bilibili", "local"}:
            raise ValueError("unsupported platform")
        return platform
    if url.startswith("file:"):
        return "local"
    if "youtube.com/" in url or "youtu.be/" in url:
        return "youtube"
    if "bilibili.com/" in url or "b23.tv/" in url:
        return "bilibili"
    raise ValueError("unsupported platform")


class TaskRunner:
    def __init__(
        self,
        storage: Storage,
        subtitle_provider: SubtitleProvider,
        transcriber: AudioTranscriber,
        summarizer: Summarizer,
    ) -> None:
        self.storage = storage
        self.subtitle_provider = subtitle_provider
        self.transcriber = transcriber
        self.summarizer = summarizer

    def run(self, task_id: str) -> None:
        task = self.storage.get_task(task_id)
        if not task:
            raise ValueError(f"task not found: {task_id}")

        try:
            transcript = self.storage.load_transcript(task_id)
            if transcript is None:
                self.storage.update_task(task_id, TaskStatus.FETCHING_SUBTITLE, "正在获取字幕")
                transcript = self.subtitle_provider.fetch(task["source_url"], task["platform"])

            if transcript is None:
                self.storage.update_task(task_id, TaskStatus.DOWNLOADING_AUDIO, "正在准备音频")
                self.storage.update_task(task_id, TaskStatus.TRANSCRIBING, "正在转写音频")
                transcript = self.transcriber.transcribe(task["source_url"], task["platform"])

            self.storage.save_transcript(task_id, transcript)
            self.storage.update_task(task_id, TaskStatus.SUMMARIZING, "正在生成笔记")
            chunks = chunk_segments(transcript.segments)
            markdown = self.summarizer.summarize(chunks, task["note_style"], task["model"])
            self.storage.update_task(task_id, TaskStatus.MERGING, "正在合并笔记")
            self.storage.save_note(task_id, markdown)
            self.storage.update_task(task_id, TaskStatus.SUCCEEDED, "处理完成")
        except Exception as exc:
            self.storage.update_task(task_id, TaskStatus.FAILED, str(exc))


class FakeSubtitleProvider:
    def __init__(self, transcript: Transcript | None) -> None:
        self.transcript = transcript

    def fetch(self, url: str, platform: str | None) -> Transcript | None:
        return self.transcript


class FakeTranscriber:
    def __init__(self) -> None:
        self.called = False

    def transcribe(self, url: str, platform: str | None) -> Transcript:
        self.called = True
        return Transcript(
            language="zh",
            segments=[
                TranscriptSegment(start=0, end=3, text="这是无字幕视频的转写内容。"),
                TranscriptSegment(start=3, end=6, text="这里验证音频转写兜底路径。"),
            ],
        )
