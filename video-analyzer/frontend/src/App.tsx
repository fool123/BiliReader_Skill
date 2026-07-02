import { FormEvent, useEffect, useMemo, useState } from 'react';
import { api } from './api';
import type { HistoryItem, TaskStatus, TaskSummary, TranscriptResponse } from './types';

const terminalStatuses: TaskStatus[] = ['succeeded', 'failed'];

const statusLabels: Record<TaskStatus, string> = {
  pending: '等待处理',
  fetching_subtitle: '获取字幕',
  downloading_audio: '下载音频',
  transcribing: '转写中',
  summarizing: '生成笔记',
  merging: '合并笔记',
  succeeded: '已完成',
  failed: '失败',
};

function formatTime(seconds: number) {
  const value = Math.max(0, Math.floor(seconds));
  const hh = Math.floor(value / 3600);
  const mm = Math.floor((value % 3600) / 60);
  const ss = value % 60;
  return [hh, mm, ss]
    .filter((part, index) => part > 0 || index > 0)
    .map((part) => String(part).padStart(2, '0'))
    .join(':');
}

function statusStep(status?: TaskStatus) {
  const order: TaskStatus[] = [
    'pending',
    'fetching_subtitle',
    'downloading_audio',
    'transcribing',
    'summarizing',
    'merging',
    'succeeded',
  ];
  return status ? Math.max(0, order.indexOf(status)) : 0;
}

