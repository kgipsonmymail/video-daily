import axios from "axios";
import type { TaskQueueResponse, TaskQueueCreate, AutoPromptRequest } from "../types";

const BASE = "http://localhost:8000/api/tasks";

export const tasksApi = {
  list(params?: { quota_date?: string; task_type?: string; status?: string; limit?: number }) {
    const p = new URLSearchParams();
    if (params?.quota_date) p.set("quota_date", params.quota_date);
    if (params?.task_type) p.set("task_type", params.task_type);
    if (params?.status) p.set("status", params.status);
    if (params?.limit) p.set("limit", String(params.limit));
    return axios.get< TaskQueueResponse[]>(`${BASE}?${p}`).then(r => r.data);
  },

  create(data: TaskQueueCreate) {
    return axios.post< TaskQueueResponse>(BASE, data).then(r => r.data);
  },

  delete(taskId: number) {
    return axios.delete(`${BASE}/${taskId}`);
  },

  updateStatus(taskId: number, data: { status?: string; run_id?: string; error_msg?: string }) {
    return axios.patch< TaskQueueResponse>(`${BASE}/${taskId}`, data).then(r => r.data);
  },

  listHistory(direction?: string) {
    const p = direction ? `?direction=${encodeURIComponent(direction)}` : "";
    return axios.get<{ id: number; text: string; direction: string; created_at: string }[]>(
      `${BASE}/history${p}`
    ).then(r => r.data);
  },

  listDirections() {
    return axios.get< string[]>(`${BASE}/directions`).then(r => r.data);
  },

  generateAuto(data: AutoPromptRequest) {
    return axios.post<{ ok: boolean; created: number; categories: string[] }>(
      `${BASE}/auto/generate`,
      data
    ).then(r => r.data);
  },
};
