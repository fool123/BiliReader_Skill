---
name: bilireader
description: Install and use BiliReader, a cross-device Codex video analysis skill for summarizing online videos and local media. Use when the user asks Codex to analyze, summarize, transcribe, or generate Markdown notes for Bilibili, YouTube, other supported video URLs, uploaded local video/audio files, or project-local media paths.
---

# BiliReader

Use BiliReader when a user wants video content summarized from Codex. Prefer the bundled CLI over manually calling the API.

## Quick Start

Run the CLI from this skill folder:

```bash
python scripts/bilireader.py install
python scripts/bilireader.py serve
python scripts/bilireader.py analyze "https://www.bilibili.com/video/BV..."
```

For local media:

```bash
python scripts/bilireader.py analyze /path/to/video.mp4
```

## Workflow

1. If BiliReader is not installed on this device, run `python scripts/bilireader.py install`.
2. Start the backend with `python scripts/bilireader.py serve`.
3. Analyze a URL or local file with `python scripts/bilireader.py analyze <url-or-path>`.
4. Re-read existing results with `note <task_id>` or `transcript <task_id>`.

The default repository is `https://github.com/fool123/BiliReader_CodexSkill.git`. Override only when the user explicitly provides another source:

```bash
BILIREADER_REPO_URL="https://github.com/owner/repo.git" python scripts/bilireader.py install
```

## Commands

- `install`: clone or update the runtime repository under `~/.codex/bilireader-runtime/repo`, create the backend `.venv`, and install backend requirements.
- `serve`: run the FastAPI backend on `127.0.0.1:${BILIREADER_PORT:-8787}`.
- `status [task_id]`: list tasks or inspect one task.
- `analyze <url-or-path>`: create a task, poll until completion, then print Markdown.
- `note <task_id>`: print saved Markdown.
- `transcript <task_id>`: print full transcript text.

## Environment

- `BILIREADER_REPO_URL`: runtime Git repository, defaults to the official BiliReader repo.
- `BILIREADER_REF`: optional branch, tag, or commit.
- `BILIREADER_RUNTIME_DIR`: install location, defaults to `~/.codex/bilireader-runtime`.
- `BILIREADER_PORT`: backend port, defaults to `8787`.
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`: optional OpenAI-compatible summarizer settings.
- `WHISPER_MODEL`: optional faster-whisper model, for example `tiny` or `base`.

## API Reference

Read `references/api-contract.md` only when the user needs direct HTTP API usage, integration details, or endpoint examples.

## Boundaries

- Do not globally install Python or Node dependencies.
- Do not copy or depend on BiliNote runtime code.
- Do not open arbitrary local disk paths through the backend path mode; use file upload for local files.
