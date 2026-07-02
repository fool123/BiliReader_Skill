import type {
  CreateLocalFileTaskRequest,
  CreateTaskRequest,
  CreateTaskResponse,
  HistoryItem,
  NoteResponse,
  TaskSummary,
  TranscriptResponse,
} from './types';

const API_BASE_URL = 'http://localhost:8787';

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    try {
      const body = (await response.json()) as { message?: string };
      message = body.message || message;
    } catch {
      // ponytail: plain HTTP failures may not include JSON; status is enough for the UI.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  createTask(payload: CreateTaskRequest) {
    return requestJson<CreateTaskResponse>('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  async createLocalFileTask(payload: CreateLocalFileTaskRequest) {
    const form = new FormData();
    if (payload.file) form.append('file', payload.file);
    if (payload.path) form.append('path', payload.path);
    if (payload.note_style) form.append('note_style', payload.note_style);
    if (payload.model) form.append('model', payload.model);
    const response = await fetch(`${API_BASE_URL}/api/tasks/local-file`, {
      method: 'POST',
      body: form,
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { message?: string };
      throw new Error(body.message || `请求失败：${response.status}`);
    }
    return response.json() as Promise<CreateTaskResponse>;
  },
  getTask(taskId: string) {
    return requestJson<TaskSummary>(`/api/tasks/${taskId}`);
  },
  getTranscript(taskId: string) {
    return requestJson<TranscriptResponse>(`/api/tasks/${taskId}/transcript`);
  },
  getNote(taskId: string) {
    return requestJson<NoteResponse>(`/api/tasks/${taskId}/note`);
  },
  async listTasks() {
    const body = await requestJson<{ items: HistoryItem[] }>('/api/tasks');
    return body.items;
  },
};
