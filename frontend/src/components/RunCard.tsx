import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { RunResponse, AssetResponse } from "../types";
import { runsApi } from "../api/runs";
import AssetCard from "./AssetCard";

interface Props {
  run: RunResponse;
  assets: AssetResponse[];
  modality: string;
}

export default function RunCard({ run, assets, modality }: Props) {
  const [expanded, setExpanded] = useState(false);
  const queryClient = useQueryClient();

  const favMutation = useMutation({
    mutationFn: () => runsApi.toggleFavorite(run.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["runs"] }),
  });

  const filtered = modality === "all"
    ? assets
    : assets.filter((a) => a.modality === modality);

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.70)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255,255,255,0.8)",
        borderRadius: 18,
        overflow: "hidden",
        boxShadow: "0 4px 20px rgba(100,90,120,0.07)",
        marginBottom: 12,
        transition: "box-shadow 0.2s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.boxShadow = "0 8px 36px rgba(100,90,120,0.13)")}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "0 4px 20px rgba(100,90,120,0.07)")}
    >
      {/* 任务头部 — 可点击展开 */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          padding: "14px 20px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: expanded ? "rgba(245,240,252,0.6)" : "rgba(255,255,255,0.3)",
          borderBottom: expanded ? "1px solid rgba(200,195,215,0.25)" : "1px solid transparent",
          transition: "all 0.18s ease",
        }}
      >
        {/* 收藏按钮 */}
        <button
          onClick={(e) => { e.stopPropagation(); favMutation.mutate(); }}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 18,
            padding: 0,
            lineHeight: 1,
            filter: run.is_favorite ? "none" : "grayscale(0.3)",
            transition: "filter 0.2s",
          }}
        >
          {run.is_favorite ? "⭐" : "☆"}
        </button>

        {/* 状态图标 */}
        <span style={{ fontSize: 15 }}>
          {run.status === "success" ? "✅" : "❌"}
        </span>

        {/* run ID */}
        <span style={{ fontFamily: "monospace", fontSize: 12, color: "#6b6375", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {run.id}
        </span>

        {/* 标签 */}
        <span style={{
          fontSize: 11, fontWeight: 600,
          padding: "3px 10px", borderRadius: 50,
          background: "rgba(155,114,207,0.1)", color: "#9b72cf",
        }}>
          {run.category}
        </span>
        <span style={{ fontSize: 12, color: "#8a8394" }}>{run.model}</span>

        {/* 资产数量 */}
        <span style={{ fontSize: 11, color: "#bdb9c8" }}>
          {run.asset_count} 个资产
        </span>

        {/* 时间 */}
        <span style={{ fontSize: 11, color: "#bdb9c8", whiteSpace: "nowrap" }}>
          {new Date(run.created_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
        </span>

        {/* 展开箭头 */}
        <span style={{ color: "#c4bfd0", fontSize: 11, transition: "transform 0.2s", transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }}>
          ▼
        </span>
      </div>

      {/* 展开内容 */}
      {expanded && (
        <div style={{ padding: "16px 20px", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
          {filtered.length === 0 ? (
            <div style={{ color: "#bdb9c8", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
              暂无匹配类型的资产
            </div>
          ) : (
            filtered.map((asset) => <AssetCard key={asset.id} asset={asset} />)
          )}
        </div>
      )}
    </div>
  );
}
