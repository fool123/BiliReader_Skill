# 前端 PRD：独立视频分析工具

状态：ready-for-agent

## Problem Statement

用户需要一个独立、清晰、可本地运行的前端，用来提交视频分析任务、查看处理进度、阅读 Markdown 笔记、核对 transcript，并回看历史记录。前端不能复用 BiliNote 的组件、状态管理或 API 封装，只能按共享接口契约调用新后端。

## Solution

构建一个新的 React + Vite + TypeScript 前端。首页直接呈现可用的视频分析工作台：URL 输入、分析选项、任务进度、Markdown 笔记、transcript 面板和历史记录。UI 以实用、克制、信息密度适中为原则，不做营销页。

## User Stories

1. As a user, I want to paste a video URL, so that I can start analysis quickly.
2. As a user, I want to choose a note style, so that the output fits my use case.
3. As a user, I want to see task status, so that I know whether the backend is working.
4. As a user, I want readable progress text, so that failures are understandable.
5. As a user, I want to read generated Markdown in the app, so that I can review results immediately.
6. As a user, I want to copy Markdown, so that I can reuse the notes elsewhere.
7. As a user, I want to view transcript segments, so that I can verify note accuracy.
8. As a user, I want timestamped transcript rows, so that I can trace claims back to the source.
9. As a user, I want a task history list, so that I can reopen previous analyses.
10. As a user, I want empty, loading, success, and failure states, so that the app feels predictable.
11. As a user, I want validation before submit, so that obvious invalid input is caught early.
12. As a developer, I want API calls centralized, so that contract changes are easy to update.
13. As a developer, I want typed task and transcript models, so that frontend and backend stay aligned.
14. As a reviewer, I want a minimal build or smoke check, so that the front end is known to compile.
15. As a future product owner, I want the UI independent from BiliNote, so that it can become a standalone tool.

## Implementation Decisions

- Build a new frontend under the independent tool directory; do not copy BiliNote components or state stores.
- The first screen is the actual analyzer workspace, not a landing page.
- Use a small component set: task form, status panel, markdown panel, transcript panel, history panel.
- Use a small API client module that targets the shared contract only.
- Poll task status while a task is not terminal; stop polling on succeeded or failed.
- Render Markdown with a minimal safe renderer or a simple preformatted MVP fallback if no dependency is already available.
- Store only lightweight local UI preferences in browser localStorage; task history source of truth comes from backend.
- Keep styling in local CSS and avoid heavy UI dependencies.
- Do not implement auth, plugin UI, desktop shell, or RAG chat in MVP.

## Testing Decisions

- Test at the user workflow seam: submit URL, show loading, render success, render failure.
- Add a build check or smoke test proving the app compiles.
- Mock API responses in component-level checks if test tooling is present; otherwise include a minimal static smoke path.
- Do not test internal component implementation details.
- Verify frontend labels and states match the shared API status vocabulary.

## Out of Scope

- Browser extension UI.
- Desktop/Tauri packaging.
- Multi-account settings.
- Rich WYSIWYG editor.
- RAG chat panel.
- Full design system.

## Further Notes

- The UI should feel like a focused work tool: compact, readable, and direct.
- The frontend thread must run exactly one reviewer sub Agent after implementation and include that review result in its final reply.
