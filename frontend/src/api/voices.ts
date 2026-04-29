import client from "./client";
import type { VoiceSampleResponse, VoiceSampleCreate } from "../types";

export const voicesApi = {
  list(params?: { lang?: string; favorites_only?: boolean; limit?: number }) {
    return client
      .get<unknown, VoiceSampleResponse[]>("/voices", { params })
      .then((r) => r.data);
  },

  create(data: VoiceSampleCreate) {
    return client
      .post<unknown, VoiceSampleResponse>("/voices", data)
      .then((r) => r.data);
  },

  update(id: number, data: { notes?: string; is_favorite?: boolean }) {
    return client
      .patch<unknown, VoiceSampleResponse>(`/voices/${id}`, data)
      .then((r) => r.data);
  },

  delete(id: number) {
    return client.delete(`/voices/${id}`).then((r) => r.data);
  },
};
