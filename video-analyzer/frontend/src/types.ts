export type TaskStatus =
  | 'pending'
  | 'fetching_subtitle'
  | 'downloading_audio'
  | 'transcribing'
  | 'summarizing'
  | 'merging'
  | 'succeeded'
  | 'failed';

export type CreateTaskRequest = {
  url: string;
  platform?: string;
  note_style?: string;
  model?: string;
};

export type CreateLocalFileTaskRequest = {
  file?: File;
  path?: string;
  note_style?: string;
  model?: string;
};

export type CreateTaskResponse = {
  task_id: string;
  status: TaskStatus;
};

export type TaskSummary = {
  task_id: string;
  status: TaskStatus;
  message?: string;
  title?: string;
  source_url?: string;
  created_at?: string;
  updated_at?: string;
  has_transcript?: boolean;
  has_note?: boolean;
};

export type HistoryItem = {
  task_id: string;
  status: TaskStatus;
  title?: string;
  source_url?: string;
  created_at?: string;
};

export type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
};

export type TranscriptResponse = {
  task_id: string;
  language?: string;
  full_text?: string;
  segments: TranscriptSegment[];
};

export type NoteResponse = {
  task_id: string;
  markdown: string;
};
