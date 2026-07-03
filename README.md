# BiliReader Codex Skill

[English](README.en.md)

BiliReader 是一个给 Codex 使用的跨设备视频分析 Skill。它会从 Git 仓库安装本地运行时，启动独立 FastAPI 后端，然后分析在线视频或本地媒体文件，输出 transcript 和 Markdown 视频笔记。

## 功能

- 支持 Bilibili、YouTube 等后端可识别的视频链接。
- 支持本地视频/音频文件上传分析。
- 优先读取平台字幕；无字幕时下载音频并用 faster-whisper 转写。
- 可接入 OpenAI-compatible API 做分块总结和合并。
- 未配置 API Key 时使用本地抽取式 fallback，仍可生成基础 Markdown 笔记。
- 保存历史任务、transcript 和 Markdown note。

## 安装

把 Skill 放到 Codex Skill 目录：

```bash
mkdir -p ~/.codex/skills
cp -R skills/BiliReader ~/.codex/skills/BiliReader
```

安装运行时：

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py install
```

默认源码仓库：

```text
https://github.com/fool123/BiliReader_CodexSkill.git
```

可选环境变量：

```bash
export BILIREADER_REPO_URL="https://github.com/fool123/BiliReader_CodexSkill.git"
export BILIREADER_RUNTIME_DIR="$HOME/.codex/bilireader-runtime"
export BILIREADER_REF="main"
export BILIREADER_PORT="8787"
export WHISPER_MODEL="tiny"
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4.1-mini"
export BILIREADER_BILIBILI_COOKIE="可选的 Bilibili Cookie"
export BILIREADER_BILIBILI_COOKIE_FILE="/path/to/cookies.txt"
```

## CLI 用法

启动后端：

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py serve
```

分析在线视频：

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py analyze "https://www.bilibili.com/video/BV..."
```

分析本地文件：

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py analyze /path/to/video.mp4
```

查看任务：

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py status
python ~/.codex/skills/BiliReader/scripts/bilireader.py status <task_id>
```

读取结果：

```bash
python ~/.codex/skills/BiliReader/scripts/bilireader.py note <task_id>
python ~/.codex/skills/BiliReader/scripts/bilireader.py transcript <task_id>
```

## API 使用方式与功效

后端默认地址：

```text
http://127.0.0.1:8787
```

### 创建在线视频分析任务

```bash
curl -X POST http://127.0.0.1:8787/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.bilibili.com/video/BV...","platform":"bilibili","note_style":"detailed","model":"gpt-4.1-mini"}'
```

功效：创建异步任务，优先尝试字幕，失败后下载音频并转写，再生成 Markdown 笔记。

### 创建本地文件分析任务

```bash
curl -X POST http://127.0.0.1:8787/api/tasks/local-file \
  -F 'file=@/path/to/video.mp4' \
  -F 'note_style=detailed'
```

功效：上传本地视频或音频文件，复用同一套转写、分块总结和笔记生成流程。

### 查询任务状态

```bash
curl http://127.0.0.1:8787/api/tasks/<task_id>
```

功效：查看任务是否处于获取字幕、下载音频、转写、总结、完成或失败状态。

### 读取 Markdown 笔记

```bash
curl http://127.0.0.1:8787/api/tasks/<task_id>/note
```

功效：获取包含 `task_id` 和 `markdown` 的 JSON；其中 `markdown` 是最终总结，适合写入文档、笔记或知识库。

### 读取 Transcript

```bash
curl http://127.0.0.1:8787/api/tasks/<task_id>/transcript
```

功效：获取包含 `task_id`、`language`、`full_text` 和带时间戳 `segments` 的 JSON，适合二次分析、检索或人工校对。

## 常见问题

- 首次运行 faster-whisper 会下载模型，耗时取决于网络。
- 真实在线视频需要当前设备能访问目标网站。
- Bilibili 链接如遇 412、登录限制或风控，可配置 `BILIREADER_BILIBILI_COOKIE` 或 `BILIREADER_BILIBILI_COOKIE_FILE`。
- 不做全局 pip/npm 安装，依赖都安装在运行时仓库的 `.venv`；后端会通过 `imageio-ffmpeg` 提供项目级 ffmpeg。
- 后端路径模式只允许项目目录内媒体文件；任意本地文件请用 CLI 上传方式。
