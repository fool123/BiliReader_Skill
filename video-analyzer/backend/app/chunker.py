from __future__ import annotations

from dataclasses import dataclass

from .schemas import TranscriptSegment


@dataclass(frozen=True)
class TranscriptChunk:
    index: int
    segments: list[TranscriptSegment]

    @property
    def text(self) -> str:
        return "\n".join(f"[{s.start:.1f}-{s.end:.1f}] {s.text}" for s in self.segments)


def chunk_segments(
    segments: list[TranscriptSegment],
    max_chars: int = 6000,
) -> list[TranscriptChunk]:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")

    chunks: list[TranscriptChunk] = []
    current: list[TranscriptSegment] = []
    current_chars = 0

    def flush() -> None:
        nonlocal current, current_chars
        if current:
            chunks.append(TranscriptChunk(index=len(chunks), segments=current))
            current = []
            current_chars = 0

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if len(text) > max_chars:
            flush()
            for start in range(0, len(text), max_chars):
                part = text[start : start + max_chars]
                chunks.append(
                    TranscriptChunk(
                        index=len(chunks),
                        segments=[
                            TranscriptSegment(
                                start=segment.start,
                                end=segment.end,
                                text=part,
                            )
                        ],
                    )
                )
            continue

        if current and current_chars + len(text) > max_chars:
            flush()
        current.append(segment)
        current_chars += len(text)

    flush()
    return chunks
