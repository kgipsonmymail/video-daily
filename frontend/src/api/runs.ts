import client from "./client";
import type { RunResponse, RunCreate, RunUpdate } from "../types";

export const runsApi = {
  list: (params?: Record<string, any>) =>
    client.get<RunResponse[]>("/runs", { params }).then((r) => r.data),

  get: (runId: string) =>
    client.get<RunResponse>(`/runs/${runId}`).then((r) => r.data),

  create: (data: RunCreate) =>
    client.post<RunResponse>("/runs", data).then((r) => r.data),

  update: (runId: string, data: RunUpdate) =>
    client.patch<RunResponse>(`/runs/${runId}`, data).then((r) => r.data),

  toggleFavorite: (runId: string) =>
    client.post<RunResponse>(`/runs/${runId}/toggle-favorite`).then((r) => r.data),
};
