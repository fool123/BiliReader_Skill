# BiliReader Codex Skill

[中文](README.md)

BiliReader is a cross-device Codex skill for video analysis. It installs a local runtime from Git, starts an independent FastAPI backend, then analyzes online videos or local media files and returns transcripts plus Markdown notes.

## Features

- Supports Bilibili, YouTube, and other URLs recognized by the backend.
- Supports uploaded local video/audio files.
- Uses platform subtitles first; falls back to audio download and faster-whisper transcription.
- Can use an OpenAI-compatible API for chunked summarization and final Markdown merging.
- Falls back to local extractive notes when no API key is configured.
- Stores task history, transcripts, and Markdown notes.

## Installation

Copy the skill into the Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R skills/BiliReader ~/.codex/skills/BiliReader
```

Install the runtime:

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py install
```

Default source repository:

```text
https://github.com/fool123/BiliReader_CodexSkill.git
```

Optional environment variables:

```bash
export BILIREADER_REPO_URL="https://github.com/fool123/BiliReader_CodexSkill.git"
export BILIREADER_RUNTIME_DIR="$HOME/.codex/bilireader-runtime"
export BILIREADER_REF="main"
export BILIREADER_PORT="8787"
export WHISPER_MODEL="tiny"
export OPENAI_API_KEY="your API key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4.1-mini"
export BILIREADER_BILIBILI_COOKIE="optional Bilibili Cookie"
export BILIREADER_BILIBILI_COOKIE_FILE="/path/to/cookies.txt"
```

## CLI Usage

Start the backend:

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py serve
```

Analyze an online video:

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py analyze "https://www.bilibili.com/video/BV..."
```

Analyze a local file:

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py analyze /path/to/video.mp4
```

Inspect tasks:

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py status
python ~/.codex/skills/BiliReader/scripts/bilireader.py status <task_id>
```

Read results:

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py note <task_id>
python ~/.codex/skills/BiliReader/scripts/bilireader.py transcript <task_id>
```

## API Usage and Effects

Default backend URL:

```text
http://127.0.0.1:8787
```

### Create an Online Video Task

```bash
curl -X POST http://127.0.0.1:8787/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.bilibili.com/video/BV...","platform":"bilibili","note_style":"detailed","model":"gpt-4.1-mini"}'
```

Effect: creates an async task, tries subtitles first, falls back to audio transcription, then generates Markdown notes.

### Create a Local File Task

```bash
curl -X POST http://127.0.0.1:8787/api/tasks/local-file \
  -F 'file=@/path/to/video.mp4' \
  -F 'note_style=detailed'
```

Effect: uploads a local video/audio file and runs the same transcription, chunking, and note-generation pipeline.

### Query Task Status

```bash
curl http://127.0.0.1:8787/api/tasks/<task_id>
```

Effect: shows whether the task is fetching subtitles, downloading audio, transcribing, summarizing, completed, or failed.

### Read Markdown Notes

```bash
curl http://127.0.0.1:8787/api/tasks/<task_id>/note
```

Effect: returns JSON with `task_id` and `markdown`; `markdown` is the final summary for documents, notes, or knowledge bases.

### Read Transcript

```bash
curl http://127.0.0.1:8787/api/tasks/<task_id>/transcript
```

Effect: returns JSON with `task_id`, `language`, `full_text`, and timestamped `segments` for review, search, or downstream analysis.

## FAQ

- The first faster-whisper run may download a model.
- Online videos require network access to the target website.
- For Bilibili 412, login-only videos, or anti-bot failures, set `BILIREADER_BILIBILI_COOKIE` or `BILIREADER_BILIBILI_COOKIE_FILE`.
- Dependencies are installed into the runtime repo `.venv`, not globally; the backend uses `imageio-ffmpeg` for a project-level ffmpeg binary.
- Backend path mode only accepts project-local media paths; use CLI upload for arbitrary local files.
