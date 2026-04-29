import { useNavigate } from "react-router-dom";
import type { Page, Modality } from "../types";

const PAGES: { id: Page; label: string; icon: string }[] = [
  { id: "tasks", label: "用户任务", icon: "📋" },
  { id: "queue", label: "任务队列", icon: "📤" },
  { id: "matrix", label: "素材矩阵", icon: "🎮" },
  { id: "music", label: "音乐生成", icon: "🎵" },
  { id: "query", label: "查询历史", icon: "🔍" },
  { id: "daily", label: "每日界面", icon: "📅" },
  { id: "voices", label: "音色管理", icon: "🎙️" },
];

const MODS: { id: Modality; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "image", label: "图片" },
  { id: "music", label: "音乐" },
  { id: "video", label: "视频" },
];

interface Props {
  page: Page;
  modality: Modality;
  onModalityChange: (m: Modality) => void;
  favoritesOnly: boolean;
  onFavoritesChange: (v: boolean) => void;
  children: React.ReactNode;
}

export default function Layout({ page, modality, onModalityChange, favoritesOnly, onFavoritesChange, children }: Props) {
  const navigate = useNavigate();

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* 侧边栏 — 毛玻璃风格 */}
      <aside
        style={{
          width: 240,
          flexShrink: 0,
          background: "rgba(245, 243, 238, 0.82)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderRight: "1px solid rgba(255,255,255,0.6)",
          padding: "28px 20px",
          display: "flex",
          flexDirection: "column",
          gap: 24,
          position: "sticky",
          top: 0,
          height: "100vh",
          overflowY: "auto",
        }}
      >
        {/* Logo 区域 */}
        <div style={{ padding: "0 4px" }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", letterSpacing: "-0.3px" }}>
            🌿 Video Daily
          </div>
          <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 3 }}>
            巨树世界 · 每日灵感
          </div>
        </div>

        <div style={{ height: 1, background: "rgba(200,195,215,0.3)" }} />

        {/* 页面导航 */}
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 11, color: "#bdb9c8", padding: "0 8px", marginBottom: 4, fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase" }}>
            导航
          </div>
          {PAGES.map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/${p.id}`)}
              style={{
                padding: "10px 14px",
                borderRadius: 12,
                cursor: "pointer",
                background: page === p.id
                  ? "linear-gradient(135deg, rgba(155,114,207,0.18), rgba(196,174,226,0.12))"
                  : "transparent",
                color: page === p.id ? "#7b4fc4" : "#8a8394",
                fontWeight: page === p.id ? 600 : 400,
                fontSize: 14,
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.18s ease",
                border: page === p.id ? "1px solid rgba(155,114,207,0.25)" : "1px solid transparent",
              }}
            >
              <span style={{ fontSize: 16 }}>{p.icon}</span>
              {p.label}
            </div>
          ))}
        </nav>

        <div style={{ height: 1, background: "rgba(200,195,215,0.3)" }} />

        {/* 类型快速切换 */}
        <div>
          <div style={{ fontSize: 11, color: "#bdb9c8", padding: "0 8px", marginBottom: 8, fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase" }}>
            类型
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            {MODS.map((m) => (
              <div
                key={m.id}
                onClick={() => onModalityChange(m.id)}
                style={{
                  padding: "7px 0",
                  textAlign: "center",
                  borderRadius: 10,
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 500,
                  background: modality === m.id
                    ? "linear-gradient(135deg, rgba(155,114,207,0.22), rgba(196,174,226,0.15))"
                    : "rgba(255,255,255,0.5)",
                  color: modality === m.id ? "#7b4fc4" : "#8a8394",
                  border: modality === m.id ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.3)",
                  transition: "all 0.18s ease",
                }}
              >
                {m.label}
              </div>
            ))}
          </div>
        </div>

        <div style={{ height: 1, background: "rgba(200,195,215,0.3)" }} />

        {/* 收藏筛选 */}
        <div
          onClick={() => onFavoritesChange(!favoritesOnly)}
          style={{
            padding: "10px 14px",
            borderRadius: 12,
            cursor: "pointer",
            background: favoritesOnly ? "rgba(255,214,122,0.15)" : "rgba(255,255,255,0.5)",
            border: favoritesOnly ? "1px solid rgba(224,184,122,0.35)" : "1px solid rgba(200,195,215,0.3)",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 13,
            color: favoritesOnly ? "#c4882a" : "#8a8394",
            fontWeight: favoritesOnly ? 600 : 400,
            transition: "all 0.18s ease",
          }}
        >
          <span style={{ fontSize: 16 }}>{favoritesOnly ? "⭐" : "☆"}</span>
          只看收藏
        </div>
      </aside>

      {/* 主内容区 */}
      <main
        style={{
          flex: 1,
          padding: "36px 44px",
          overflowY: "auto",
          maxWidth: "calc(100vw - 240px)",
        }}
      >
        {children}
      </main>
    </div>
  );
}
