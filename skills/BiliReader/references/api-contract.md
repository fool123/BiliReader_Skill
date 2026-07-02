# BiliReader API Contract

Base URL: `http://127.0.0.1:8787` by default. Override the CLI and backend port with `BILIREADER_PORT`.

## Create URL Task

```bash
curl -X POST http://127.0.0.1:8787/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.bilibili.com/video/BV...","platform":"bilibili","note_style":"detailed","model":"gpt-4.1-mini"}'
```

Creates an asynchronous task for an online video. The backend prefers platform subtitles, then falls back to audio download and faster-whisper transcription.

## Create Local File Task

```bash
curl -X POST http://127.0.0.1:8787/api/tasks/local-file \
  -F 'file=@/path/to/video.mp4' \
  -F 'note_style=detailed'
```

Uploads local video/audio and analyzes it with the same transcription and summarization pipeline.

## Query Task

```bash
curl http://127.0.0.1:8787/api/tasks/{task_id}
```

Returns task state, message, source, and whether transcript/note are ready.

Statuses: `pending`, `fetching_subtitle`, `downloading_audio`, `transcribing`, `summarizing`, `merging`, `succeeded`, `failed`.

## Read Results

```bash
curl http://127.0.0.1:8787/api/tasks/{task_id}/note
curl http://127.0.0.1:8787/api/tasks/{task_id}/transcript
```

`note` returns JSON with `task_id` and `markdown`. `transcript` returns JSON with language, full text, and timestamped segments.
