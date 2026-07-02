# 执行线程提示词

## 后端执行线程提示词

请在项目 `/Users/winsonzhang/Documents/SkillDesign` 中执行后端任务。

约束：

- 必须先阅读：
  - `independent-video-analyzer-docs/01-design-proposal.md`
  - `independent-video-analyzer-docs/02-backend-prd.md`
  - `independent-video-analyzer-docs/04-shared-api-contract.md`
- 新建独立后端目录：`video-analyzer/backend`
- 不允许修改、导入、调用或复制 `BiliNote/` 内部代码。
- 可以参考 BiliNote 的思路，但实现必须独立。
- 只负责后端，不写前端。
- 你不是唯一执行者，前端线程会并行写 `video-analyzer/frontend`；不要改前端目录，不要回滚他人改动。

实现目标：

- Python 3.11 + FastAPI + SQLite。
- 提供共享契约中的 API。
- 实现任务状态流转。
- 实现 transcript schema、chunker、summarizer 接口、缓存目录。
- 字幕优先、音频转写兜底的真实集成可以保留为小模块；测试必须能用 fake 路径离线跑通。
- 写最小可运行检查，至少覆盖 chunker、任务状态流转、无字幕兜底路径。

完成后：

- 只开启 1 个 reviewer 子 Agent。
- reviewer 审查范围：是否可运行、是否符合 PRD/API 契约、是否无明显 bug、是否未依赖 BiliNote。
- 最终回复必须包含：
  - 改动路径
  - 如何运行
  - 测试/检查结果
  - reviewer 审查结论
  - 未完成项或风险

## 前端执行线程提示词

请在项目 `/Users/winsonzhang/Documents/SkillDesign` 中执行前端任务。

约束：

- 必须先阅读：
  - `independent-video-analyzer-docs/01-design-proposal.md`
  - `independent-video-analyzer-docs/03-frontend-prd.md`
  - `independent-video-analyzer-docs/04-shared-api-contract.md`
- 新建独立前端目录：`video-analyzer/frontend`
- 不允许修改、导入、调用或复制 `BiliNote/` 内部代码或组件。
- 只负责前端，不写后端。
- 你不是唯一执行者，后端线程会并行写 `video-analyzer/backend`；不要改后端目录，不要回滚他人改动。

实现目标：

- React + Vite + TypeScript。
- 首页就是视频分析工作台，不做营销落地页。
- 实现 URL 输入、任务状态、Markdown 笔记、transcript 面板、历史记录。
- 所有 API 调用只按 `04-shared-api-contract.md`。
- 样式用最少依赖，保持工作台式界面。
- 写最小可运行检查：构建检查或组件/页面 smoke check。

完成后：

- 只开启 1 个 reviewer 子 Agent。
- reviewer 审查范围：是否可运行、是否符合 PRD/API 契约、是否无明显 bug、是否未依赖 BiliNote。
- 最终回复必须包含：
  - 改动路径
  - 如何运行
  - 测试/检查结果
  - reviewer 审查结论
  - 未完成项或风险

## Reviewer 子 Agent 通用提示词

你是本线程唯一 reviewer。请审查当前线程产物：

- 是否可运行。
- 是否符合 `independent-video-analyzer-docs/` 中对应 PRD 和共享 API 契约。
- 是否存在明显 bug。
- 是否误用了 `BiliNote/` 的 API、内部工具或代码。
- 是否有最小检查覆盖核心路径。

只输出：

- 结论：通过 / 不通过。
- 发现的问题，按严重程度排序。
- 必须修复项。
- 可后续优化项。
- 你实际运行或检查过的命令。
