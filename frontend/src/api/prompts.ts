import client from "./client";
import type { PromptResponse, PromptCreate } from "../types";

export const promptsApi = {
  list: (params?: Record<string, any>) =>
    client.get<PromptResponse[]>("/prompts", { params }).then((r) => r.data),

  get: (promptId: number) =>
    client.get<PromptResponse>(`/prompts/${promptId}`).then((r) => r.data),

  create: (data: PromptCreate) =>
    client.post<PromptResponse>("/prompts", data).then((r) => r.data),
};
