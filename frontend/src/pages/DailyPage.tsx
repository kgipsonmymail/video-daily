import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { runsApi } from "../api/runs";
import { assetsApi } from "../api/assets";
import { quotasApi } from "../api/quotas";
import RunCard from "../components/RunCard";
import type { Modality } from "../types";

const TODAY = new Date().toISOString().split("T")[0];

interface Props {
  modality: Modality;
  favoritesOnly: boolean;
}

// 按 model 分组的 run + collapse 状态
interface ModelGroup {
  model: string;
  bucket_name: string;
  used: number;
  daily_limit: number;
  remaining: number;
  collapsed: boolean;
  runs: any[];
}

// 额度说明小字（按 model 或 bucket_name 匹配）
const QUOTA_HINTS: Record<string, string> = {
  "Text to Speech HD": "字符数/日",
  "image-01": "张数/日",
  "Hailuo-2.3-768P 6s": "次数/日",
  "Hailuo-2.3-Fast-768P 6s": "次数/日",
  "music-2.5": "次数/日",
  "music-2.6": "次数/日",
  "music-cover": "次数/日",
  "lyrics_generation": "次数/日",
};

export default function DailyPage({ modality, favoritesOnly }: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const { data: quotas = [] } = useQuery({
    queryKey: ["quotas", TODAY],
    queryFn: () => quotasApi.listAll(TODAY),
  });

  const { data: runs = [] } = useQuery({
    queryKey: ["runs", "daily", { quota_date: TODAY, favorites_only: favoritesOnly }],
    queryFn: () => runsApi.list({ quota_date: TODAY, favorites_only: favoritesOnly, limit: 200 }),
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["assets", "daily", { quota_date: TODAY, modality, favorites_only: favoritesOnly }],
    queryFn: () =>
      assetsApi.list({
        quota_date: TODAY,
        modality: modality === "all" ? undefined : modality,
        favorites_only: favoritesOnly,
        limit: 500,
      }),
  });

  // runs 按 run_id 分组 assets
  const byRun = new Map<string, typeof assets>();
  for (const a of assets) {
    if (!byRun.has(a.run_id)) byRun.set(a.run_id, []);
    byRun.get(a.run_id)!.push(a);
  }

  // 构建分组：每个 quota (model) 下挂属于它的 runs
  const groups: ModelGroup[] = quotas.map((q) => ({
    model: q.model,
    bucket_name: q.bucket_name,
    used: q.used,
    daily_limit: q.daily_limit,
    remaining: q.remaining,
    collapsed: collapsed[q.model] ?? false,
    runs: runs.filter((r) => r.model === q.model),
  }));

  function toggleModel(model: string) {
    setCollapsed((prev) => ({ ...prev, [model]: !prev[model] }));
  }

  const totalRuns = runs.length;
  const totalAssets = assets.length;

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", marginBottom: 4 }}>
          📅 每日界面
        </h2>
        <p style={{ fontSize: 13, color: "#bdb9c8" }}>
          {TODAY} · 共 {totalRuns} 个任务 · {totalAssets} 条资产
        </p>
      </div>

      {/* 今日额度 — 整体折叠 */}
      {quotas.length === 0 && (
        <div
          style={{
            background: "rgba(255,255,255,0.45)",
            borderRadius: 16, padding: "20px 24px", marginBottom: 24,
            border: "1px dashed rgba(200,195,215,0.4)",
            fontSize: 13, color: "#bdb9c8",
          }}
        >
          今日尚无额度记录
        </div>
      )}

      {groups.map((g) => {
        const pct = g.daily_limit > 0 ? g.used / g.daily_limit : 0;
        const icon = g.remaining === 0 ? "🔴" : g.remaining < g.daily_limit * 0.3 ? "🟡" : "🟢";
        const hint = QUOTA_HINTS[g.bucket_name] || QUOTA_HINTS[g.model] || "";

        return (
          <div
            key={g.model}
            style={{
              background: "rgba(255,255,255,0.68)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              border: "1px solid rgba(255,255,255,0.8)",
              borderRadius: 18,
              padding: "18px 22px",
              marginBottom: 12,
              boxShadow: "0 4px 24px rgba(100,90,120,0.08)",
            }}
          >
            {/* 额度标题行 + 折叠按钮 */}
            <div
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              onClick={() => toggleModel(g.model)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13 }}>{icon}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#3d3545" }}>
                  {g.bucket_name}
                </span>
                <span style={{ fontSize: 11, color: "#bdb9c8" }}>
                  {g.used}/{g.daily_limit} · 剩余 {g.remaining}
                </span>
                {hint && (
                  <span style={{ fontSize: 10, color: "#c8c4d4", background: "rgba(200,195,215,0.25)", padding: "1px 5px", borderRadius: 4 }}>
                    {hint}
                  </span>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 11, color: "#bdb9c8" }}>
                  {g.collapsed ? `${g.runs.length} 个任务` : ""}
                </span>
                <button
                  style={{
                    background: "none", border: "none", fontSize: 13, cursor: "pointer",
                    color: "#9b72cf", padding: "2px 6px",
                  }}
                >
                  {g.collapsed ? "▶" : "▼"}
                </button>
              </div>
            </div>

            {/* 进度条 */}
            <div style={{ height: 4, borderRadius: 2, background: "rgba(200,195,215,0.3)", margin: "8px 0 12px" }}>
              <div style={{ width: `${pct * 100}%`, height: "100%", borderRadius: 2, background: icon === "🔴" ? "#d98a8a" : icon === "🟡" ? "#e8c84a" : "#7ab89a", transition: "width 0.3s" }} />
            </div>

            {/* 折叠的任务列表 */}
            {!g.collapsed && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {g.runs.length === 0 && (
                  <div style={{ fontSize: 12, color: "#bdb9c8", textAlign: "center", padding: "8px 0" }}>
                    暂无记录
                  </div>
                )}
                {g.runs.map((run) => (
                  <RunCard
                    key={run.id}
                    run={run}
                    assets={byRun.get(run.id) ?? []}
                    modality={modality}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
