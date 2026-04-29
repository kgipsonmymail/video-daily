import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { assetsApi } from "../api/assets";
import type { AssetResponse, Modality } from "../types";

const FILE_BASE = "http://localhost:8000/files";

interface Props {
  modality: Modality;
  onSelect: (asset: AssetResponse) => void;
  onClose: () => void;
}

export default function AssetPickerDialog({ modality, onSelect, onClose }: Props) {
  const [search, setSearch] = useState("");

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["assets", "picker", modality],
    queryFn: () => assetsApi.list({ modality, limit: 300 }),
  });

  const filtered = search
    ? assets.filter((a) =>
        a.prompt_text?.toLowerCase().includes(search.toLowerCase())
      )
    : assets;

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 500,
        background: "rgba(10,8,18,0.6)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "rgba(255,255,255,0.95)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.8)",
          borderRadius: 20,
          width: "100%",
          maxWidth: 720,
          maxHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div style={{
          padding: "18px 20px 14px",
          borderBottom: "1px solid rgba(200,195,215,0.3)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#3d3545" }}>
            选择参考图片
          </span>
          <button onClick={onClose} style={{
            background: "none", border: "none", fontSize: 18,
            cursor: "pointer", color: "#8a8394",
          }}>✕</button>
        </div>

        {/* Search */}
        <div style={{ padding: "12px 20px" }}>
          <input
            type="text"
            placeholder="搜索提示词..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input"
            style={{ width: "100%", boxSizing: "border-box" }}
          />
        </div>

        {/* Grid */}
        <div style={{
          flex: 1, overflowY: "auto",
          padding: "0 20px 16px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
          gap: 10,
          alignContent: "start",
        }}>
          {isLoading && (
            <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 20, color: "#bdb9c8" }}>
              加载中...
            </div>
          )}
          {!isLoading && filtered.length === 0 && (
            <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 20, color: "#bdb9c8" }}>
              {search ? "没有匹配的资产" : "暂无可用资产"}
            </div>
          )}
          {filtered.map((asset) => (
            <div
              key={asset.id}
              onClick={() => onSelect(asset)}
              style={{
                borderRadius: 12, overflow: "hidden",
                border: "2px solid transparent",
                cursor: "pointer",
                transition: "border-color 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(155,114,207,0.5)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "transparent")}
            >
              {asset.modality === "image" ? (
                <img
                  src={`${FILE_BASE}/${asset.file_path}`}
                  alt=""
                  style={{ width: "100%", height: 100, objectFit: "cover", display: "block" }}
                />
              ) : (
                <div style={{ width: "100%", height: 100, background: "#f0eee8", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "#bdb9c8" }}>
                  {asset.modality}
                </div>
              )}
              <div style={{
                padding: "6px 8px",
                fontSize: 10.5, color: "#8a8394",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                background: "rgba(255,255,255,0.8)",
              }}>
                {asset.sub_type || asset.modality}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
