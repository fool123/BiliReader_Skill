from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chunker import chunk_segments
from app.schemas import TaskStatus, Transcript, TranscriptSegment
from app.services import (
    FakeSubtitleProvider,
    FakeTranscriber,
    OpenAICompatibleSummarizer,
    TaskRunner,
    YtDlpWhisperTranscriber,
    infer_platform,
)
from app.storage import Storage


def assert_chunker() -> None:
    chunks = chunk_segments(
        [
            TranscriptSegment(0, 1, "a" * 80),
            TranscriptSegment(1, 2, "b" * 80),
            TranscriptSegment(2, 3, "c" * 250),
        ],
        max_chars=100,
    )
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].segments[0].text.startswith("a")
    assert chunks[1].segments[0].text.startswith("b")
    assert len(chunks[2].segments[0].text) == 100
    assert len(chunks[3].segments[0].text) == 100
    assert len(chunks[4].segments[0].text) == 50


def new_storage(tmp: str) -> Storage:
    return Storage(Path(tmp) / "data")


def assert_task_flow_with_subtitle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        storage = new_storage(tmp)
        task_id = str(uuid4())
        storage.create_task(task_id, "https://example.com/video", None, "detailed", None)
        runner = TaskRunner(
            storage,
            FakeSubtitleProvider(
                Transcript(
                    language="zh",
                    segments=[TranscriptSegment(0, 2, "字幕优先路径。")],
                )
            ),
            FakeTranscriber(),
            OpenAICompatibleSummarizer(),
        )
        runner.run(task_id)
        task = storage.get_task(task_id)
        assert task and task["status"] == TaskStatus.SUCCEEDED.value
        assert task["has_transcript"] is True
        assert task["has_note"] is True
        assert "字幕优先路径" in (storage.load_note(task_id) or "")


def assert_audio_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        storage = new_storage(tmp)
        task_id = str(uuid4())
        storage.create_task(task_id, "https://example.com/no-subtitle", None, "detailed", None)
        transcriber = FakeTranscriber()
        runner = TaskRunner(
            storage,
            FakeSubtitleProvider(None),
            transcriber,
            OpenAICompatibleSummarizer(),
        )
        runner.run(task_id)
        transcript = storage.load_transcript(task_id)
        assert transcriber.called is True
        assert transcript is not None
        assert "兜底路径" in transcript.full_text
        assert storage.get_task(task_id)["status"] == TaskStatus.SUCCEEDED.value


def assert_platform_validation() -> None:
    assert infer_platform("https://www.youtube.com/watch?v=xxxxxxxxxxx", None) == "youtube"
    assert infer_platform("https://www.bilibili.com/video/BV175LQ6UE5q/", None) == "bilibili"
    assert infer_platform("file:///tmp/demo.mp4", None) == "local"
    assert infer_platform("anything", "local") == "local"
    assert infer_platform("https://example.com/video", "bilibili") == "bilibili"
    try:
        infer_platform("https://example.com/video", None)
    except ValueError as exc:
        assert str(exc) == "unsupported platform"
    else:
        raise AssertionError("unsupported URL should fail")


def assert_bilibili_headers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BILIREADER_BILIBILI_COOKIE"] = "SESSDATA=test"
        headers = YtDlpWhisperTranscriber(Path(tmp))._bilibili_headers("https://www.bilibili.com/video/BVxxx/")
        assert "Chrome" in headers["User-Agent"]
        assert headers["Referer"].endswith("/BVxxx/")
        assert headers["Cookie"] == "SESSDATA=test"
        os.environ.pop("BILIREADER_BILIBILI_COOKIE", None)


if __name__ == "__main__":
    assert_chunker()
    assert_task_flow_with_subtitle()
    assert_audio_fallback()
    assert_platform_validation()
    assert_bilibili_headers()
    print("checks passed")
