from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    FETCHING_SUBTITLE = "fetching_subtitle"
    DOWNLOADING_AUDIO = "downloading_audio"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    MERGING = "merging"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Transcript:
    language: str
    segments: list[TranscriptSegment]

    @property
    def full_text(self) -> str:
        return "\n".join(segment.text for segment in self.segments)

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "full_text": self.full_text,
            "segments": [segment.to_dict() for segment in self.segments],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Transcript":
        return cls(
            language=payload.get("language", "unknown"),
            segments=[
                TranscriptSegment(
                    start=float(item["start"]),
                    end=float(item["end"]),
                    text=str(item["text"]),
                )
                for item in payload.get("segments", [])
            ],
        )
