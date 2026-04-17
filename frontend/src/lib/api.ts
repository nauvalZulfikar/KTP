import { API_URL } from "./config";
import type {
  MetricsRead,
  ScheduleRunDetail,
  ScheduleRunRead,
  TaskCreate,
  TaskRead,
  TaskUpdate,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Typed via the useSWR<T> call site — return type is intentionally any.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetcher = (path: string): Promise<any> => request(path);

export const api = {
  listTasks: () => request<TaskRead[]>("/tasks"),
  listOriginalTasks: () => request<TaskRead[]>("/tasks/original"),
  getTask: (id: number) => request<TaskRead>(`/tasks/${id}`),
  createTask: (body: TaskCreate) =>
    request<TaskRead>("/tasks", { method: "POST", body: JSON.stringify(body) }),
  updateTask: (id: number, body: TaskUpdate) =>
    request<TaskRead>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTask: (id: number) => request<void>(`/tasks/${id}`, { method: "DELETE" }),

  runSchedule: (notes?: string) =>
    request<ScheduleRunRead>("/schedule/run", {
      method: "POST",
      body: JSON.stringify({ notes: notes ?? null }),
    }),
  listRuns: () => request<ScheduleRunRead[]>("/runs"),
  getRun: (id: number) => request<ScheduleRunDetail>(`/runs/${id}`),
  getRunMetrics: (id: number) => request<MetricsRead>(`/runs/${id}/metrics`),
  deleteAllRuns: () => request<void>("/runs", { method: "DELETE" }),
};
