import { useState, useEffect } from "react";
import type { AssetResponse } from "../types";

const FILE_BASE = "http://localhost:8000/files";

function fileUrl(fp: string) {
  return `${FILE_BASE}/${fp}`;
}

function ImageLightbox({ src, onClose }: { src: string; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(10,8,18,0.95)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center",
        cursor: "zoom-out",
        padding: "40px",
        boxSizing: "border-box",
      }}
    >
      <img
        src={src}
        alt=""
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: "100%",
          maxHeight: "100%",
          objectFit: "contain",
          display: "block",
          borderRadius: 8,
          boxShadow: "0 0 60px rgba(0,0,0,0.6)",
        }}
      />
      <button
        onClick={onClose}
        style={{
          position: "absolute", top: 16, right: 20,
          background: "rgba(255,255,255,0.1)",
          border: "1px solid rgba(255,255,255,0.18)",
          borderRadius: 50,
          width: 44, height: 44,
          fontSize: 20, color: "#fff",
          cursor: "pointer", lineHeight: 1,
          backdropFilter: "blur(8px)",
        }}
      >
        ✕
      </button>
    </div>
  );
}

function ModalityBadge({ sub }: { sub: string | null }) {
  const labels: Record<string, string> = {
    t2i: "文生图", i2i: "图生图", t2v: "文生视频", i2v: "图生视频",
    image: "图片", video: "视频", music: "音乐",
  };
  const clsMap: Record<string, string> = {
    t2i: "badge-t2i", i2i: "badge-i2i", t2v: "badge-t2v", i2v: "badge-video",
    image: "badge-image", video: "badge-video", music: "badge-music",
  };
  const cls = sub || "";
  return (
    <span className={`badge ${clsMap[cls] || "badge-image"}`}>
      {labels[cls] || cls}
    </span>
  );
}

export default function AssetCard({ asset }: { asset: AssetResponse }) {
  const [promptOpen, setPromptOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  const imgSrc = fileUrl(asset.file_path);

  return (
    <>
      {lightboxSrc && (
        <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      <div
        style={{
          background: "rgba(255,255,255,0.68)",
          backdropFilter: "blur(18px)",
          WebkitBackdropFilter: "blur(18px)",
          border: "1px solid rgba(255,255,255,0.8)",
          borderRadius: 18,
          padding: 18,
          boxShadow: "0 4px 24px rgba(100,90,120,0.08)",
          transition: "box-shadow 0.2s ease",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.boxShadow = "0 8px 36px rgba(100,90,120,0.14)")}
        onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "0 4px 24px rgba(100,90,120,0.08)")}
      >
        {/* 媒体展示 */}
        <div style={{ borderRadius: 12, overflow: "hidden", marginBottom: 14, background: "#f0eee8" }}>
          {asset.modality === "image" && !imgError && (
            <img
              src={imgSrc}
              alt={asset.sub_type || asset.modality}
              style={{ width: "100%", display: "block", maxHeight: 300, objectFit: "cover", cursor: "zoom-in" }}
              onError={() => setImgError(true)}
              onClick={() => setLightboxSrc(imgSrc)}
            />
          )}
          {imgError && (
            <div style={{ padding: "32px 0", textAlign: "center", color: "#bdb9c8", fontSize: 13 }}>
              图片加载失败
            </div>
          )}
          {asset.modality === "video" && (
            <video controls style={{ width: "100%", borderRadius: 12 }}>
              <source src={fileUrl(asset.file_path)} />
            </video>
          )}
          {asset.modality === "music" && (
            <div style={{ padding: "20px", textAlign: "center", background: "rgba(155,114,207,0.06)", borderRadius: 12 }}>
              <audio controls style={{ width: "100%" }}>
                <source src={fileUrl(asset.file_path)} />
              </audio>
            </div>
          )}
        </div>

        {/* 元信息 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <ModalityBadge sub={asset.sub_type} />
            <span style={{ fontSize: 12, color: "#8a8394" }}>{asset.model}</span>
            <span style={{ fontSize: 11, color: asset.status === "success" ? "#7ab89a" : "#d98a8a" }}>
              {asset.status === "success" ? "成功" : "失败"}
            </span>
          </div>

          {asset.seed !== null && (
            <div style={{ fontSize: 11, color: "#bdb9c8" }}>
              Seed <span style={{ fontFamily: "monospace", fontSize: 11 }}>{asset.seed}</span>
            </div>
          )}
          {asset.aspect_ratio && (
            <div style={{ fontSize: 11, color: "#bdb9c8" }}>比例 {asset.aspect_ratio}</div>
          )}

          <div style={{ fontSize: 10.5, color: "#c4bfd0", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {asset.run_id}
          </div>

          {asset.external_url && (
            <a href={asset.external_url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: 12, color: "#9b72cf", textDecoration: "none" }}>
              🔗 云盘链接
            </a>
          )}

          {/* 提示词 */}
          <div style={{ marginTop: 2 }}>
            <button
              onClick={() => setPromptOpen(!promptOpen)}
              style={{
                background: promptOpen ? "rgba(155,114,207,0.12)" : "rgba(255,255,255,0.55)",
                border: "1px solid rgba(155,114,207,0.22)",
                borderRadius: 50,
                padding: "5px 14px",
                fontSize: 12,
                color: "#9b72cf",
                cursor: "pointer",
                transition: "all 0.18s ease",
                fontFamily: "var(--font-main)",
              }}
            >
              {promptOpen ? "收起提示词" : "查看提示词"}
            </button>
            {promptOpen && (
              <div style={{
                marginTop: 10,
                padding: "12px 14px",
                background: "rgba(250,248,244,0.92)",
                borderRadius: 12,
                fontSize: 12.5,
                color: "#5a5470",
                lineHeight: 1.75,
                whiteSpace: "pre-wrap",
                border: "1px solid rgba(200,195,215,0.3)",
              }}>
                {asset.prompt_text || "（无提示词）"}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
