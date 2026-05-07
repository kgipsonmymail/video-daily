import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "../api/tasks";
import { assetsApi } from "../api/assets";
import { generateApi } from "../api/generate";
import AssetPickerDialog from "../components/AssetPickerDialog";
import type { AssetResponse } from "../types";

const CATEGORIES = [
  { value: "t2i", label: "文生图", model_default: "image-01" },
  { value: "i2i", label: "图生图", model_default: "image-01" },
  { value: "t2v", label: "文生视频", model_default: "MiniMax-Hailuo-2.3" },
  { value: "i2v", label: "图生视频", model_default: "MiniMax-Hailuo-2.3-Fast" },
  { value: "music", label: "音乐生成", model_default: "music-2.6" },
];

const ASPECT_RATIOS = [
  { value: "1:1",   label: "正方",   w: 30, h: 30 },
  { value: "16:9", label: "宽屏",   w: 40, h: 23 },
  { value: "4:3",  label: "标准",   w: 36, h: 27 },
  { value: "3:2",  label: "风光",   w: 38, h: 25 },
  { value: "2:3",  label: "竖幅",   w: 20, h: 30 },
  { value: "3:4",  label: "人像",   w: 23, h: 30 },
  { value: "9:16", label: "手机",   w: 17, h: 30 },
  { value: "21:9", label: "带鱼",   w: 40, h: 17 },
];

function AspectBox({ w, h, selected }: { w: number; h: number; selected: boolean }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
      cursor: "pointer",
    }}>
      <div style={{
        width: w, height: h,
        borderRadius: 3,
        background: selected
          ? "linear-gradient(135deg, rgba(155,114,207,0.8), rgba(196,174,226,0.6))"
          : "rgba(155,114,207,0.18)",
        border: selected ? "1.5px solid rgba(155,114,207,0.6)" : "1.5px solid rgba(155,114,207,0.25)",
        transition: "all 0.15s",
        boxShadow: selected ? "0 2px 8px rgba(155,114,207,0.3)" : "none",
      }} />
      <span style={{ fontSize: 9, color: selected ? "#7b4fc4" : "#9b8fc4", fontWeight: selected ? 600 : 400 }}>
        {w}:{h}
      </span>
    </div>
  );
}

const VIDEO_DURATIONS = [6, 10];

const VIDEO_RESOLUTIONS = [
  { value: "512P", label: "512P" },
  { value: "720P", label: "720P" },
  { value: "768P", label: "768P" },
  { value: "1080P", label: "1080P" },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "#8a8394",
  running: "#9b72cf",
  done: "#7ab89a",
  failed: "#d98a8a",
};
const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  running: "执行中",
  done: "已完成",
  failed: "失败",
};

const TYPE_ICONS: Record<string, string> = {
  user: "👤",
  auto: "🤖",
};

