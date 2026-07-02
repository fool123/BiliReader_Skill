# 独立视频分析工具使用手册

## 1. 工具位置

- 后端：`/Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend`
- 前端：`/Users/winsonzhang/Documents/SkillDesign/video-analyzer/frontend`
- 设计与日志：`/Users/winsonzhang/Documents/SkillDesign/independent-video-analyzer-docs`

## 2. 已安装环境

后端环境已安装在：

```bash
/Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend/.venv
```

其中包含：

- Python 3.11.15
- ffmpeg 8.1.2
- FastAPI
- uvicorn
- youtube-transcript-api
- yt-dlp
- faster-whisper

前端环境已安装在：

```bash
/Users/winsonzhang/Documents/SkillDesign/video-analyzer/frontend/node_modules
```

其中包含：

- React
- Vite
- TypeScript
- Vitest

## 3. 启动后端

打开一个终端：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787
```

后端地址：

```text
http://127.0.0.1:8787
```

健康检查可以访问：

```bash
curl http://127.0.0.1:8787/api/tasks
```

正常返回：

```json
{"items":[]}
```

如果已经跑过测试或创建过任务，`items` 里会有历史任务；只要响应里有 `items` 数组，就表示后端可访问。

## 4. 启动前端

再打开一个终端：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/frontend
npm run dev
```

前端默认地址通常是：

```text
http://127.0.0.1:5173
```

如果 5173 被占用，Vite 会在终端里显示新的端口，按终端显示的地址打开即可。

## 5. 基本使用流程

1. 先启动后端。
2. 再启动前端。
3. 在浏览器打开前端地址。
4. 粘贴 YouTube 或 Bilibili 视频链接。
5. 平台可填 `youtube` / `bilibili`，也可留给后端识别。
6. 选择笔记风格，默认 `detailed`。
7. 模型字段可填 `gpt-4.1-mini`，也可以留空使用后端默认。
8. 点击创建分析任务。
9. 前端会轮询任务状态。
10. 成功后查看 Markdown 笔记、Transcript 和历史记录。

## 6. AI 总结配置

如果不配置 API Key，后端会使用本地 extractive fallback，能生成基础 Markdown 摘要。

如需使用 OpenAI-compatible 模型：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4.1-mini"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8787
```

如果使用兼容服务，把 `OPENAI_BASE_URL` 改成对应地址即可。

## 7. 转写配置

无字幕视频会走：

```text
yt-dlp 下载音频 -> ffmpeg 提取 mp3 -> faster-whisper 转写
```

默认 Whisper 模型：

```text
base
```

可改成更小模型以降低首次下载和运行成本：

```bash
export WHISPER_MODEL="tiny"
```

再启动后端。

注意：

- 首次使用 faster-whisper 会下载模型。
- 真实在线视频需要网络可达。
- 如果本机使用代理，确保终端进程能访问对应代理端口。

## 8. 常用验证命令

后端离线检查：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend
.venv/bin/python tests/run_checks.py
```

预期输出：

```text
checks passed
```

前端测试：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/frontend
npm test
```

前端构建：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/frontend
npm run build
```

## 9. 目录说明

后端：

```text
video-analyzer/backend/app/main.py          API 入口
video-analyzer/backend/app/services.py      任务流程、字幕、转写、总结
video-analyzer/backend/app/storage.py       SQLite 与文件缓存
video-analyzer/backend/app/chunker.py       transcript 分块
video-analyzer/backend/app/schemas.py       状态和数据结构
video-analyzer/backend/tests/run_checks.py  离线检查
```

前端：

```text
video-analyzer/frontend/src/App.tsx     工作台页面
video-analyzer/frontend/src/api.ts      API 调用
video-analyzer/frontend/src/types.ts    前端类型
video-analyzer/frontend/src/App.css     页面样式
```

## 10. 常见问题

### 后端启动失败：端口被占用

换一个端口：

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8788
```

然后前端 API 地址也需要同步调整。当前前端默认调用：

```text
http://localhost:8787
```

### 真实视频分析失败

优先检查：

- 视频链接是否是 YouTube 或 Bilibili 链接。
- 终端是否能访问外网。
- 代理是否可用。
- 是否配置了 `OPENAI_API_KEY`。
- 首次 Whisper 模型是否下载完成。

### 只想本地验证，不调用网络

运行：

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend
.venv/bin/python tests/run_checks.py
```

这条检查不需要网络、视频站点或 API Key。

## 11. 当前限制

- MVP 优先支持 YouTube 和 Bilibili。
- 没有浏览器插件、桌面端、多用户系统、RAG 问答。
- 没有配置页面，模型和 API Key 通过环境变量传入。
- 后端当前任务在 API 请求中直接执行，长视频会占用请求时间；后续可改成后台队列。
