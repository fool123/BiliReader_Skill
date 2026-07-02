from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from .schemas import Transcript, TranscriptSegment


class CompositeSubtitleProvider:
    def __init__(self, *providers) -> None:
        self.providers = providers

    def fetch(self, url: str, platform: str | None) -> Transcript | None:
        for provider in self.providers:
            transcript = provider.fetch(url, platform)
            if transcript and transcript.segments:
                return transcript
        return None


class YouTubeSubtitleProvider:
    def fetch(self, url: str, platform: str | None) -> Transcript | None:
        if platform and platform != "youtube":
            return None
        video_id = self._video_id(url)
        if not video_id:
            return None

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            return None

        try:
            rows = YouTubeTranscriptApi.get_transcript(video_id, languages=["zh", "zh-Hans", "en"])
        except Exception:
            return None

        return Transcript(
            language="unknown",
            segments=[
                TranscriptSegment(
                    start=float(row["start"]),
                    end=float(row["start"]) + float(row.get("duration", 0)),
                    text=str(row["text"]).strip(),
                )
                for row in rows
                if str(row.get("text", "")).strip()
            ],
        )

    def _video_id(self, url: str) -> str | None:
        patterns = [
            r"[?&]v=([A-Za-z0-9_-]{11})",
            r"youtu\.be/([A-Za-z0-9_-]{11})",
            r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class YtDlpSubtitleProvider:
    def fetch(self, url: str, platform: str | None) -> Transcript | None:
        if platform not in {"bilibili"}:
            return None

        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            return None

        with tempfile.TemporaryDirectory() as tmp:
            outtmpl = str(Path(tmp) / "subtitle.%(ext)s")
            opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hans", "zh-CN", "zh", "ai-zh", "en"],
                "subtitlesformat": "json3/srt/vtt/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "noplaylist": True,
            }
            try:
                with YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
            except Exception:
                return None

            for path in sorted(Path(tmp).iterdir()):
                transcript = self._parse_file(path)
                if transcript and transcript.segments:
                    return transcript
        return None

    def _parse_file(self, path: Path) -> Transcript | None:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix in {".json", ".json3"}:
            return self._parse_json(text)
        return self._parse_timed_text(text)

    def _parse_json(self, text: str) -> Transcript | None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        rows = []
        if isinstance(data.get("body"), list):
            for item in data["body"]:
                rows.append((item.get("from", 0), item.get("to", 0), item.get("content", "")))
        elif isinstance(data.get("events"), list):
            for item in data["events"]:
                start = float(item.get("tStartMs", 0)) / 1000
                end = start + float(item.get("dDurationMs", 0)) / 1000
                content = "".join(seg.get("utf8", "") for seg in item.get("segs", []))
                rows.append((start, end, content))

        segments = [
            TranscriptSegment(start=float(start), end=float(end), text=str(content).strip())
            for start, end, content in rows
            if str(content).strip()
        ]
        return Transcript(language="unknown", segments=segments) if segments else None

    def _parse_timed_text(self, text: str) -> Transcript | None:
        segments = []
        blocks = re.split(r"\n\s*\n", text)
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip() and not line.startswith("WEBVTT")]
            time_line = next((line for line in lines if "-->" in line), "")
            if not time_line:
                continue
            content = " ".join(line for line in lines if line != time_line and not line.isdigit())
            match = re.search(r"([\d:. ,]+)\s*-->\s*([\d:. ,]+)", time_line)
            if match and content.strip():
                segments.append(TranscriptSegment(self._seconds(match.group(1)), self._seconds(match.group(2)), content))
        return Transcript(language="unknown", segments=segments) if segments else None

    def _seconds(self, value: str) -> float:
        value = value.replace(",", ".")
        parts = [float(part) for part in value.split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0]
