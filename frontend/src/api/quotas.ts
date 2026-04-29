import client from "./client";
import type { QuotaResponse, QuotaCreate } from "../types";

export const quotasApi = {
  list: (quotaDate?: string) =>
    client.get<QuotaResponse[]>("/quotas", { params: { quota_date: quotaDate } }).then((r) => r.data),

  /** 返回所有已知额度类型（含 DB 记录和未记录的占位） */
  listAll: (quotaDate?: string) =>
    client.get<QuotaResponse[]>("/quotas/all", { params: { quota_date: quotaDate } }).then((r) => r.data),

  /** 初始化当天所有额度记录到 DB */
  initAll: (quotaDate?: string) =>
    client.post<QuotaResponse[]>("/quotas/init", null, { params: { quota_date: quotaDate } }).then((r) => r.data),

  upsert: (data: QuotaCreate) =>
    client.post<QuotaResponse>("/quotas", data).then((r) => r.data),
};
