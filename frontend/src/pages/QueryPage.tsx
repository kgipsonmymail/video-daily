import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { assetsApi } from "../api/assets";
import AssetCard from "../components/AssetCard";
import type { Modality } from "../types";

const CATEGORIES = [
  { id: "", label: "全部" },
  { id: "t2i", label: "文生图" },
  { id: "i2i", label: "图生图" },
  { id: "t2v", label: "文生视频" },
  { id: "i2v", label: "图生视频" },
  { id: "fl2v", label: "首尾帧" },
  { id: "s2v", label: "主体参考" },
  { id: "music", label: "音乐" },
];

interface Props {
  modality: Modality;
  favoritesOnly: boolean;
}

export default function QueryPage({ modality, favoritesOnly }: Props) {
  const [searchText, setSearchText] = useState("");
  const [category, setCategory] = useState("");

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["assets", "query", { modality, search_text: searchText, favorites_only: favoritesOnly, category }],
    queryFn: () =>
      assetsApi.list({
        modality: modality === "all" ? undefined : modality,
        search_text: searchText || undefined,
        favorites_only: favoritesOnly,
        category: category || undefined,
        limit: 300,
      }),
  });

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", marginBottom: 4 }}>
          🔍 查询历史
        </h2>
        <p style={{ fontSize: 13, color: "#bdb9c8" }}>
          搜索提示词，研究不同生成效果的差异
        </p>
      </div>

      {/* 搜索框 */}
      <div style={{ marginBottom: 16, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <input
          type="text"
          placeholder="输入提示词关键词..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="input"
          style={{ maxWidth: 320 }}
        />
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              style={{
                padding: "5px 12px",
                borderRadius: 20,
                border: category === c.id
                  ? "1px solid rgba(155,114,207,0.5)"
                  : "1px solid rgba(200,195,215,0.35)",
                background: category === c.id ? "rgba(155,114,207,0.12)" : "rgba(255,255,255,0.5)",
                color: category === c.id ? "#7b4fc4" : "#8a8394",
                fontSize: 12,
                cursor: "pointer",
                fontWeight: category === c.id ? 600 : 400,
              }}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#bdb9c8" }}>搜索中...</div>
      )}

      {!isLoading && assets.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 0",
            background: "rgba(255,255,255,0.45)",
            borderRadius: 20,
            border: "1px dashed rgba(200,195,215,0.4)",
          }}
        >
          <div style={{ fontSize: 36, marginBottom: 10 }}>🔎</div>
          <div style={{ fontSize: 14, color: "#8a8394" }}>
            {searchText ? "没有找到匹配的记录" : "输入关键词开始搜索"}
          </div>
        </div>
      )}

      {!isLoading && assets.length > 0 && (
        <>
          <div style={{ fontSize: 12, color: "#bdb9c8", marginBottom: 16 }}>
            找到 {assets.length} 条资产
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
            {assets.map((asset) => (
              <AssetCard key={asset.id} asset={asset} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
