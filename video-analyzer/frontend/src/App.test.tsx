import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

const apiBase = 'http://localhost:8787';

function json(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify(data), { status: 200 }));
}

describe('视频分析工作台', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === `${apiBase}/api/tasks` && init?.method === 'POST') {
        return json({ task_id: 'task-1', status: 'pending' });
      }

      if (url === `${apiBase}/api/tasks/local-file` && init?.method === 'POST') {
        return json({ task_id: 'task-1', status: 'pending' });
      }

      if (url === `${apiBase}/api/tasks`) {
        return json({
          items: [
            {
              task_id: 'task-1',
              status: 'succeeded',
              title: '历史视频',
              source_url: 'https://example.com/video',
              created_at: '2026-06-30T19:00:00+08:00',
            },
          ],
        });
      }

      if (url === `${apiBase}/api/tasks/task-1`) {
        return json({
          task_id: 'task-1',
          status: 'succeeded',
          message: '已完成',
          title: '测试视频',
          source_url: 'https://example.com/video',
          has_note: true,
          has_transcript: true,
        });
      }

      if (url === `${apiBase}/api/tasks/task-1/note`) {
        return json({ task_id: 'task-1', markdown: '# 测试笔记\n\n- 关键观点' });
      }

      if (url === `${apiBase}/api/tasks/task-1/transcript`) {
        return json({
          task_id: 'task-1',
          language: 'zh',
          full_text: '第一句',
          segments: [{ start: 1, end: 3, text: '第一句 transcript' }],
        });
      }

      return Promise.resolve(new Response(JSON.stringify({ message: 'not found' }), { status: 404 }));
    }));
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('提交 URL 后展示任务结果，并可从历史回开 transcript', async () => {
    render(<App />);

    fireEvent.change(screen.getByLabelText('视频 URL / 本地路径'), {
      target: { value: 'https://example.com/video' },
    });
    fireEvent.click(screen.getByRole('button', { name: '开始分析' }));

    await screen.findByText('等待处理');

    await screen.findByText('测试视频', {}, { timeout: 3500 });
    expect(screen.getByText((_, element) => element?.textContent === '# 测试笔记\n\n- 关键观点')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Transcript' }));
    expect(await screen.findByText('第一句 transcript')).toBeTruthy();

    const history = screen.getByRole('button', { name: /历史视频/ });
    fireEvent.click(history);
    await waitFor(() => expect(within(history).getByText('已完成')).toBeTruthy());
  });

  it('选择本地视频文件后提交上传任务', async () => {
    const fetchMock = vi.mocked(fetch);
    render(<App />);

    const file = new File(['demo'], 'demo.mp4', { type: 'video/mp4' });
    fireEvent.change(screen.getByLabelText('本地视频文件'), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole('button', { name: '开始分析' }));

    await screen.findByText('等待处理');
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(`${apiBase}/api/tasks/local-file`, expect.objectContaining({ method: 'POST' }));
    });
  });
});
