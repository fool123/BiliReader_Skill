from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .schemas import TaskStatus, Transcript


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(
            data_dir
            or os.environ.get("VIDEO_ANALYZER_DATA_DIR")
            or Path(__file__).resolve().parents[1] / "data"
        )
        self.cache_dir = self.data_dir / "cache"
        self.transcript_dir = self.cache_dir / "transcripts"
        self.note_dir = self.cache_dir / "notes"
        self.upload_dir = self.data_dir / "uploads"
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.note_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "tasks.sqlite3"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists tasks (
                    task_id text primary key,
                    status text not null,
                    message text not null default '',
                    title text,
                    source_url text not null,
                    platform text,
                    note_style text not null,
                    model text,
                    created_at text not null,
                    updated_at text not null
                )
                """
            )

    def create_task(
        self,
        task_id: str,
        source_url: str,
        platform: str | None,
        note_style: str,
        model: str | None,
    ) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                insert into tasks (
                    task_id, status, source_url, platform, note_style, model,
                    created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    TaskStatus.PENDING.value,
                    source_url,
                    platform,
                    note_style,
                    model,
                    now,
                    now,
                ),
            )

    def update_task(
        self,
        task_id: str,
        status: TaskStatus,
        message: str = "",
        title: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                update tasks
                set status = ?, message = ?, title = coalesce(?, title), updated_at = ?
                where task_id = ?
                """,
                (status.value, message, title, utc_now(), task_id),
            )

    def get_task(self, task_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("select * from tasks where task_id = ?", (task_id,)).fetchone()
        return self._task_payload(row) if row else None

    def list_tasks(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from tasks order by created_at desc"
            ).fetchall()
        return [self._task_payload(row) for row in rows]

    def save_transcript(self, task_id: str, transcript: Transcript) -> None:
        (self.transcript_dir / f"{task_id}.json").write_text(
            json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_transcript(self, task_id: str) -> Transcript | None:
        path = self.transcript_dir / f"{task_id}.json"
        if not path.exists():
            return None
        return Transcript.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_note(self, task_id: str, markdown: str) -> None:
        (self.note_dir / f"{task_id}.md").write_text(markdown, encoding="utf-8")

    def load_note(self, task_id: str) -> str | None:
        path = self.note_dir / f"{task_id}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def _task_payload(self, row: sqlite3.Row) -> dict:
        task_id = row["task_id"]
        return {
            "task_id": task_id,
            "status": row["status"],
            "message": row["message"],
            "title": row["title"],
            "source_url": row["source_url"],
            "platform": row["platform"],
            "note_style": row["note_style"],
            "model": row["model"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "has_transcript": (self.transcript_dir / f"{task_id}.json").exists(),
            "has_note": (self.note_dir / f"{task_id}.md").exists(),
        }
