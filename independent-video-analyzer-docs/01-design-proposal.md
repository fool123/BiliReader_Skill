# 独立视频分析工具总体设计

状态：ready-for-agent

## 目标

开发一个用户专属、独立的视频分析工具。它可以参考 BiliNote 的产品逻辑，但不能依赖 BiliNote 的 API、内部工具、下载器、前端组件或后端代码。

## 核心用户价值

用户输入在线视频链接或本地视频后，工具自动提取内容、生成结构化 Markdown 笔记，并尽量保留可追溯时间点。第一版优先保证稳定、可运行、可本地验证。

## MVP 范围

- 输入视频链接。
- 优先获取平台字幕。
- 无字幕时下载音频并转写。
- 将 transcript 统一成带时间戳的 segments。
- 按请求预算分块，调用 OpenAI-compatible LLM 生成局部笔记。
- 合并局部笔记为完整 Markdown。
- 查询任务状态、查看 transcript、查看 note、查看历史。
- 缓存中间产物，避免重复处理。

## 暂不做

- 浏览器插件。
- 桌面端封装。
- 多用户系统。
- RAG 问答。
- 复杂视频多模态理解。
- 自动发布、账号体系和计费。

## 技术选择

后端：

- Python 3.11。
- FastAPI。
- SQLite。
- yt-dlp。
- youtube-transcript-api。
- faster-whisper。
- FFmpeg。
- OpenAI-compatible SDK。

前端：

- React。
- Vite。
- TypeScript。
- 原生 CSS 或少量样式工具。
- 不引入复杂 UI 框架，MVP 先保证清晰可用。

## 数据流

```text
用户输入 URL
→ 创建任务
→ 识别平台与视频 ID
→ 查询缓存
→ 优先获取平台字幕
→ 无字幕则下载音频并转写
→ 生成 transcript segments
→ 分块总结
→ 合并 Markdown
→ 保存任务结果
→ 前端轮询状态并展示笔记
```

## 精确性原则

- 平台字幕优先于 ASR。
- transcript 必须保留 `start`、`end`、`text`。
- LLM prompt 明确禁止编造 transcript 外内容。
- 章节尽量带来源时间点。
- 合并阶段只允许合并、去重和整理结构，不新增事实。
- 前端提供 transcript 查看入口，方便人工核对。

## 高效性原则

- 有字幕时不下载音视频。
- 有缓存时不重复获取字幕、转写或总结。
- 长 transcript 分块处理，避免上下文超限。
- 截图和视频理解默认不做。
- 默认使用轻量转写模型，用户后续可手动提高精度。

## 验收标准

- 可以本地启动后端 API。
- 可以本地启动前端页面。
- 输入任务后能看到任务状态变化。
- mock 或真实 transcript 能生成 Markdown。
- chunker、任务状态流转、无字幕兜底路径有最小检查。
- 前后端接口契约一致。