export default function App() {
  const [url, setUrl] = useState('');
  const [localFile, setLocalFile] = useState<File | null>(null);
  const [platform, setPlatform] = useState('');
  const [noteStyle, setNoteStyle] = useState('detailed');
  const [model, setModel] = useState('');
  const [currentTask, setCurrentTask] = useState<TaskSummary | null>(null);
  const [markdown, setMarkdown] = useState('');
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [activePanel, setActivePanel] = useState<'note' | 'transcript'>('note');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const progress = useMemo(() => {
    if (!currentTask) return 0;
    if (currentTask.status === 'failed') return 100;
    return Math.round((statusStep(currentTask.status) / 6) * 100);
  }, [currentTask]);

  async function refreshHistory() {
    try {
      setHistory(await api.listTasks());
    } catch (err) {
      setError(err instanceof Error ? err.message : '历史记录读取失败');
    }
  }

  async function loadResult(task: TaskSummary) {
    const [noteResult, transcriptResult] = await Promise.all([
      task.has_note ? api.getNote(task.task_id) : Promise.resolve({ markdown: '' }),
      task.has_transcript ? api.getTranscript(task.task_id) : Promise.resolve(null),
    ]);
    setMarkdown(noteResult.markdown);
    setTranscript(transcriptResult);
  }

  async function loadTask(taskId: string) {
    setError('');
    const task = await api.getTask(taskId);
    setCurrentTask(task);
    if (task.status === 'succeeded') {
      await loadResult(task);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmedUrl = url.trim();
    if (!localFile && !trimmedUrl) {
      setError('请输入视频 URL、本地路径，或选择本地视频文件。');
      return;
    }

    setLoading(true);
    setError('');
    setMarkdown('');
    setTranscript(null);
    try {
      const isUrl = /^https?:\/\/\S+$/i.test(trimmedUrl);
      const task = localFile || !isUrl
        ? await api.createLocalFileTask({
            file: localFile || undefined,
            path: localFile ? undefined : trimmedUrl,
            note_style: noteStyle,
            model: model.trim() || undefined,
          })
        : await api.createTask({
            url: trimmedUrl,
            platform: platform.trim() || undefined,
            note_style: noteStyle,
            model: model.trim() || undefined,
          });
      setCurrentTask({
        task_id: task.task_id,
        status: task.status,
        source_url: localFile?.name || trimmedUrl,
      });
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建任务失败');
    } finally {
      setLoading(false);
    }
  }

  async function copyMarkdown() {
    if (!markdown) return;
    try {
      await navigator.clipboard.writeText(markdown);
    } catch {
      setError('复制 Markdown 失败，请手动选择文本复制。');
    }
  }

  useEffect(() => {
    void refreshHistory();
  }, []);

  useEffect(() => {
    if (!currentTask || terminalStatuses.includes(currentTask.status)) return;

    const timer = window.setInterval(async () => {
      try {
        const task = await api.getTask(currentTask.task_id);
        setCurrentTask(task);
        if (task.status === 'succeeded') {
          await loadResult(task);
          await refreshHistory();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '任务状态读取失败');
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [currentTask]);

  return (
    <main className="shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>视频分析工作台</h1>
            <p>提交链接，生成可核对 transcript 的 Markdown 笔记。</p>
          </div>
          <button className="secondary" type="button" onClick={refreshHistory}>
            刷新历史
          </button>
        </header>

        <form className="task-form" onSubmit={handleSubmit}>
          <label className="url-field">
            <span>视频 URL / 本地路径</span>
            <input
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://... 或 /Users/.../video.mp4"
            />
          </label>
          <label>
            <span>本地视频文件</span>
            <input
              accept="audio/*,video/*"
              type="file"
              onChange={(event) => setLocalFile(event.target.files?.[0] || null)}
            />
          </label>
          <label>
            <span>平台</span>
            <input
              value={platform}
              onChange={(event) => setPlatform(event.target.value)}
              placeholder="留空自动识别"
            />
          </label>
          <label>
            <span>笔记风格</span>
            <select value={noteStyle} onChange={(event) => setNoteStyle(event.target.value)}>
              <option value="detailed">详细</option>
              <option value="outline">大纲</option>
              <option value="concise">精简</option>
            </select>
          </label>
          <label>
            <span>模型</span>
            <input value={model} onChange={(event) => setModel(event.target.value)} placeholder="默认后端配置" />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? '提交中' : '开始分析'}
          </button>
        </form>

        {error && <div className="alert">{error}</div>}

        <section className="status-panel">
          <div>
            <span className="eyebrow">当前任务</span>
            <h2>{currentTask?.title || currentTask?.task_id || '尚未创建任务'}</h2>
            <p>{currentTask?.message || currentTask?.source_url || '输入视频链接后开始分析。'}</p>
          </div>
          <div className={`status-pill status-${currentTask?.status || 'pending'}`}>
            {currentTask ? statusLabels[currentTask.status] : '空闲'}
          </div>
          <div className="progress" aria-label="任务进度">
            <span style={{ width: `${progress}%` }} />
          </div>
        </section>

        <section className="content-grid">
          <div className="main-panel">
            <div className="panel-tabs">
              <button className={activePanel === 'note' ? 'active' : ''} type="button" onClick={() => setActivePanel('note')}>
                Markdown 笔记
              </button>
              <button
                className={activePanel === 'transcript' ? 'active' : ''}
                type="button"
                onClick={() => setActivePanel('transcript')}
              >
                Transcript
              </button>
            </div>

            {activePanel === 'note' ? (
              <div className="panel-body">
                <div className="panel-actions">
                  <span>{markdown ? '已生成' : '等待任务完成'}</span>
                  <button className="secondary" type="button" onClick={copyMarkdown} disabled={!markdown}>
                    复制 Markdown
                  </button>
                </div>
                <pre className="markdown-view">{markdown || '任务完成后，这里显示 Markdown 笔记。'}</pre>
              </div>
            ) : (
              <div className="panel-body transcript-list">
                {transcript?.segments.length ? (
                  transcript.segments.map((segment, index) => (
                    <div className="segment" key={`${segment.start}-${index}`}>
                      <time>
                        {formatTime(segment.start)} - {formatTime(segment.end)}
                      </time>
                      <p>{segment.text}</p>
                    </div>
                  ))
                ) : (
                  <p className="empty">任务完成后，这里显示带时间点的 transcript。</p>
                )}
              </div>
            )}
          </div>

          <aside className="history-panel">
            <h2>历史记录</h2>
            <div className="history-list">
              {history.length ? (
                history.map((item) => (
                  <button
                    className="history-item"
                    key={item.task_id}
                    type="button"
                    onClick={() => void loadTask(item.task_id)}
                  >
                    <strong>{item.title || item.task_id}</strong>
                    <span>{statusLabels[item.status]}</span>
                    <small>{item.created_at || item.source_url || '无时间信息'}</small>
                  </button>
                ))
              ) : (
                <p className="empty">暂无历史任务。</p>
              )}
            </div>
          </aside>
        </section>
      </section>
    </main>
  );
}
