# 前后端共享 API 契约

状态：ready-for-agent

## 基础约定

- Base URL: `http://localhost:8787`
- JSON 编码：UTF-8
- 时间：ISO 8601 字符串
- 错误响应保留 `message` 字段

## TaskStatus

```text
pending
fetching_subtitle
downloading_audio
transcribing
summarizing
merging
succeeded
failed
```

## POST /api/tasks

创建视频分析任务。

请求：

```json
{
  "url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
  "platform": "youtube",
  "note_style": "detailed",
  "model": "gpt-4.1-mini"
}
```

字段：

- `url`: 必填，视频链接。
- `platform`: 可选；缺省时后端尝试识别。
- `note_style`: 可选，默认 `detailed`。
- `model`: 可选，默认由后端配置决定。

响应：

```json
{
  "task_id": "uuid",
  "status": "pending"
}
```

## POST /api/tasks/local-file

创建本地视频/音频分析任务。

请求：`multipart/form-data`

字段：

- `file`: 可选，本地视频或音频文件；优先级高于 `path`。
- `path`: 可选，本项目目录内的本地视频或音频路径。
- `note_style`: 可选，默认 `detailed`。
- `model`: 可选，默认由后端配置决定。

支持格式：`mp4`、`mov`、`mkv`、`webm`、`avi`、`mp3`、`m4a`、`wav`、`aac`、`flac`、`ogg`、`m4v`。

响应：

```json
{
  "task_id": "uuid",
  "status": "pending"
}
```

## GET /api/tasks/{task_id}

查询任务状态和摘要信息。

响应：

```json
{
  "task_id": "uuid",
  "status": "summarizing",
  "message": "正在生成笔记",
  "title": "视频标题",
  "source_url": "https://example.com/video",
  "created_at": "2026-06-30T19:00:00+08:00",
  "updated_at": "2026-06-30T19:01:00+08:00",
  "has_transcript": true,
  "has_note": false
}
```

## GET /api/tasks/{task_id}/transcript

读取 transcript。

响应：

```json
{
  "task_id": "uuid",
  "language": "zh",
  "full_text": "完整转写文本",
  "segments": [
    {
      "start": 12.3,
      "end": 18.4,
      "text": "这一段内容"
    }
  ]
}
```

## GET /api/tasks/{task_id}/note

读取 Markdown 笔记。

响应：

```json
{
  "task_id": "uuid",
  "markdown": "# 视频笔记\n\n..."
}
```

## GET /api/tasks

读取历史任务列表。

响应：

```json
{
  "items": [
    {
      "task_id": "uuid",
      "status": "succeeded",
      "title": "视频标题",
      "source_url": "https://example.com/video",
      "created_at": "2026-06-30T19:00:00+08:00"
    }
  ]
}
```

## 前端轮询规则

- 创建任务成功后，每 2 秒轮询 `GET /api/tasks/{task_id}`。
- 当状态为 `succeeded` 时读取 note 和 transcript。
- 当状态为 `failed` 时停止轮询并展示 `message`。

## 后端最小持久化

- SQLite 保存任务基础信息。
- 文件缓存保存 transcript 和 Markdown。
- 缓存 key 可基于 task id；后续再扩展 URL/content hash 去重。
