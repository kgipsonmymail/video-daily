import { useQuery } from "@tanstack/react-query";
import { runsApi } from "../api/runs";
import { assetsApi } from "../api/assets";
import RunCard from "../components/RunCard";
import type { Modality } from "../types";

interface Props {
  modality: Modality;
  favoritesOnly: boolean;
}

export default function TasksPage({ modality, favoritesOnly }: Props) {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["runs", { favorites_only: favoritesOnly }],
    queryFn: () => runsApi.list({ favorites_only: favoritesOnly, limit: 200 }),
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["assets", { modality, favorites_only: favoritesOnly }],
    queryFn: () =>
      assetsApi.list({
        modality: modality === "all" ? undefined : modality,
        favorites_only: favoritesOnly,
        limit: 500,
      }),
  });

  const byRun = new Map<string, typeof assets>();
  for (const a of assets) {
    if (!byRun.has(a.run_id)) byRun.set(a.run_id, []);
    byRun.get(a.run_id)!.push(a);
  }

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", marginBottom: 4 }}>
          📋 用户任务
        </h2>
        <p style={{ fontSize: 13, color: "#bdb9c8" }}>
          共 {runs.length} 个任务 · {assets.length} 条资产
        </p>
      </div>

      {isLoading && (
        <div style={{ textAlign: "center", padding: "60px 0", color: "#bdb9c8" }}>
          加载中...
        </div>
      )}

      {!isLoading && runs.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "80px 0",
            background: "rgba(255,255,255,0.5)",
            borderRadius: 20,
            border: "1px dashed rgba(200,195,215,0.4)",
          }}
        >
          <div style={{ fontSize: 40, marginBottom: 12 }}>🌿</div>
          <div style={{ fontSize: 15, color: "#8a8394", fontWeight: 500 }}>暂无任务记录</div>
          <div style={{ fontSize: 12, color: "#bdb9c8", marginTop: 6 }}>
            运行 pipeline 后这里会出现生成结果
          </div>
        </div>
      )}

      {runs.map((run) => (
        <RunCard
          key={run.id}
          run={run}
          assets={byRun.get(run.id) ?? []}
          modality={modality}
        />
      ))}
    </div>
  );
}
