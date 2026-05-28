import { useState, useEffect } from "react";
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 检测屏幕尺寸
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setSidebarOpen(false); // 桌面端自动关闭抽屉
      }
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // 页面切换时关闭侧边栏
  const handleNavigate = (pageId: Page) => {
    navigate(`/${pageId}`);
    if (isMobile) setSidebarOpen(false);
  };

  // 侧边栏样式
  const sidebarStyle: React.CSSProperties = isMobile
    ? {
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 1000,
        width: 280,
        height: "100vh",
        background: "rgba(245, 243, 238, 0.95)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderRight: "1px solid rgba(255,255,255,0.6)",
        padding: "28px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 24,
        overflowY: "auto",
        transform: sidebarOpen ? "translateX(0)" : "translateX(-100%)",
        transition: "transform 0.3s ease",
        boxShadow: sidebarOpen ? "4px 0 24px rgba(0,0,0,0.1)" : "none",
      }
    : {
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
      };

  // 主内容区样式
  const mainStyle: React.CSSProperties = isMobile
    ? {
        flex: 1,
        padding: "16px",
        paddingTop: "60px", // 为顶部汉堡按钮留空间
        overflowY: "auto",
        width: "100%",
      }
    : {
        flex: 1,
        padding: "36px 44px",
        overflowY: "auto",
        maxWidth: "calc(100vw - 240px)",
      };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* 移动端顶部栏 */}
      {isMobile && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            zIndex: 999,
            height: 56,
            background: "rgba(245, 243, 238, 0.9)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            borderBottom: "1px solid rgba(200,195,215,0.3)",
            display: "flex",
            alignItems: "center",
            padding: "0 16px",
            gap: 12,
          }}
        >
          {/* 汉堡菜单按钮 */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 8,
              borderRadius: 8,
              display: "flex",
              flexDirection: "column",
              gap: 5,
              width: 40,
              height: 40,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <span
              style={{
                display: "block",
                width: 20,
                height: 2,
                background: "#3d3545",
                borderRadius: 2,
                transform: sidebarOpen ? "rotate(45deg) translate(5px, 5px)" : "none",
                transition: "transform 0.3s ease",
              }}
            />
            <span
              style={{
                display: "block",
                width: 20,
                height: 2,
                background: "#3d3545",
                borderRadius: 2,
                opacity: sidebarOpen ? 0 : 1,
                transition: "opacity 0.3s ease",
              }}
            />
            <span
              style={{
                display: "block",
                width: 20,
                height: 2,
                background: "#3d3545",
                borderRadius: 2,
                transform: sidebarOpen ? "rotate(-45deg) translate(5px, -5px)" : "none",
                transition: "transform 0.3s ease",
              }}
            />
          </button>

          {/* Logo */}
          <div style={{ fontSize: 18, fontWeight: 700, color: "#3d3545" }}>
            🌿 Video Daily
          </div>
        </div>
      )}

      {/* 遮罩层（移动端） */}
      {isMobile && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 999,
            background: "rgba(0,0,0,0.3)",
            backdropFilter: "blur(4px)",
          }}
        />
      )}

      {/* 侧边栏 */}
      <aside style={sidebarStyle}>
        {/* Logo 区域（桌面端显示） */}
        {!isMobile && (
          <div style={{ padding: "0 4px" }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", letterSpacing: "-0.3px" }}>
              🌿 Video Daily
            </div>
            <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 3 }}>
              巨树世界 · 每日灵感
            </div>
          </div>
        )}

        {/* 移动端侧边栏头部 */}
        {isMobile && (
          <div style={{ padding: "0 4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#3d3545" }}>
                🌿 Video Daily
              </div>
              <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 2 }}>
                巨树世界 · 每日灵感
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 24,
                color: "#8a8394",
                padding: 4,
              }}
            >
              ✕
            </button>
          </div>
        )}

        <div style={{ height: 1, background: "rgba(200,195,215,0.3)" }} />

        {/* 页面导航 */}
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 11, color: "#bdb9c8", padding: "0 8px", marginBottom: 4, fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase" }}>
            导航
          </div>
          {PAGES.map((p) => (
            <div
              key={p.id}
              onClick={() => handleNavigate(p.id)}
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
                onClick={() => {
                  onModalityChange(m.id);
                  if (isMobile) setSidebarOpen(false);
                }}
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
          onClick={() => {
            onFavoritesChange(!favoritesOnly);
            if (isMobile) setSidebarOpen(false);
          }}
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
      <main style={mainStyle}>
        {children}
      </main>
    </div>
  );
}
