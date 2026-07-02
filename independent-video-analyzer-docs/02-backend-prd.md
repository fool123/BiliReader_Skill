# 后端 PRD：独立视频分析工具

状态：ready-for-agent

## Problem Statement

用户需要一个专属、独立的视频分析后端，用于把在线视频或本地视频转换成可追溯的结构化笔记。现有参考项目功能完整，但用户不希望依赖该项目的 API、内部工具或代码实现。后端必须提供清晰、可测试、可本地运行的最小能力，支撑前端独立调用。

## Solution

构建一个全新的 FastAPI 后端。它接收视频分析任务，优先获取平台字幕，无字幕时下载音频并转写，将内容规范化为带时间戳的 transcript segments，再调用 OpenAI-compatible LLM 分块总结并合并成 Markdown。所有任务状态、transcript、note 和缓存落到本地 SQLite 与文件目录，便于复现和调试。

## User Stories

1. As a knowledge worker, I want to submit a video URL, so that I can create notes without manually watching the full video.
2. As a learner, I want transcript segments with timestamps, so that I can verify the note against the original video.
3. As a local-first user, I want generated notes saved locally, so that my analysis history remains available.
4. As a user with limited bandwidth, I want subtitles to be used before video download, so that processing is faster.
5. As a user analyzing videos without subtitles, I want audio transcription fallback, so that unsupported videos can still be processed.
6. As a user of long videos, I want chunked summarization, so that long transcripts do not fail due to model limits.
7. As a user retrying failed tasks, I want intermediate cache reuse, so that I do not pay repeated processing cost.
8. As a developer, I want a stable API contract, so that the frontend can be built independently.
9. As a developer, I want task status transitions, so that progress can be shown accurately.
10. As a user, I want Markdown output, so that notes can be copied into common writing tools.
11. As a user, I want platform and URL validation, so that unsupported inputs fail clearly.
12. As a user, I want configurable LLM provider settings, so that I can use my own model provider.
13. As a user, I want concise error messages, so that I know whether a task failed at subtitle, download, transcription, or summarization.
14. As a maintainer, I want small self-checks, so that regressions in chunking and status flow are caught early.
15. As a future product owner, I want the backend to stay independent from BiliNote, so that the tool can evolve separately.

## Implementation Decisions

- Build a new backend under the independent tool directory; do not import from or call BiliNote modules.
- Provide HTTP APIs for task creation, task status, transcript retrieval, note retrieval, and history listing.
- Store task metadata in SQLite and larger artifacts as local files under a data directory.
- Normalize all transcripts into one schema with language, full text, and ordered timestamped segments.
- Use this retrieval order: cache, platform subtitles, audio download, ASR transcription.
- Use YouTube subtitle support in MVP; keep platform adapters simple enough to add Bilibili later.
- Use a chunker that groups transcript segments by configurable request budget and preserves order.
- Use a summarizer interface with a default OpenAI-compatible implementation and a deterministic mock path for tests.
- Use status values: pending, fetching_subtitle, downloading_audio, transcribing, summarizing, merging, succeeded, failed.
- Do not implement authentication, background distributed queues, cloud storage, RAG, or browser extension support in MVP.

## Testing Decisions

- Test external behavior at the highest practical seam: API task lifecycle and persisted results.
- Add direct checks for chunker order preservation and oversized segment splitting.
- Add a task-flow check using a fake subtitle/transcriber/summarizer path, so no network or API key is required.
- Add an audio-fallback check using a fake subtitle miss and fake transcriber, so fallback behavior is covered without downloading real media.
- Existing BiliNote tests are only reference material; new tests must live with the independent backend.

## Out of Scope

- Reusing BiliNote code or calling BiliNote APIs.
- Multi-user auth and permissions.
- Browser extension integration.
- Desktop packaging.
- RAG chat over generated notes.
- Production deployment automation.

## Further Notes

- The first implementation should favor simple local files and SQLite over a larger service architecture.
- Network-heavy integrations should be isolated behind small modules so tests can use fakes.
- The backend thread must run exactly one reviewer sub Agent after implementation and include that review result in its final reply.
