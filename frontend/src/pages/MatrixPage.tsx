import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { matrixApi, type MatrixConfig, type MatrixAsset, type MusicMatrixConfig } from "../api/matrix";
import { generateApi } from "../api/generate";
import { assetsApi } from "../api/assets";
import type { AssetResponse } from "../types";

const FILE_BASE = "http://localhost:8000/files";

// 工具：组合完整 prompt（支持自定义 base）
function buildPrompt(basePrompt: string, subjectLine: string, styleLine: string) {
  const base = basePrompt.trim();
  const subj = subjectLine.trim();
  const style = styleLine.trim();
  // 如果 base 末尾已有标点，直接拼接；否则加逗号
  const sep = /[.!?,;]$/.test(base) ? " " : ", ";
  return `${base}${sep}${subj}, ${style}`;
}

function parseLines(text: string): string[] {
  return text.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
}

// Maps generic variant prefixes → index of the corresponding subject in the giant-tree 6×6 config
const VARIANT_ROW_MAP: Record<string, number> = {
  human: 0,    // A brave young farmer
  npc: 1,      // A grumpy old mushroom shop keeper
  creature: 2, // A curious leaf spirit creature
  item: 3,     // An ancient brass compass
  building: 4, // A cozy cottage built inside a giant tree hollow
  scene: 5,    // A bustling morning market
};

/**
 * Parse variant string into (subject_index, style_index).
 * Variant format: "{subject_slice}-{style_slice}" where each slice
 * is the first N chars of the original line (with underscores for spaces).
 * We match against the actual subjects/styles arrays by content.
 */
function parseVariantToRowCol(
  variant: string,
  subjects: string[],
  styles: { abbr: string; full: string }[]
): { row: number; col: number } | null {
  if (!variant) return null;
  // Split on first dash only
  const dashIdx = variant.indexOf("-");
  if (dashIdx < 0) return null;
  const subjSlice = variant.slice(0, dashIdx);
  const styleSlice = variant.slice(dashIdx + 1);

  // Find subject by checking if its first N chars (N=15) match
  // or if the slice appears as a prefix of the subject
  let rowIdx = -1;
  for (let i = 0; i < subjects.length; i++) {
    const sub = subjects[i];
    const subPrefix = sub.slice(0, 20).replace(/\s/g, "_");
    if (subPrefix.startsWith(subjSlice) || subjSlice.startsWith(subPrefix.slice(0, Math.min(subjSlice.length, 10)))) {
      rowIdx = i;
      break;
    }
  }

  // Find style by checking abbr or full prefix
  let colIdx = -1;
  for (let i = 0; i < styles.length; i++) {
    const st = styles[i];
    const stPrefix = st.full.slice(0, 12).replace(/\s/g, "_");
    if (stPrefix.startsWith(styleSlice) || styleSlice.startsWith(stPrefix.slice(0, Math.min(styleSlice.length, 8)))) {
      colIdx = i;
      break;
    }
  }

  if (rowIdx < 0 || colIdx < 0) return null;
  return { row: rowIdx, col: colIdx };
}

// Legacy fallback for old giant-tree style variants
function variantToRowCol(variant: string): { row: number; col: number } | null {
  const parts = variant.split("-");
  const colStr = parts[parts.length - 1];
  const rowStr = parts.slice(0, parts.length - 1).join("-");
  const colStyles = ["fantasy", "anime", "watercolor", "pixel", "oil", "sketch"];
  const colIdx = colStyles.indexOf(colStr);
  const rowIdx = VARIANT_ROW_MAP[rowStr];
  if (rowIdx === undefined || colIdx < 0) return null;
  return { row: rowIdx, col: colIdx };
}

interface Cell {
  row: number;
  col: number;
  status: "idle" | "generating" | "done" | "error";
  asset?: MatrixAsset;
  error?: string;
}

function ImageLightbox({ src, onClose }: { src: string; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(10,8,18,0.95)",
        backdropFilter: "blur(16px)", zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center", cursor: "zoom-out",
      }}
    >
      <img src={src} alt="" onClick={(e) => e.stopPropagation()}
        style={{ width: "100vw", height: "100vh", objectFit: "contain" }} />
      <button onClick={onClose}
        style={{ position: "absolute", top: 16, right: 20, background: "rgba(255,255,255,0.1)",
          border: "1px solid rgba(255,255,255,0.18)", borderRadius: 50, width: 44, height: 44,
          fontSize: 20, color: "#fff", cursor: "pointer", lineHeight: 1 }}>
        ✕
      </button>
    </div>
  );
}

// 单格组件
function Cell({ cell, onGenerate }: { cell: Cell; onGenerate: () => void }) {
  const [lightbox, setLightbox] = useState<string | null>(null);

  const bgMap: Record<string, string> = {
    idle: "rgba(200,195,215,0.15)",
    generating: "rgba(155,114,207,0.1)",
    done: "transparent",
    error: "rgba(220,150,150,0.08)",
  };

  return (
    <>
      {lightbox && <ImageLightbox src={lightbox} onClose={() => setLightbox(null)} />}
      <div
        onClick={() => {
          if (cell.status === "done" && cell.asset) {
            setLightbox(`${FILE_BASE}/${cell.asset.file_path}`);
          }
        }}
        style={{
          height: 110, borderRadius: 10, overflow: "hidden",
          background: bgMap[cell.status],
          border: cell.status === "done"
            ? "1.5px solid rgba(155,114,207,0.3)"
            : "1.5px solid rgba(200,195,215,0.2)",
          cursor: cell.status === "done" ? "zoom-in" : "default",
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "all 0.2s", position: "relative",
        }}
      >
        {cell.status === "idle" && (
          <span style={{ fontSize: 10, color: "#c4bfd0" }}>—</span>
        )}
        {cell.status === "generating" && (
          <div style={{ fontSize: 11, color: "#9b72cf", textAlign: "center" }}>
            <div style={{ fontSize: 14 }}>⏳</div>
            <div style={{ marginTop: 3 }}>生成中</div>
          </div>
        )}
        {cell.status === "done" && cell.asset && (
          <img
            src={`${FILE_BASE}/${cell.asset.file_path}`}
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        )}
        {cell.status === "error" && (
          <div
            title={cell.error || "生成失败"}
            style={{ fontSize: 11, color: "#d98a8a", textAlign: "center", padding: 8, cursor: "help" }}>
            <div>❌</div>
            <div style={{ marginTop: 3, fontSize: 10 }}>
              {cell.error ? cell.error.slice(0, 40) : "失败"}
            </div>
          </div>
        )}
        {cell.status === "idle" && (
          <button
            onClick={(e) => { e.stopPropagation(); onGenerate(); }}
            style={{
              position: "absolute", top: 3, right: 3,
              background: "rgba(155,114,207,0.65)",
              border: "none", borderRadius: 5,
              fontSize: 9, color: "#fff", cursor: "pointer",
              padding: "2px 5px",
            }}
          >
            生成
          </button>
        )}
      </div>
    </>
  );
}