export default function QueuePage() {
  const queryClient = useQueryClient();

  // 提交表单
  const [cat, setCat] = useState("t2i");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("image-01");
  const [notes, setNotes] = useState("");
  const [submitMsg, setSubmitMsg] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageFile2, setImageFile2] = useState<File | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [imageAssetPath, setImageAssetPath] = useState<string | null>(null);
  const [imageAssetPath2, setImageAssetPath2] = useState<string | null>(null);
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [duration, setDuration] = useState(6);
  const [resolution, setResolution] = useState("768P");
  const [isInstrumental, setIsInstrumental] = useState(false);

  // Auto 生成
  const [direction, setDirection] = useState("");
  const [autoCount, setAutoCount] = useState(3);

  const needsImage = cat === "i2i" || cat === "i2v";

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => tasksApi.list({ limit: 200 }),
  });

  const { data: directions = [] } = useQuery({
    queryKey: ["task-directions"],
    queryFn: () => tasksApi.listDirections(),
  });

  const createMut = useMutation({
    mutationFn: async (data: { category: string; prompt_text: string; model: string; notes?: string; image?: string; image2?: string; aspect_ratio?: string }) => {
      return tasksApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setPrompt("");
      setNotes("");
      setSubmitMsg("✅ 任务已加入队列");
      setTimeout(() => setSubmitMsg(""), 3000);
    },
    onError: () => setSubmitMsg("❌ 提交失败"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => tasksApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const generateAutoMut = useMutation({
    mutationFn: (data: { direction: string; count: number }) =>
      tasksApi.generateAuto({ direction: data.direction, count: data.count, theme: "giant-tree" }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["task-directions"] });
      setDirection("");
      alert(`✅ 生成了 ${res.created} 个 Auto 任务：${res.categories.join(", ")}`);
    },
  });

  const today = new Date().toISOString().split("T")[0];
  const pendingTasks = tasks.filter((t) => t.status === "pending");
  const doneTasks = tasks.filter((t) => t.status !== "pending");

  function handleCatChange(c: string) {
    setCat(c);
    setImageFile(null);
    setImageFile2(null);
    setImageAssetPath(null);
    setImageAssetPath2(null);
    setPickerOpen(false);
    const found = CATEGORIES.find((x) => x.value === c);
    if (found) setModel(found.model_default);
    if (c !== "t2i" && c !== "i2i") setAspectRatio("16:9");
    if (c !== "t2v" && c !== "i2v" && c !== "fl2v" && c !== "s2v") {
      setDuration(6);
      setResolution("768P");
    }
    if (c !== "music") setIsInstrumental(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    if (needsImage && !imageFile && !imageAssetPath) return;

    let imagePath: string | undefined;
    let image2Path: string | undefined;

    if (imageAssetPath) {
      imagePath = imageAssetPath;
    } else if (imageFile) {
      const res = await generateApi.upload(imageFile);
      imagePath = res.file_path;
    }

    if (imageAssetPath2) {
      image2Path = imageAssetPath2;
    } else if (imageFile2) {
      const res = await generateApi.upload(imageFile2);
      image2Path = res.file_path;
    }

    createMut.mutate({ category: cat, prompt_text: prompt.trim(), model, notes: notes.trim() || undefined, image: imagePath, image2: image2Path, aspect_ratio: aspectRatio, duration: duration, resolution: resolution, is_instrumental: isInstrumental });
  }

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", marginBottom: 4 }}>
          📤 任务队列
        </h2>
        <p style={{ fontSize: 13, color: "#bdb9c8" }}>
          {today} · {pendingTasks.length} 个等待中 · {doneTasks.length} 个已完成
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>

        {/* 左侧：提交新任务 */}
        <div>
          <div style={{
            background: "rgba(255,255,255,0.68)",
            backdropFilter: "blur(18px)",
            border: "1px solid rgba(255,255,255,0.8)",
            borderRadius: 18,
            padding: 24,
            marginBottom: 16,
          }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#6b6375", marginBottom: 16 }}>
              提交用户任务
            </h3>
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* 类型选择 */}
              <div>
                <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>任务类型</label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
                  {CATEGORIES.map((c) => (
                    <div
                      key={c.value}
                      onClick={() => handleCatChange(c.value)}
                      style={{
                        padding: "8px 0", textAlign: "center",
                        borderRadius: 10, cursor: "pointer", fontSize: 12, fontWeight: 500,
                        background: cat === c.value
                          ? "linear-gradient(135deg, rgba(155,114,207,0.22), rgba(196,174,226,0.15))"
                          : "rgba(255,255,255,0.5)",
                        color: cat === c.value ? "#7b4fc4" : "#8a8394",
                        border: cat === c.value ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.3)",
                        transition: "all 0.18s",
                      }}
                    >
                      {c.label}
                    </div>
                  ))}
                </div>
              </div>

              {/* Prompt */}
              <div>
                <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>Prompt</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="描述你想生成的内容..."
                  rows={4}
                  style={{
                    width: "100%", boxSizing: "border-box",
                    padding: "10px 14px", borderRadius: 12,
                    border: "1px solid rgba(200,195,215,0.4)",
                    background: "rgba(255,255,255,0.6)",
                    fontSize: 13, color: "#3d3545",
                    fontFamily: "var(--font-main)",
                    resize: "vertical",
                    outline: "none",
                  }}
                />
              </div>

              {/* 模型 */}
              <div>
                <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>模型</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="input"
                  style={{ maxWidth: 300 }}
                >
                  {CATEGORIES.find((c) => c.value === cat)?.value === "t2i" || CATEGORIES.find((c) => c.value === cat)?.value === "i2i" ? (
                    <>
                      <option value="image-01">image-01</option>
                    </>
                  ) : CATEGORIES.find((c) => c.value === cat)?.value === "t2v" ? (
                    <>
                      <option value="MiniMax-Hailuo-2.3">MiniMax-Hailuo-2.3</option>
                    </>
                  ) : CATEGORIES.find((c) => c.value === cat)?.value === "i2v" ? (
                    <>
                      <option value="MiniMax-Hailuo-2.3-Fast">MiniMax-Hailuo-2.3-Fast</option>
                    </>
                  ) : CATEGORIES.find((c) => c.value === cat)?.value === "music" ? (
                    <>
                      <option value="music-2.6">music-2.6</option>
                    </>
                  ) : null}
                </select>
              </div>

              {/* 图片比例（仅 t2i / i2i） */}
              {(cat === "t2i" || cat === "i2i") && (
                <div>
                  <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 8, display: "block" }}>输出比例</label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-end" }}>
                    {ASPECT_RATIOS.map((r) => (
                      <div
                        key={r.value}
                        onClick={() => setAspectRatio(r.value)}
                        style={{
                          display: "flex", flexDirection: "column", alignItems: "center",
                          cursor: "pointer",
                          padding: "8px 10px", borderRadius: 10,
                          background: aspectRatio === r.value ? "rgba(155,114,207,0.08)" : "transparent",
                          border: aspectRatio === r.value ? "1px solid rgba(155,114,207,0.3)" : "1px solid transparent",
                          transition: "all 0.15s",
                        }}
                      >
                        <AspectBox w={r.w} h={r.h} selected={aspectRatio === r.value} />
                        <span style={{ fontSize: 9, color: aspectRatio === r.value ? "#7b4fc4" : "#9b8fc4", marginTop: 4, fontWeight: 500 }}>
                          {r.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 视频参数（仅 t2v / i2v / fl2v / s2v） */}
              {(cat === "t2v" || cat === "i2v" || cat === "fl2v" || cat === "s2v") && (
                <>
                  <div>
                    <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>视频时长</label>
                    <div style={{ display: "flex", gap: 6 }}>
                      {VIDEO_DURATIONS.map((d) => (
                        <div
                          key={d}
                          onClick={() => setDuration(d)}
                          style={{
                            padding: "5px 14px", borderRadius: 8, fontSize: 12, cursor: "pointer",
                            background: duration === d ? "rgba(155,114,207,0.2)" : "rgba(255,255,255,0.5)",
                            color: duration === d ? "#7b4fc4" : "#8a8394",
                            border: duration === d ? "1px solid rgba(155,114,207,0.35)" : "1px solid rgba(200,195,215,0.3)",
                            fontWeight: duration === d ? 600 : 400,
                          }}
                        >
                          {d}秒
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>分辨率</label>
                    <div style={{ display: "flex", gap: 6 }}>
                      {VIDEO_RESOLUTIONS.map((r) => (
                        <div
                          key={r.value}
                          onClick={() => setResolution(r.value)}
                          style={{
                            padding: "5px 14px", borderRadius: 8, fontSize: 12, cursor: "pointer",
                            background: resolution === r.value ? "rgba(155,114,207,0.2)" : "rgba(255,255,255,0.5)",
                            color: resolution === r.value ? "#7b4fc4" : "#8a8394",
                            border: resolution === r.value ? "1px solid rgba(155,114,207,0.35)" : "1px solid rgba(200,195,215,0.3)",
                            fontWeight: resolution === r.value ? 600 : 400,
                          }}
                        >
                          {r.label}
                        </div>
                      ))}
                    </div>
                    {cat === "i2v" && (
                      <div style={{ fontSize: 11, color: "#b0a8bc", marginTop: 4 }}>
                        注：输出比例由参考图比例决定
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* 音乐参数（仅 music） */}
              {cat === "music" && (
                <div>
                  <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>
                    <input
                      type="checkbox"
                      checked={isInstrumental}
                      onChange={(e) => setIsInstrumental(e.target.checked)}
                      style={{ marginRight: 6 }}
                    />
                    纯音乐（无人声）
                  </label>
                </div>
              )}

              {/* 图片上传/选择（i2i / i2v） */}
              {needsImage && (
                <div>
                  <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>
                    参考图片
                  </label>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() => setPickerOpen(true)}
                      style={{
                        padding: "6px 14px", borderRadius: 10, fontSize: 12,
                        background: "rgba(155,114,207,0.1)",
                        border: "1px solid rgba(155,114,207,0.25)",
                        color: "#7b4fc4", cursor: "pointer",
                      }}
                    >
                      从资产库选择
                    </button>
                    <span style={{ fontSize: 12, color: "#bdb9c8" }}>或</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => { setImageFile(e.target.files?.[0] ?? null); setPickerOpen(false); }}
                      style={{ fontSize: 12 }}
                    />
                  </div>
                  {imageFile && (
                    <div style={{ fontSize: 11, color: "#7ab89a", marginTop: 4 }}>
                      本地: {imageFile.name}
                    </div>
                  )}
                </div>
              )}

              
              {/* 资产选择弹窗 */}
              {pickerOpen && (
                <AssetPickerDialog
                  modality="image"
                  onSelect={(asset) => {
                    setImageAssetPath(asset.file_path);
                    setImageFile(null);
                    setPickerOpen(false);
                  }}
                  onClose={() => setPickerOpen(false)}
                />
              )}

              {/* 备注 */}
              <div>
                <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>备注（可选）</label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="备注信息..."
                  className="input"
                  style={{ maxWidth: 300 }}
                />
              </div>

              <button
                type="submit"
                disabled={createMut.isPending || !prompt.trim() || (needsImage && !imageFile)}
                style={{
                  padding: "10px 20px", borderRadius: 12,
                  background: "linear-gradient(135deg, rgba(155,114,207,0.8), rgba(196,174,226,0.6))",
                  border: "none", color: "#fff", fontSize: 14, fontWeight: 600,
                  cursor: createMut.isPending ? "not-allowed" : "pointer",
                  opacity: createMut.isPending ? 0.6 : 1,
                }}
              >
                {createMut.isPending ? "提交中..." : "加入队列"}
              </button>

              {submitMsg && (
                <div style={{ fontSize: 13, color: "#7ab89a" }}>{submitMsg}</div>
              )}
            </form>
          </div>

          {/* Auto prompt 生成 */}
          <div style={{
            background: "rgba(255,255,255,0.68)",
            backdropFilter: "blur(18px)",
            border: "1px solid rgba(255,255,255,0.8)",
            borderRadius: 18,
            padding: 24,
          }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: "#6b6375", marginBottom: 16 }}>
              🤖 Auto 任务生成
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 6, display: "block" }}>方向描述</label>
                <input
                  type="text"
                  value={direction}
                  onChange={(e) => setDirection(e.target.value)}
                  placeholder="例如：巨树世界的四季变化、白天的市场集市..."
                  className="input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <label style={{ fontSize: 12, color: "#8a8394" }}>生成数量</label>
                <input
                  type="number"
                  min={1} max={10}
                  value={autoCount}
                  onChange={(e) => setAutoCount(Number(e.target.value))}
                  className="input"
                  style={{ width: 70 }}
                />
              </div>
              {directions.length > 0 && (
                <div style={{ fontSize: 12, color: "#bdb9c8" }}>
                  已用方向：{directions.map((d) => (
                    <span key={d} style={{ marginRight: 6 }}>· {d}</span>
                  ))}
                </div>
              )}
              <button
                onClick={() => {
                  if (!direction.trim()) return;
                  generateAutoMut.mutate({ direction: direction.trim(), count: autoCount });
                }}
                disabled={generateAutoMut.isPending || !direction.trim()}
                style={{
                  padding: "9px 18px", borderRadius: 12,
                  background: "rgba(155,114,207,0.15)",
                  border: "1px solid rgba(155,114,207,0.3)",
                  color: "#7b4fc4", fontSize: 13, fontWeight: 600,
                  cursor: generateAutoMut.isPending ? "not-allowed" : "pointer",
                  opacity: generateAutoMut.isPending ? 0.6 : 1,
                }}
              >
                {generateAutoMut.isPending ? "生成中..." : "LLM 生成 Auto 任务"}
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：队列列表 */}
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#6b6375", marginBottom: 12 }}>
            等待执行 ({pendingTasks.length})
          </div>

          {isLoading && <div style={{ color: "#bdb9c8", fontSize: 13 }}>加载中...</div>}

          {!isLoading && pendingTasks.length === 0 && (
            <div style={{
              background: "rgba(255,255,255,0.45)", borderRadius: 16,
              padding: "20px", marginBottom: 16, border: "1px dashed rgba(200,195,215,0.4)",
              fontSize: 13, color: "#bdb9c8", textAlign: "center",
            }}>
              队列为空，输入任务后点击"加入队列"
            </div>
          )}

          {pendingTasks.map((task) => (
            <div key={task.id} style={{
              background: "rgba(255,255,255,0.68)",
              backdropFilter: "blur(14px)",
              border: "1px solid rgba(255,255,255,0.8)",
              borderRadius: 14, padding: "14px 16px", marginBottom: 8,
              display: "flex", gap: 10, alignItems: "flex-start",
            }}>
              <span style={{ fontSize: 16 }}>{TYPE_ICONS[task.task_type] || "📋"}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 5 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 50,
                    background: "rgba(155,114,207,0.1)", color: "#9b72cf",
                  }}>
                    {task.category}
                  </span>
                  <span style={{ fontSize: 11, color: "#8a8394" }}>{task.model}</span>
                  <span style={{ fontSize: 11, color: STATUS_COLORS[task.status] }}>
                    {STATUS_LABELS[task.status]}
                  </span>
                </div>
                <div style={{
                  fontSize: 12.5, color: "#5a5470", lineHeight: 1.6,
                  overflow: "hidden", display: "-webkit-box",
                  WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                }}>
                  {task.prompt_text}
                </div>
                {task.notes && (
                  <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 3 }}>备注: {task.notes}</div>
                )}
              </div>
              <button
                onClick={() => deleteMut.mutate(task.id)}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  fontSize: 14, color: "#d98a8a", padding: "2px 6px",
                }}
                title="删除"
              >
                🗑
              </button>
            </div>
          ))}

          {doneTasks.length > 0 && (
            <>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#6b6375", margin: "20px 0 12px" }}>
                已完成 ({doneTasks.length})
              </div>
              {doneTasks.map((task) => (
                <div key={task.id} style={{
                  background: "rgba(255,255,255,0.45)",
                  border: "1px solid rgba(200,195,215,0.25)",
                  borderRadius: 12, padding: "10px 14px", marginBottom: 6,
                  display: "flex", gap: 10, alignItems: "center",
                  opacity: 0.7,
                }}>
                  <span style={{ fontSize: 14 }}>{TYPE_ICONS[task.task_type] || "📋"}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: 11, color: "#8a8394" }}>{task.category}</span>
                    <span style={{ fontSize: 11, color: STATUS_COLORS[task.status], marginLeft: 8 }}>
                      {STATUS_LABELS[task.status]}
                    </span>
                    <div style={{
                      fontSize: 12, color: "#6b6375",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {task.prompt_text}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteMut.mutate(task.id)}
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      fontSize: 13, color: "#d98a8a", padding: "2px 6px",
                    }}
                  >
                    🗑
                  </button>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
