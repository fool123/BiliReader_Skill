# 独立视频分析工具后端

## 运行

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

无字幕兜底需要本机可用 `ffmpeg`，并安装 `yt-dlp` 与 `faster-whisper`。

## 离线检查

```bash
cd /Users/winsonzhang/Documents/SkillDesign/video-analyzer/backend
python3 tests/run_checks.py
```

默认数据目录是 `data/`，可用 `VIDEO_ANALYZER_DATA_DIR` 覆盖。