// 矩阵主体
function MatrixGrid({
  subjects, styles, cells, onGenerateCell, onGenerateAll,
}: {
  subjects: string[];
  styles: { abbr: string; full: string }[];
  cells: Record<string, Cell>;
  onGenerateCell: (r: number, c: number) => void;
  onGenerateAll: () => void;
}) {
  const doneCount = Object.values(cells).filter((c) => c.status === "done").length;
  const total = subjects.length * styles.length;
  const isRunning = Object.values(cells).some((c) => c.status === "generating");
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div>
      {/* 进度 */}
      {doneCount > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 12, color: "#8a8394", marginBottom: 5 }}>
            {doneCount}/{total} 已生成 {pct}%
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {/* 操作栏 */}
      <div style={{ display: "flex", gap: 10, marginBottom: 18, flexWrap: "wrap" }}>
        <button
          onClick={onGenerateAll}
          disabled={isRunning || subjects.length === 0}
          style={{
            padding: "9px 20px", borderRadius: 12,
            background: isRunning
              ? "rgba(155,114,207,0.4)"
              : "linear-gradient(135deg, rgba(155,114,207,0.85), rgba(196,174,226,0.65))",
            border: "none", color: "#fff", fontSize: 13, fontWeight: 600,
            cursor: isRunning ? "not-allowed" : "pointer",
          }}
        >
          {isRunning ? "生成中..." : `🚀 生成全部 ${total} 张`}
        </button>
      </div>

      {/* 表格 */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 5, minWidth: 500 }}>
          <thead>
            <tr>
              <th style={{ width: 80, padding: "0 4px 8px", fontSize: 10, color: "#bdb9c8", textAlign: "left" }} />
              {styles.map((s, ci) => (
                <th key={`img-col-${ci}`} style={{ padding: "0 0 8px" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                    <div title={s.full}
                      style={{ fontSize: 12, fontWeight: 700, color: "#7b4fc4",
                        background: "rgba(155,114,207,0.12)",
                        border: "1px solid rgba(155,114,207,0.25)",
                        borderRadius: 8, padding: "4px 10px", cursor: "help", whiteSpace: "nowrap" }}>
                      {s.abbr}
                    </div>
                    <div title={s.full}
                      style={{ fontSize: 10, color: "#9b8fc4", cursor: "help", textAlign: "center", maxWidth: 70, lineHeight: 1.3 }}>
                      {s.full.split(",")[0]}
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {subjects.map((subj, r) => (
              <tr key={r}>
                <td style={{ padding: "0 4px 0 0" }}>
                  <div title={subj}
                    style={{ background: "rgba(155,114,207,0.08)",
                      border: "1px solid rgba(155,114,207,0.2)",
                      borderRadius: 8, padding: "5px 8px",
                      cursor: "help", height: 110,
                      display: "flex", flexDirection: "column", justifyContent: "center", gap: 3 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "#6b6375", whiteSpace: "nowrap" }}>
                      #{r + 1}
                    </div>
                    <div style={{ fontSize: 9.5, color: "#9b8fc4", lineHeight: 1.3 }}>
                      {subj.split(",")[0]}
                    </div>
                  </div>
                </td>
                {styles.map((_, c) => {
                  const key = `${r}-${c}`;
                  const cell = cells[key] || { row: r, col: c, status: "idle" as const };
                  return (
                    <td key={key} style={{ padding: 0 }}>
                      <Cell
                        cell={cell}
                        onGenerate={() => onGenerateCell(r, c)}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// 主组件
export default function MatrixPage() {
  const [tab, setTab] = useState<"image" | "image-i2i" | "music">("image");
  const [mode, setMode] = useState<"edit" | "view">("edit");
  const [activeConfigId, setActiveConfigId] = useState<number | null>(null);

  // 编辑状态
  const [name, setName] = useState("巨树世界素材矩阵");
  const [promptBaseText, setPromptBaseText] = useState(
    "A giant tree world: giant leaf as big as a town, normal-sized plants and trees surrounding"
  );
  const [subjectsText, setSubjectsText] = useState(
    "A brave young farmer working on the giant leaf\nA grumpy old mushroom shop keeper in the village market\nA curious leaf spirit creature peeking from a bark hollow\nAn ancient brass compass on a worn wooden table\nA cozy cottage built inside a giant tree hollow\nA bustling morning market on a giant leaf town square"
  );
  const [stylesText, setStylesText] = useState(
    "Fantasy art, vibrant colors, dramatic lighting, highly detailed\nAnime cel-shading, clean lineart, expressive character\nSoft watercolor painting, pastel tones, dreamy atmosphere\nPixel art, 16-bit retro RPG style, vibrant colors\nClassical oil painting, rich texture, warm golden light\nPencil sketch, detailed linework, hatching shading"
  );
  const [cells, setCells] = useState<Record<string, Cell>>({});

  // 加载配置列表
  const { data: configList = [], refetch: refetchConfigs } = useQuery({
    queryKey: ["matrix-configs"],
    queryFn: matrixApi.listConfigs,
  });

  // 加载历史配置的资产
  const { data: historyAssets = [] } = useQuery({
    queryKey: ["matrix-assets", activeConfigId],
    queryFn: () => matrixApi.getConfigAssets(activeConfigId!),
    enabled: activeConfigId !== null,
  });

  // subjects/styles 用 useMemo 缓存，避免每次 render 新建引用导致 useEffect 死循环
  const subjects = useMemo(() => parseLines(subjectsText), [subjectsText]);
  const stylesLines = useMemo(() => parseLines(stylesText), [stylesText]);
  const styleLabels = useMemo(
    () => stylesLines.map((s) => {
      // 格式: "标签 | full prompt" 或回退到 "full prompt"
      const pipeIdx = s.indexOf("|");
      if (pipeIdx > 0) {
        return { abbr: s.slice(0, pipeIdx).trim(), full: s.slice(pipeIdx + 1).trim() };
      }
      return { abbr: s.split(",")[0].slice(0, 8).trim(), full: s };
    }),
    [stylesLines]
  );

  // 用 ref 记录上次填充的 key 集合，避免内容未变时重复 setCells 导致死循环
  const lastFilledKeys = useRef<Set<string> | null>(null);

  useEffect(() => {
    if (mode !== "view" || activeConfigId === null || historyAssets.length === 0) return;
    const newCells: Record<string, Cell> = {};
    for (const asset of historyAssets) {
      let pos = parseVariantToRowCol(asset.variant || "", subjects, styleLabels);
      if (!pos) pos = variantToRowCol(asset.variant || "");
      if (pos) {
        newCells[`${pos.row}-${pos.col}`] = { row: pos.row, col: pos.col, status: "done", asset };
      }
    }
    const newKeys = new Set(Object.keys(newCells));
    const prevKeys = lastFilledKeys.current;
    // 仅在 key 集合真正变化时才更新
    if (
      !prevKeys ||
      prevKeys.size !== newKeys.size ||
      ![...newKeys].every((k) => prevKeys.has(k))
    ) {
      lastFilledKeys.current = newKeys;
      setCells((prev) => {
        const merged = { ...prev };
        for (const [k, v] of Object.entries(newCells)) {
          // 不覆盖正在生成或已完成的格子
          if (!merged[k] || merged[k].status === "idle") merged[k] = v;
        }
        return merged;
      });
    }
  }, [mode, activeConfigId, historyAssets, subjects, styleLabels]);

  // 默认 RV 主题的 base prompt（后端重启后改用 cfg.prompt_base）
  const RV_BASE = "A recreational vehicle (RV) scene, cinematic composition, highly detailed";
  const TREE_BASE = "A giant tree world: giant leaf as big as a town, normal-sized plants and trees surrounding";

  function loadConfig(cfg: MatrixConfig) {
    setName(cfg.name);
    // prompt_base: undefined → theme default; "" (空字符串) → 显式空base; 有值 → 用该值
    const base = cfg.prompt_base !== undefined
      ? cfg.prompt_base
      : (cfg.theme === "rv-themed" ? RV_BASE : TREE_BASE);
    setPromptBaseText(base);
    setSubjectsText(cfg.subjects_text);
    setStylesText(cfg.styles_text);
    setActiveConfigId(cfg.id);
  }

  async function handleSave() {
    if (!name.trim()) return;
    const cfg = await matrixApi.createConfig({
      name: name.trim(),
      subjects_text: subjectsText,
      styles_text: stylesText,
      theme: "rv-themed",
      prompt_base: promptBaseText,
    });
    setActiveConfigId(cfg.id);
    refetchConfigs();
    return cfg;
  }

  async function handleGenerateCell(r: number, c: number) {
    const subjects = parseLines(subjectsText);
    const styles = parseLines(stylesText);
    if (r >= subjects.length || c >= styles.length) return;

    const subjectLine = subjects[r];
    const styleLine = styles[c];
    const prompt = buildPrompt(promptBaseText, subjectLine, styleLine);
    const variant = `${subjectLine.slice(0, 15).replace(/\s/g, "_")}-${styleLine.slice(0, 12).replace(/\s/g, "_")}`;

    setCells((prev) => ({ ...prev, [`${r}-${c}`]: { row: r, col: c, status: "generating" } }));

    try {
      // 确保有配置
      let cfgId = activeConfigId;
      if (!cfgId) {
        const cfg = await handleSave();
        cfgId = cfg!.id;
      }
      const result = await generateApi.image({
        prompt,
        model: "image-01",
        aspect_ratio: "16:9",
        n: 1,
        variant,
        theme: "rv-themed",
        config_id: cfgId!,
        matrix_name: name,
      });
      const asset: MatrixAsset = {
        ...result.assets[0],
        variant,
        category: "t2i",
        model: "image-01",
        status: "success",
        prompt_text: prompt,
      };
      setCells((prev) => ({ ...prev, [`${r}-${c}`]: { row: r, col: c, status: "done", asset } }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`[Matrix] Cell[${r},${c}] error:`, msg);
      setCells((prev) => ({ ...prev, [`${r}-${c}`]: { row: r, col: c, status: "error", error: msg } }));
    }
  }

  async function handleGenerateAll() {
    const subjects = parseLines(subjectsText);
    const styles = parseLines(stylesText);
    if (subjects.length === 0 || styles.length === 0) return;

    let cfgId = activeConfigId;
    if (!cfgId) {
      const cfg = await handleSave();
      if (!cfg) return;
      cfgId = cfg.id;
    }

    outer:
    for (let r = 0; r < subjects.length; r++) {
      for (let c = 0; c < styles.length; c++) {
        const key = `${r}-${c}`;
        if (cells[key]?.status === "done") continue;
        setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "generating" } }));
        try {
          const subjectLine = subjects[r];
          const styleLine = styles[c];
          const prompt = buildPrompt(promptBaseText, subjectLine, styleLine);
          const variant = `${subjectLine.slice(0, 15).replace(/\s/g, "_")}-${styleLine.slice(0, 12).replace(/\s/g, "_")}`;
          const result = await generateApi.image({
            prompt, model: "image-01", aspect_ratio: "16:9", n: 1,
            variant, theme: "rv-themed", config_id: cfgId!, matrix_name: name,
          });
          const asset: MatrixAsset = {
            ...result.assets[0], variant, category: "t2i",
            model: "image-01", status: "success", prompt_text: prompt,
          };
          setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "done", asset } }));
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          console.error(`[Matrix] Cell[${r},${c}] error:`, msg);
          setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "error", error: msg } }));
        }
        // 随机间隔
        await new Promise((r) => setTimeout(r, 800 + Math.random() * 1500));
      }
    }
  }

  function exportTxt() {
    const subjects = parseLines(subjectsText);
    const styles = parseLines(stylesText);
    let content = `# ${name}\n\n## 主体 (${subjects.length})\n`;
    subjects.forEach((s, i) => content += `${i + 1}. ${s}\n`);
    content += `\n## 风格 (${styles.length})\n`;
    styles.forEach((s, i) => content += `${i + 1}. ${s}\n`);
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${name}.txt`; a.click();
    URL.revokeObjectURL(url);
  }

  function exportJson() {
    const cfg = { name, subjects_text: subjectsText, styles_text: stylesText, theme: "giant-tree" };
    const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${name}.json`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      {/* 标题栏 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 22 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", margin: 0 }}>
          🎮 素材矩阵
        </h2>
        <div style={{ display: "flex", gap: 6 }}>
          {(["image", "image-i2i", "music"] as const).map((t) => (
            <button key={t} onClick={() => { setTab(t); setMode("edit"); setCells({}); }}
              style={{
                padding: "5px 14px", borderRadius: 50, fontSize: 12, fontWeight: 500,
                cursor: "pointer", transition: "all 0.15s",
                background: tab === t ? "rgba(155,114,207,0.18)" : "transparent",
                border: tab === t ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.3)",
                color: tab === t ? "#7b4fc4" : "#8a8394",
              }}>
              {t === "image" ? "🖼 T2I" : t === "image-i2i" ? "🖼 I2I" : "🎵 音乐"}
            </button>
          ))}
        </div>
      </div>

      {tab === "music" && <MusicMatrix />}
      {tab === "image-i2i" && <ImageI2IMatrix />}
      {tab === "image" && (
        <>
          {mode === "edit" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
          {/* 左侧：配置编辑 */}
          <div>
            {/* 名称 */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>矩阵名称</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                style={{ maxWidth: 300, width: "100%" }} />
            </div>

            {/* Base Prompt */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>
                基础描述（所有 prompt 共享的前缀）
              </label>
              <textarea
                value={promptBaseText}
                onChange={(e) => setPromptBaseText(e.target.value)}
                rows={3}
                style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(155,114,207,0.35)",
                  background: "rgba(155,114,207,0.06)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }}
                placeholder="例如：A recreational vehicle (RV) scene, cozy and atmospheric"
              />
            </div>

            {/* 主体配置 */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label style={{ fontSize: 12, color: "#8a8394" }}>
                  主体（每行一个，{subjects.length}个）
                </label>
                <span style={{ fontSize: 11, color: "#bdb9c8" }}>共 {subjects.length} 个</span>
              </div>
              <textarea
                value={subjectsText}
                onChange={(e) => setSubjectsText(e.target.value)}
                rows={8}
                style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(200,195,215,0.4)",
                  background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }}
              />
            </div>

            {/* 风格配置 */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label style={{ fontSize: 12, color: "#8a8394" }}>
                  画风（每行一个，{stylesLines.length}个）
                </label>
                <span style={{ fontSize: 11, color: "#bdb9c8" }}>共 {stylesLines.length} 个</span>
              </div>
              <textarea
                value={stylesText}
                onChange={(e) => setStylesText(e.target.value)}
                rows={6}
                style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(200,195,215,0.4)",
                  background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }}
              />
            </div>

            {/* 操作按钮 */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={async () => { await handleSave(); refetchConfigs(); }}
                style={{ padding: "8px 16px", borderRadius: 10, background: "rgba(155,114,207,0.8)",
                  border: "none", color: "#fff", fontSize: 13, cursor: "pointer" }}>
                💾 保存配置
              </button>
              <button onClick={exportTxt}
                style={{ padding: "8px 14px", borderRadius: 10, background: "rgba(255,255,255,0.5)",
                  border: "1px solid rgba(200,195,215,0.4)", color: "#6b6375", fontSize: 13, cursor: "pointer" }}>
                📄 导出 TXT
              </button>
              <button onClick={exportJson}
                style={{ padding: "8px 14px", borderRadius: 10, background: "rgba(255,255,255,0.5)",
                  border: "1px solid rgba(200,195,215,0.4)", color: "#6b6375", fontSize: 13, cursor: "pointer" }}>
                📋 导出 JSON
              </button>
            </div>

            {/* 历史记录 */}
            {configList.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#6b6375", marginBottom: 8 }}>历史配置</div>
                {configList.map((cfg) => (
                  <div key={cfg.id}
                    onClick={() => { loadConfig(cfg); setMode("view"); }}
                    style={{
                      padding: "10px 14px", borderRadius: 10, marginBottom: 6, cursor: "pointer",
                      background: activeConfigId === cfg.id ? "rgba(155,114,207,0.12)" : "rgba(255,255,255,0.5)",
                      border: activeConfigId === cfg.id ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.25)",
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                    }}>
                    <div>
                      <div style={{ fontSize: 13, color: "#3d3545", fontWeight: 500 }}>{cfg.name}</div>
                      <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 2 }}>
                        {parseLines(cfg.subjects_text).length} 主体 × {parseLines(cfg.styles_text).length} 风格 · {new Date(cfg.created_at).toLocaleDateString("zh-CN")}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); matrixApi.deleteConfig(cfg.id).then(() => refetchConfigs()); }}
                      style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#d98a8a", padding: "4px 8px" }}
                    >
                      🗑
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 右侧：矩阵预览 */}
          <div>
            {subjects.length > 0 && stylesLines.length > 0 ? (
              <MatrixGrid
                subjects={subjects}
                styles={styleLabels}
                cells={cells}
                onGenerateCell={handleGenerateCell}
                onGenerateAll={handleGenerateAll}
              />
            ) : (
              <div style={{
                background: "rgba(255,255,255,0.45)", borderRadius: 16, padding: "40px",
                border: "1px dashed rgba(200,195,215,0.4)", textAlign: "center", color: "#bdb9c8", fontSize: 13,
              }}>
                填写主体和画风配置后，这里将显示矩阵预览
              </div>
            )}
          </div>
        </div>
      )}

      {mode === "view" && activeConfigId !== null && (
        (() => {
          const cfg = configList.find((c) => c.id === activeConfigId);
          if (!cfg) return null;
          const subs = parseLines(cfg.subjects_text);
          const stys = parseLines(cfg.styles_text);
          return (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#3d3545", margin: 0 }}>{cfg.name}</h3>
                <span style={{ fontSize: 12, color: "#bdb9c8" }}>
                  {subs.length} 主体 × {stys.length} 风格 · {new Date(cfg.created_at).toLocaleDateString("zh-CN")}
                </span>
                <button onClick={() => { loadConfig(cfg); setMode("edit"); }}
                  style={{ padding: "5px 12px", borderRadius: 8, background: "rgba(155,114,207,0.12)",
                    border: "1px solid rgba(155,114,207,0.25)", color: "#7b4fc4", fontSize: 12, cursor: "pointer" }}>
                  重新编辑
                </button>
              </div>
              <MatrixGrid
                subjects={subs}
                styles={stys.map((s) => ({ abbr: s.split(",")[0].slice(0, 8).trim(), full: s }))}
                cells={cells}
                onGenerateCell={handleGenerateCell}
                onGenerateAll={handleGenerateAll}
              />
            </div>
          );
        })()
      )}

      {mode === "view" && activeConfigId === null && (
        <div style={{ color: "#bdb9c8", fontSize: 13, textAlign: "center", padding: "40px 0" }}>
          从左侧历史记录选择一个配置查看
        </div>
      )}
        </>
      )}
    </div>
  );
}

