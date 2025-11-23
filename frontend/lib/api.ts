const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type HarnessType = 'harbor' | 'terminus';
export type ModelType = 'openai/gpt-4o' | 'anthropic/claude-3.5-sonnet' | 'google/gemini-pro-1.5' | 'meta-llama/llama-3.1-405b-instruct';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Run {
  id: string;
  job_id: string;
  run_number: number;
  status: JobStatus;
  tests_passed: number | null;
  tests_total: number | null;
  logs: string | null;
  result_path: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface Job {
  id: string;
  task_name: string;
  status: JobStatus;
  harness: string;
  model: string;
  created_at: string;
  completed_at: string | null;
  runs: Run[];
}

export interface UploadResponse {
  job_id: string;
  status: string;
  runs_queued: number;
  message: string;
}

export interface JobSummary {
  id: string;
  task_name: string;
  status: JobStatus;
  harness: string;
  model: string;
  created_at: string;
  completed_at: string | null;
  runs: Run[];
}

export async function uploadTask(
  file: File,
  harness: HarnessType,
  model: ModelType,
  openrouterKey: string,
  nRuns: number = 10
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('harness', harness);
  formData.append('model', model);
  formData.append('openrouter_key', openrouterKey);
  formData.append('n_runs', nRuns.toString());
  
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Upload failed');
  }
  
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  
  if (!res.ok) {
    throw new Error('Failed to fetch job');
  }
  
  return res.json();
}

export async function listJobs(limit: number = 100, offset: number = 0): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/api/jobs?limit=${limit}&offset=${offset}`);
  
  if (!res.ok) {
    throw new Error('Failed to fetch jobs');
  }
  
  return res.json();
}

export async function uploadTasksBatch(
  files: File[],
  harness: HarnessType,
  model: ModelType,
  openrouterKey: string,
  nRuns: number = 10
): Promise<UploadResponse[]> {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('harness', harness);
  formData.append('model', model);
  formData.append('openrouter_key', openrouterKey);
  formData.append('n_runs', nRuns.toString());
  
  const res = await fetch(`${API_BASE}/api/upload/batch`, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Batch upload failed');
  }
  
  return res.json();
}

export function streamLogs(
  jobId: string,
  runNumber: number,
  onLog: (logs: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): () => void {
  const eventSource = new EventSource(
    `${API_BASE}/api/jobs/${jobId}/runs/${runNumber}/logs/stream`
  );
  
  let accumulatedLogs = '';
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.logs) {
        accumulatedLogs += data.logs;
        onLog(accumulatedLogs);
      }
      if (data.status === 'complete') {
        eventSource.close();
        onComplete?.();
      }
    } catch (error) {
      onError?.(error as Error);
    }
  };
  
  eventSource.onerror = (error) => {
    eventSource.close();
    onError?.(new Error('EventSource error occurred'));
  };
  
  return () => eventSource.close();
}

