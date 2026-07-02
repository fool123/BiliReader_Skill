from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .integrations import CompositeSubtitleProvider, YouTubeSubtitleProvider, YtDlpSubtitleProvider
from .schemas import TaskStatus
from .services import OpenAICompatibleSummarizer, TaskRunner, YtDlpWhisperTranscriber, infer_platform
from .storage import Storage


class CreateTaskRequest(BaseModel):
    url: str = Field(min_length=1)
    platform: str | None = None
    note_style: str = "detailed"
    model: str | None = None


MEDIA_SUFFIXES = {
    ".aac",
    ".avi",
    ".flac",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
}


app = FastAPI(title="Independent Video Analyzer")
storage = Storage()
runner = TaskRunner(
    storage=storage,
    subtitle_provider=CompositeSubtitleProvider(YouTubeSubtitleProvider(), YtDlpSubtitleProvider()),
    transcriber=YtDlpWhisperTranscriber(storage.cache_dir / "audio"),
    summarizer=OpenAICompatibleSummarizer(),
)


@app.exception_handler(HTTPException)
def http_exception_handler(request, exc: HTTPException) -> JSONResponse:  # noqa: ANN001
    detail = exc.detail
    message = detail.get("message") if isinstance(detail, dict) else str(detail)
    return JSONResponse(status_code=exc.status_code, content={"message": message})


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc: RequestValidationError) -> JSONResponse:  # noqa: ANN001
    return JSONResponse(status_code=422, content={"message": "invalid request"})


@app.post("/api/tasks")
def create_task(payload: CreateTaskRequest, background_tasks: BackgroundTasks) -> dict:
    try:
        platform = infer_platform(payload.url, payload.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="unsupported platform") from exc

    task_id = str(uuid4())
    storage.create_task(
        task_id=task_id,
        source_url=payload.url,
        platform=platform,
        note_style=payload.note_style,
        model=payload.model,
    )
    background_tasks.add_task(runner.run, task_id)
    return {"task_id": task_id, "status": TaskStatus.PENDING.value}


@app.post("/api/tasks/local-file")
def create_local_file_task(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    path: str | None = Form(default=None),
    note_style: str = Form(default="detailed"),
    model: str | None = Form(default=None),
) -> dict:
    media_path = _save_upload(file) if file and file.filename else _validate_local_path(path)
    task_id = str(uuid4())
    storage.create_task(
        task_id=task_id,
        source_url=media_path.as_uri(),
        platform="local",
        note_style=note_style,
        model=model,
    )
    background_tasks.add_task(runner.run, task_id)
    return {"task_id": task_id, "status": TaskStatus.PENDING.value}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/api/tasks/{task_id}/transcript")
def get_transcript(task_id: str) -> dict:
    transcript = storage.load_transcript(task_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="transcript not found")
    return {"task_id": task_id, **transcript.to_dict()}


@app.get("/api/tasks/{task_id}/note")
def get_note(task_id: str) -> dict:
    markdown = storage.load_note(task_id)
    if markdown is None:
        raise HTTPException(status_code=404, detail="note not found")
    return {"task_id": task_id, "markdown": markdown}


@app.get("/api/tasks")
def list_tasks() -> dict:
    return {
        "items": [
            {
                "task_id": task["task_id"],
                "status": task["status"],
                "title": task["title"],
                "source_url": task["source_url"],
                "created_at": task["created_at"],
            }
            for task in storage.list_tasks()
        ]
    }


def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in MEDIA_SUFFIXES:
        raise HTTPException(status_code=400, detail="unsupported media file")
    target = storage.upload_dir / f"{uuid4()}{suffix}"
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return target


def _validate_local_path(path: str | None) -> Path:
    if not path:
        raise HTTPException(status_code=400, detail="missing local file")
    media_path = Path(path).expanduser().resolve()
    allowed_root = Path(__file__).resolve().parents[2]
    if allowed_root not in media_path.parents and media_path != allowed_root:
        raise HTTPException(status_code=400, detail="local file must be inside project directory")
    if not media_path.is_file() or media_path.suffix.lower() not in MEDIA_SUFFIXES:
        raise HTTPException(status_code=400, detail="unsupported media file")
    return media_path
