import client from "./client";
import type { AssetResponse, AssetCreate, AssetUpdate } from "../types";

export const assetsApi = {
  list: (params?: Record<string, any>) =>
    client.get<AssetResponse[]>("/assets", { params }).then((r) => r.data),

  get: (assetId: number) =>
    client.get<AssetResponse>(`/assets/${assetId}`).then((r) => r.data),

  create: (data: AssetCreate) =>
    client.post<AssetResponse>("/assets", data).then((r) => r.data),

  update: (assetId: number, data: AssetUpdate) =>
    client.patch<AssetResponse>(`/assets/${assetId}`, data).then((r) => r.data),
};