// ── Music Matrix ──────────────────────────────────────────────────────────────

function MusicMatrix() {
  const FILE_BASE = "http://localhost:8000/files";
  const [tab2, setTab2] = useState<"edit" | "history">("edit");
  const [musicName, setMusicName] = useState("游戏BGM矩阵");
  const [basePrompt, setBasePrompt] = useState("game background music, instrumental");
  const [rowStylesText, setRowStylesText] = useState([
    "Fantasy Kingdom, epic and majestic",
    "Dungeon Crawler, dark and mysterious",
    "Cozy Village, warm and peaceful",
    "Space Station, futuristic and calm",
    "Tropical Adventure, bright and energetic",
    "Haunted Manor, eerie and suspenseful",
  ].join("\n"));
  const [colStylesText, setColStylesText] = useState([
    "Epic Orchestra, cinematic, powerful",
    "8-bit Chiptune, retro gaming, catchy",
    "Jazz Trio, smooth and sophisticated",
    "Celtic Folk, traditional, adventurous",
    "Synthwave, electronic, nostalgic",
    "Minimal Piano, solo, emotional",
  ].join("\n"));
  const [cells, setCells] = useState<Record<string, { status: string; file_path?: string; error?: string }>>({});
  const [currentAudio, setCurrentAudio] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const { data: musicConfigs = [], refetch: refetchMusic } = useQuery({
    queryKey: ["music-matrix-configs"],
    queryFn: matrixApi.listMusicConfigs,
  });

  function parseLines(text: string) {
    return text.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
  }

  const rowStyles = useMemo(() => parseLines(rowStylesText), [rowStylesText]);
  const colStyles = useMemo(() => parseLines(colStylesText), [colStylesText]);
  const colStyleLabels = useMemo(
    () => colStyles.map((s) => ({ abbr: s.split(",")[0].slice(0, 10).trim(), full: s })),
    [colStyles]
  );

  const [activeMusicConfigId, setActiveMusicConfigId] = useState<number | null>(null);
  const { data: tracks = [], refetch: refetchTracks } = useQuery({
    queryKey: ["music-tracks", activeMusicConfigId],
    queryFn: () => matrixApi.getMusicConfigTracks(activeMusicConfigId!),
    enabled: activeMusicConfigId !== null,
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (!tracks.length) return;
    const newCells: Record<string, { status: string; file_path?: string; error?: string }> = {};
    for (const t of tracks) {
      newCells[`${t.row}-${t.col}`] = { status: t.status, file_path: t.file_path, error: t.error };
    }
    setCells(newCells);
  }, [tracks]);

  async function handleGenerate() {
    if (!musicName.trim() || rowStyles.length !== 6 || colStyles.length !== 6) return;
    try {
      const result = await matrixApi.generateMusicMatrix({
        name: musicName.trim(),
        row_styles: rowStyles,
        col_styles: colStyles,
        base_prompt: basePrompt,
      });
      setActiveMusicConfigId(result.config_id);
      setTab2("history");
      refetchMusic();
      const initCells: Record<string, { status: string }> = {};
      for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++)
        initCells[`${r}-${c}`] = { status: "pending" };
      setCells(initCells);
    } catch (err) {
      console.error(err);
    }
  }

  function loadMusicConfig(cfg: MusicMatrixConfig) {
    setActiveMusicConfigId(cfg.id);
    setMusicName(cfg.name);
    const rowsSet = new Set<number>();
    const colsSet = new Set<number>();
    const rowPrompts: Record<number, string> = {};
    const colPrompts: Record<number, string> = {};
    for (const line of cfg.prompts_text.trim().split("\n")) {
      const [idx, prompt] = line.split("::");
      if (!idx || !prompt) continue;
      const [r, c] = idx.split(",").map(Number);
      rowsSet.add(r);
      colsSet.add(c);
      rowPrompts[r] = prompt.split(",").slice(0, 2).join(",");
      colPrompts[c] = prompt.split(",").slice(1).join(",");
    }
    const maxRow = Math.max(...rowsSet) + 1;
    const maxCol = Math.max(...colsSet) + 1;
    const rowsArr = Array.from({ length: maxRow }, (_, i) => rowPrompts[i] || "");
    const colsArr = Array.from({ length: maxCol }, (_, i) => colPrompts[i] || "");
    setRowStylesText(rowsArr.join("\n"));
    setColStylesText(colsArr.join("\n"));
    setTab2("history");
  }

  function playTrack(filePath: string) {
    if (audioRef.current) audioRef.current.pause();
    const url = `${FILE_BASE}/${filePath}`;
    setCurrentAudio(url);
    audioRef.current = new Audio(url);
    audioRef.current.play();
  }

  function stopPlayback() {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; setCurrentAudio(null); }
  }

  const doneCount = Object.values(cells).filter((c) => c.status === "done").length;
  const total = 36;
  const donePct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div>
      <audio ref={audioRef} onEnded={() => setCurrentAudio(null)} />
      <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
        {([["edit", "编辑模式"], ["history", "历史记录"]] as const).map(([t, label]) => (
          <button key={t} onClick={() => setTab2(t)}
            style={{
              padding: "5px 14px", borderRadius: 50, fontSize: 12, fontWeight: 500, cursor: "pointer",
              background: tab2 === t ? "rgba(155,114,207,0.18)" : "transparent",
              border: tab2 === t ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.3)",
              color: tab2 === t ? "#7b4fc4" : "#8a8394",
            }}>
            {label}
          </button>
        ))}
      </div>

      {tab2 === "edit" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>矩阵名称</label>
              <input className="input" value={musicName} onChange={(e) => setMusicName(e.target.value)}
                style={{ maxWidth: 300, width: "100%" }} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>基础 Prompt</label>
              <input className="input" value={basePrompt} onChange={(e) => setBasePrompt(e.target.value)}
                style={{ maxWidth: 400, width: "100%" }} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>行风格（游戏场景，6个）</label>
              <textarea value={rowStylesText} onChange={(e) => setRowStylesText(e.target.value)}
                rows={7} style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(200,195,215,0.4)",
                  background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>列风格（乐器/编曲，6个）</label>
              <textarea value={colStylesText} onChange={(e) => setColStylesText(e.target.value)}
                rows={7} style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(200,195,215,0.4)",
                  background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }} />
            </div>
            {rowStyles.length !== 6 && <div style={{ fontSize: 11, color: "#d98a8a", marginBottom: 8 }}>请提供 6 个行风格（当前 {rowStyles.length} 个）</div>}
            {colStyles.length !== 6 && <div style={{ fontSize: 11, color: "#d98a8a", marginBottom: 8 }}>请提供 6 个列风格（当前 {colStyles.length} 个）</div>}
            <button
              onClick={handleGenerate}
              disabled={rowStyles.length !== 6 || colStyles.length !== 6}
              style={{
                padding: "9px 22px", borderRadius: 12,
                background: rowStyles.length === 6 && colStyles.length === 6
                  ? "linear-gradient(135deg, rgba(155,114,207,0.85), rgba(196,174,226,0.65))"
                  : "rgba(155,114,207,0.3)",
                border: "none", color: "#fff", fontSize: 14, fontWeight: 600,
                cursor: rowStyles.length === 6 && colStyles.length === 6 ? "pointer" : "not-allowed",
              }}
            >
              🎵 生成 36 首游戏 BGM
            </button>

            {musicConfigs.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#6b6375", marginBottom: 8 }}>历史配置</div>
                {musicConfigs.map((cfg) => (
                  <div key={cfg.id}
                    onClick={() => loadMusicConfig(cfg)}
                    style={{
                      padding: "10px 14px", borderRadius: 10, marginBottom: 6, cursor: "pointer",
                      background: activeMusicConfigId === cfg.id ? "rgba(155,114,207,0.12)" : "rgba(255,255,255,0.5)",
                      border: activeMusicConfigId === cfg.id ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.25)",
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                    }}>
                    <div>
                      <div style={{ fontSize: 13, color: "#3d3545", fontWeight: 500 }}>{cfg.name}</div>
                      <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 2 }}>
                        {new Date(cfg.created_at).toLocaleDateString("zh-CN")}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); matrixApi.deleteMusicConfig(cfg.id).then(() => refetchMusic()); }}
                      style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#d98a8a", padding: "4px 8px" }}>
                      🗑
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            {rowStyles.length === 6 && colStyles.length === 6 ? (
              <MusicGridPreview rowStyles={rowStyles} colStyleLabels={colStyleLabels} cells={cells}
                currentAudio={currentAudio} onPlay={playTrack} onStop={stopPlayback} />
            ) : (
              <div style={{
                background: "rgba(255,255,255,0.45)", borderRadius: 16, padding: "40px",
                border: "1px dashed rgba(200,195,215,0.4)", textAlign: "center", color: "#bdb9c8", fontSize: 13,
              }}>
                填写 6×6 配置后，这里将显示预览
              </div>
            )}
          </div>
        </div>
      )}

      {tab2 === "history" && activeMusicConfigId !== null && (
        <div>
          {doneCount > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: "#8a8394", marginBottom: 5 }}>
                {doneCount}/{total} 已生成 {donePct}%
                {currentAudio && <span style={{ marginLeft: 12, color: "#7b4fc4" }}>▶ 播放中</span>}
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${donePct}%` }} />
              </div>
            </div>
          )}
          {doneCount < total && (
            <div style={{ marginBottom: 14 }}>
              <button
                onClick={async () => { try { await matrixApi.retryMusicMatrix(activeMusicConfigId); refetchTracks(); } catch (e) { console.error(e); } }}
                style={{ padding: "7px 16px", borderRadius: 10, background: "linear-gradient(135deg, rgba(155,114,207,0.85), rgba(196,174,226,0.65))",
                  border: "none", color: "#fff", fontSize: 13, cursor: "pointer" }}>
                🔄 继续生成剩余 {total - doneCount} 首
              </button>
            </div>
          )}
          <MusicGridPreview rowStyles={rowStyles} colStyleLabels={colStyleLabels} cells={cells}
            currentAudio={currentAudio} onPlay={playTrack} onStop={stopPlayback} />
        </div>
      )}

      {tab2 === "history" && activeMusicConfigId === null && (
        <div style={{ color: "#bdb9c8", fontSize: 13, textAlign: "center", padding: "40px 0" }}>
          从编辑模式生成音乐后自动跳转到这里
        </div>
      )}
    </div>
  );
}

// 音乐格仔预览（6×6）
function MusicGridPreview({
  rowStyles, colStyleLabels, cells, currentAudio, onPlay, onStop,
}: {
  rowStyles: string[];
  colStyleLabels: { abbr: string; full: string }[];
  cells: Record<string, { status: string; file_path?: string; error?: string }>;
  currentAudio: string | null;
  onPlay: (file_path: string) => void;
  onStop: () => void;
}) {
  const FILE_BASE = "http://localhost:8000/files";
  const statusColor: Record<string, string> = {
    idle: "rgba(200,195,215,0.15)", pending: "rgba(155,114,207,0.1)",
    generating: "rgba(155,114,207,0.15)", done: "transparent", failed: "rgba(220,150,150,0.08)",
  };

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ borderCollapse: "separate", borderSpacing: 5, minWidth: 500 }}>
        <thead>
          <tr>
            <th style={{ width: 80, padding: "0 4px 8px" }} />
            {colStyleLabels.map((s, ci) => (
              <th key={`col-${ci}`} style={{ padding: "0 0 8px" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                  <div title={s.full} style={{ fontSize: 11, fontWeight: 700, color: "#7b4fc4",
                    background: "rgba(155,114,207,0.12)", border: "1px solid rgba(155,114,207,0.25)",
                    borderRadius: 8, padding: "4px 8px", cursor: "help", whiteSpace: "nowrap" }}>
                    {s.abbr}
                  </div>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowStyles.map((row, r) => (
            <tr key={r}>
              <td style={{ padding: "0 4px 0 0" }}>
                <div title={row} style={{
                  background: "rgba(155,114,207,0.08)", border: "1px solid rgba(155,114,207,0.2)",
                  borderRadius: 8, padding: "5px 8px", height: 110,
                  display: "flex", flexDirection: "column", justifyContent: "center", gap: 3 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: "#6b6375" }}>#{r + 1}</div>
                  <div style={{ fontSize: 9.5, color: "#9b8fc4", lineHeight: 1.3 }}>{row.split(",")[0]}</div>
                </div>
              </td>
              {colStyleLabels.map((_, c) => {
                const key = `${r}-${c}`;
                const cell = cells[key] || { status: "idle" };
                const isPlaying = cell.status === "done" && currentAudio?.includes(`r${r}c${c}`);
                return (
                  <td key={key} style={{ padding: 0 }}>
                    <div style={{
                      height: 110, borderRadius: 10, overflow: "hidden",
                      background: statusColor[cell.status] || statusColor.idle,
                      border: cell.status === "done" ? "1.5px solid rgba(155,114,207,0.3)" : "1.5px solid rgba(200,195,215,0.2)",
                      display: "flex", alignItems: "center", justifyContent: "center", position: "relative",
                    }}>
                      {cell.status === "idle" && <span style={{ fontSize: 10, color: "#c4bfd0" }}>—</span>}
                      {cell.status === "pending" && <span style={{ fontSize: 10, color: "#9b72cf" }}>⏳</span>}
                      {cell.status === "generating" && (
                        <div style={{ fontSize: 11, color: "#9b72cf", textAlign: "center" }}>
                          <div>⏳</div><div style={{ fontSize: 9, marginTop: 2 }}>生成中</div>
                        </div>
                      )}
                      {cell.status === "done" && (
                        <button
                          onClick={() => isPlaying ? onStop() : onPlay(cell.file_path!)}
                          style={{
                            background: isPlaying ? "rgba(155,114,207,0.8)" : "rgba(155,114,207,0.5)",
                            border: "none", borderRadius: 50, width: 40, height: 40,
                            fontSize: 18, color: "#fff", cursor: "pointer",
                            display: "flex", alignItems: "center", justifyContent: "center",
                          }}>
                          {isPlaying ? "⏸" : "▶"}
                        </button>
                      )}
                      {cell.status === "failed" && (
                        <div title={cell.error || "失败"} style={{ fontSize: 10, color: "#d98a8a", textAlign: "center", padding: 6 }}>
                          ❌<div style={{ marginTop: 2, fontSize: 9 }}>{cell.error?.slice(0, 20)}</div>
                        </div>
                      )}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Image I2I Matrix ─────────────────────────────────────────────────────────

function ImageI2IMatrix() {
  const FILE_BASE = "http://localhost:8000/files";
  const [tab2, setTab2] = useState<"edit" | "history">("edit");
  const [name, setName] = useState("批量图生图矩阵");
  const [promptBaseText, setPromptBaseText] = useState("");
  const [subjectsText, setSubjectsText] = useState("");
  const [stylesText, setStylesText] = useState("");
  const [referenceImage, setReferenceImage] = useState<string>(""); // 文件路径
  const [referencePreview, setReferencePreview] = useState<string>(""); // 预览 URL
  const [cells, setCells] = useState<Record<string, Cell>>({});
  const [showPicker, setShowPicker] = useState(false);
  const [pickerSearch, setPickerSearch] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: configList = [], refetch: refetchConfigs } = useQuery({
    queryKey: ["matrix-i2i-configs"],
    queryFn: matrixApi.listConfigs,
  });

  const { data: pickerAssets = [], refetch: refetchPicker } = useQuery({
    queryKey: ["asset-picker", pickerSearch],
    queryFn: () => assetsApi.picker({ search: pickerSearch || undefined, limit: 40 }),
    enabled: showPicker,
  });

  const subjects = useMemo(() => parseLines(subjectsText), [subjectsText]);
  const stylesLines = useMemo(() => parseLines(stylesText), [stylesText]);
  const styleLabels = useMemo(
    () => stylesLines.map((s) => ({
      abbr: s.split(",")[0].slice(0, 8).trim(),
      full: s,
    })),
    [stylesLines]
  );

  function loadConfig(cfg: MatrixConfig) {
    if (cfg.category !== "i2i") return;
    setName(cfg.name);
    setPromptBaseText(cfg.prompt_base || "");
    setSubjectsText(cfg.subjects_text);
    setStylesText(cfg.styles_text);
    setReferenceImage(cfg.reference_image || "");
    if (cfg.reference_image) {
      setReferencePreview(`${FILE_BASE}/${cfg.reference_image}`);
    }
  }

  async function handleUploadRef(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await generateApi.upload(file);
      setReferenceImage(result.file_path);
      setReferencePreview(`${FILE_BASE}/${result.file_path}`);
    } catch (err) {
      console.error("上传参考图失败:", err);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function selectFromPicker(asset: AssetResponse) {
    setReferenceImage(asset.file_path);
    setReferencePreview(`${FILE_BASE}/${asset.file_path}`);
    setShowPicker(false);
  }

  async function handleSave() {
    if (!name.trim()) return;
    const cfg = await matrixApi.createConfig({
      name: name.trim(),
      subjects_text: subjectsText,
      styles_text: stylesText,
      theme: "rv-themed",
      prompt_base: promptBaseText,
      category: "i2i",
      reference_image: referenceImage,
      rows_count: subjects.length,
      cols_count: stylesLines.length,
    });
    refetchConfigs();
    return cfg;
  }

  async function handleGenerateCell(r: number, c: number) {
    if (!referencePreview) return;
    const subs = parseLines(subjectsText);
    const stys = parseLines(stylesText);
    if (r >= subs.length || c >= stys.length) return;

    const subjectLine = subs[r];
    const styleLine = stys[c];
    const prompt = buildPrompt(promptBaseText, subjectLine, styleLine);
    const variant = `${subjectLine.slice(0, 15).replace(/\s/g, "_")}-${styleLine.slice(0, 12).replace(/\s/g, "_")}`;

    setCells((prev) => ({ ...prev, [`${r}-${c}`]: { row: r, col: c, status: "generating" } }));

    let cfgId: number | undefined;
    try {
      // 读取参考图 base64
      let refB64 = "";
      if (referenceImage.startsWith("works/") || referenceImage.startsWith("works\\")) {
        // 相对路径，fetch 它
        const resp = await fetch(`${FILE_BASE}/${referenceImage}`);
        const blob = await resp.blob();
        refB64 = await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result as string);
          reader.readAsDataURL(blob);
        });
      } else {
        refB64 = referencePreview; // 已经是 data URL 或完整 URL
      }

      const result = await generateApi.image({
        prompt,
        model: "image-01",
        aspect_ratio: "16:9",
        n: 1,
        variant,
        theme: "rv-themed",
        config_id: undefined,
        matrix_name: name,
        reference_image: refB64,
      });
      const asset: MatrixAsset = {
        ...result.assets[0],
        variant,
        category: "i2i",
        model: "image-01",
        status: "success",
        prompt_text: prompt,
      };
      setCells((prev) => ({ ...prev, [`${r}-${c}`]: { row: r, col: c, status: "done", asset } }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCells((prev) => ({ ...prev, [`${r}-${c}`]: { row: r, col: c, status: "error", error: msg } }));
    }
  }

  async function handleGenerateAll() {
    if (!referencePreview) return;
    const subs = parseLines(subjectsText);
    const stys = parseLines(stylesText);
    if (subs.length === 0 || stys.length === 0) return;

    let refB64 = "";
    if (referenceImage.startsWith("works/") || referenceImage.startsWith("works\\")) {
      const resp = await fetch(`${FILE_BASE}/${referenceImage}`);
      const blob = await resp.blob();
      refB64 = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      });
    } else {
      refB64 = referencePreview;
    }

    for (let r = 0; r < subs.length; r++) {
      for (let c = 0; c < stys.length; c++) {
        const key = `${r}-${c}`;
        if (cells[key]?.status === "done") continue;
        const subjectLine = subs[r];
        const styleLine = stys[c];
        const prompt = buildPrompt(promptBaseText, subjectLine, styleLine);
        const variant = `${subjectLine.slice(0, 15).replace(/\s/g, "_")}-${styleLine.slice(0, 12).replace(/\s/g, "_")}`;
        setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "generating" } }));
        try {
          const result = await generateApi.image({
            prompt, model: "image-01", aspect_ratio: "16:9", n: 1,
            variant, theme: "rv-themed", reference_image: refB64,
          });
          const asset: MatrixAsset = {
            ...result.assets[0], variant, category: "i2i",
            model: "image-01", status: "success", prompt_text: prompt,
          };
          setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "done", asset } }));
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "error", error: msg } }));
        }
        await new Promise((r2) => setTimeout(r2, 800 + Math.random() * 1500));
      }
    }
  }

  function exportJson() {
    const cfg = {
      name, category: "i2i", reference_image: referenceImage,
      subjects_text: subjectsText, styles_text: stylesText,
      prompt_base: promptBaseText, theme: "rv-themed",
      rows_count: subjects.length, cols_count: stylesLines.length,
    };
    const blob = new Blob([JSON.stringify(cfg, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${name}.json`; a.click();
    URL.revokeObjectURL(url);
  }

  function importJson(file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const cfg = JSON.parse(e.target!.result as string);
        setName(cfg.name || "批量图生图矩阵");
        setSubjectsText(cfg.subjects_text || "");
        setStylesText(cfg.styles_text || "");
        setPromptBaseText(cfg.prompt_base || "");
        if (cfg.reference_image) {
          setReferenceImage(cfg.reference_image);
          setReferencePreview(`${FILE_BASE}/${cfg.reference_image}`);
        }
      } catch {
        alert("无效的 JSON 文件");
      }
    };
    reader.readAsText(file);
  }

  const i2iConfigs = configList.filter((c) => c.category === "i2i");
  const doneCount = Object.values(cells).filter((c) => c.status === "done").length;
  const total = subjects.length * stylesLines.length;
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  return (
    <div>
      <input
        type="file" accept="image/*" ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleUploadRef}
      />

      {/* 图片选择器浮层 */}
      {showPicker && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(10,8,18,0.7)",
          backdropFilter: "blur(8px)", zIndex: 500,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            background: "#fff", borderRadius: 20, padding: 24,
            width: "90vw", maxWidth: 800, maxHeight: "80vh",
            overflow: "hidden", display: "flex", flexDirection: "column",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <span style={{ fontSize: 16, fontWeight: 600, color: "#3d3545" }}>选择参考图</span>
              <button onClick={() => setShowPicker(false)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}>✕</button>
            </div>
            <input
              className="input" placeholder="搜索图片 prompt..." value={pickerSearch}
              onChange={(e) => setPickerSearch(e.target.value)}
              style={{ marginBottom: 14, maxWidth: 300 }}
            />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: 10, overflowY: "auto", flex: 1 }}>
              {pickerAssets.filter((a) => a.modality === "image").map((asset) => (
                <div key={asset.id}
                  onClick={() => selectFromPicker(asset)}
                  style={{ cursor: "pointer", borderRadius: 10, overflow: "hidden", border: "2px solid transparent" }}
                >
                  <img src={`${FILE_BASE}/${asset.file_path}`} alt=""
                    style={{ width: "100%", height: 90, objectFit: "cover" }} />
                  <div style={{ fontSize: 9, color: "#8a8394", padding: "4px 6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {asset.prompt_text.slice(0, 30)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 子 Tab */}
      <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
        {([["edit", "编辑模式"], ["history", "历史配置"]] as const).map(([t, label]) => (
          <button key={t} onClick={() => setTab2(t)}
            style={{
              padding: "5px 14px", borderRadius: 50, fontSize: 12, fontWeight: 500,
              cursor: "pointer",
              background: tab2 === t ? "rgba(155,114,207,0.18)" : "transparent",
              border: tab2 === t ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.3)",
              color: tab2 === t ? "#7b4fc4" : "#8a8394",
            }}>
            {label}
          </button>
        ))}
      </div>

      {tab2 === "edit" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
          {/* 左侧 */}
          <div>
            {/* 名称 */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>矩阵名称</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                style={{ maxWidth: 300, width: "100%" }} />
            </div>

            {/* 参考图 */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>参考图</label>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  style={{ padding: "7px 14px", borderRadius: 10, background: "rgba(155,114,207,0.15)",
                    border: "1px solid rgba(155,114,207,0.3)", color: "#7b4fc4", fontSize: 12, cursor: "pointer" }}>
                  📤 上传参考图
                </button>
                <button
                  onClick={() => setShowPicker(true)}
                  style={{ padding: "7px 14px", borderRadius: 10, background: "rgba(255,255,255,0.5)",
                    border: "1px solid rgba(200,195,215,0.4)", color: "#6b6375", fontSize: 12, cursor: "pointer" }}>
                  🖼 从图库选择
                </button>
                {referencePreview && (
                  <img src={referencePreview} alt="参考图"
                    style={{ width: 60, height: 60, objectFit: "cover", borderRadius: 8, border: "1px solid rgba(155,114,207,0.3)" }} />
                )}
              </div>
              {referenceImage && (
                <div style={{ fontSize: 10, color: "#bdb9c8", marginTop: 4 }}>{referenceImage}</div>
              )}
            </div>

            {/* Base Prompt */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>
                基础描述（所有 prompt 共享的前缀，可选）
              </label>
              <textarea value={promptBaseText} onChange={(e) => setPromptBaseText(e.target.value)}
                rows={2}
                style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(155,114,207,0.35)",
                  background: "rgba(155,114,207,0.06)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }}
                placeholder="如：A cozy RV scene, cinematic, highly detailed" />
            </div>

            {/* 主体 */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label style={{ fontSize: 12, color: "#8a8394" }}>主体（每行一个）</label>
                <span style={{ fontSize: 11, color: "#bdb9c8" }}>{subjects.length} 个</span>
              </div>
              <textarea value={subjectsText} onChange={(e) => setSubjectsText(e.target.value)}
                rows={6}
                style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(200,195,215,0.4)",
                  background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }}
                placeholder={"每行一个主体描述，如：\nA cozy cabin in a forest\nA mountain village at sunrise"} />
            </div>

            {/* 风格 */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label style={{ fontSize: 12, color: "#8a8394" }}>风格（每行一个）</label>
                <span style={{ fontSize: 11, color: "#bdb9c8" }}>{stylesLines.length} 个</span>
              </div>
              <textarea value={stylesText} onChange={(e) => setStylesText(e.target.value)}
                rows={5}
                style={{ width: "100%", boxSizing: "border-box", padding: "10px 12px",
                  borderRadius: 12, border: "1px solid rgba(200,195,215,0.4)",
                  background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                  fontFamily: "var(--font-main)", resize: "vertical", outline: "none" }}
                placeholder={"每行一个风格描述，如：\nFantasy art, vibrant colors\nSoft watercolor, pastel tones"} />
            </div>

            {/* 操作 */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={async () => { await handleSave(); refetchConfigs(); }}
                style={{ padding: "8px 16px", borderRadius: 10, background: "rgba(155,114,207,0.8)",
                  border: "none", color: "#fff", fontSize: 13, cursor: "pointer" }}>
                💾 保存配置
              </button>
              <button onClick={exportJson}
                style={{ padding: "8px 14px", borderRadius: 10, background: "rgba(255,255,255,0.5)",
                  border: "1px solid rgba(200,195,215,0.4)", color: "#6b6375", fontSize: 13, cursor: "pointer" }}>
                📋 导出 JSON
              </button>
              <label style={{ padding: "8px 14px", borderRadius: 10, background: "rgba(255,255,255,0.5)",
                border: "1px solid rgba(200,195,215,0.4)", color: "#6b6375", fontSize: 13, cursor: "pointer" }}>
                📂 导入 JSON
                <input type="file" accept=".json" style={{ display: "none" }}
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) importJson(f); }} />
              </label>
            </div>

            {/* 历史配置 */}
            {i2iConfigs.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#6b6375", marginBottom: 8 }}>历史配置</div>
                {i2iConfigs.map((cfg) => (
                  <div key={cfg.id}
                    onClick={() => { loadConfig(cfg); setTab2("edit"); }}
                    style={{
                      padding: "10px 14px", borderRadius: 10, marginBottom: 6, cursor: "pointer",
                      background: "rgba(255,255,255,0.5)",
                      border: "1px solid rgba(200,195,215,0.25)",
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                    }}>
                    <div>
                      <div style={{ fontSize: 13, color: "#3d3545", fontWeight: 500 }}>{cfg.name}</div>
                      <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 2 }}>
                        {cfg.rows_count}×{cfg.cols_count} · {cfg.reference_image?.split("/").pop() || "无参考图"} · {new Date(cfg.created_at).toLocaleDateString("zh-CN")}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); matrixApi.deleteConfig(cfg.id).then(() => refetchConfigs()); }}
                      style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#d98a8a", padding: "4px 8px" }}>
                      🗑
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 右侧预览 */}
          <div>
            {!referencePreview ? (
              <div style={{
                background: "rgba(255,255,255,0.45)", borderRadius: 16, padding: "40px",
                border: "1px dashed rgba(200,195,215,0.4)", textAlign: "center", color: "#bdb9c8", fontSize: 13,
              }}>
                请先上传或选择参考图
              </div>
            ) : subjects.length > 0 && stylesLines.length > 0 ? (
              <MatrixGrid
                subjects={subjects}
                styles={styleLabels}
                cells={cells}
                onGenerateCell={handleGenerateCell}
                onGenerateAll={handleGenerateAll}
              />
            ) : (
              <div style={{
                background: "rgba(255,255,255,0.45)", borderRadius: 16, padding: "40px",
                border: "1px dashed rgba(200,195,215,0.4)", textAlign: "center", color: "#bdb9c8", fontSize: 13,
              }}>
                填写主体和风格后，这里将显示矩阵预览
              </div>
            )}
          </div>
        </div>
      )}

      {tab2 === "history" && (
        <div>
          {doneCount > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: "#8a8394", marginBottom: 5 }}>
                {doneCount}/{total} 已生成 {pct}%
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${pct}%` }} />
              </div>
            </div>
          )}
          <MatrixGrid
            subjects={subjects}
            styles={styleLabels}
            cells={cells}
            onGenerateCell={handleGenerateCell}
            onGenerateAll={handleGenerateAll}
          />
        </div>
      )}
    </div>
  );
}
