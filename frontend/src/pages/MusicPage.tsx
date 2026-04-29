import { useState, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { musicApi, type MusicGenerateParams } from "../api/music";
import { quotasApi } from "../api/quotas";

const FILE_BASE = "http://localhost:8000/files";

// ── Music models with quota info ──────────────────────────────────────────────
const MUSIC_MODELS = [
  { value: "music-2.6", label: "music-2.6（推荐）", quota: 100, desc: "文本描述+歌词→生成完整歌曲" },
  { value: "music-2.6-free", label: "music-2.6-free（限免）", quota: 4, desc: "2.6限免版，RPM较低" },
  { value: "music-cover", label: "music-cover（翻唱）", quota: 100, desc: "参考音频→生成翻唱版本，需上传音频" },
  { value: "music-cover-free", label: "music-cover-free（翻唱限免）", quota: 4, desc: "翻唱限免版" },
];

const LYRICS_MODEL = "lyrics_generation";

// ── Default params ─────────────────────────────────────────────────────────────
const DEFAULT_PARAMS: MusicGenerateParams = {
  prompt: "",
  model: "music-2.6",
  lyrics: "",
  is_instrumental: false,
  lyrics_optimizer: false,
  output_format: "url",
  aigc_watermark: false,
  audio_url: "",
  variant: "default",
  theme: "giant-tree",
};

// ── Helper ────────────────────────────────────────────────────────────────────
function parseLines(text: string): string[] {
  return text.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
}

function buildPrompt(base: string, extra: string): string {
  if (!base.trim()) return extra.trim();
  const sep = /[.!?,;]$/.test(base) ? " " : ", ";
  return `${base.trim()}${sep}${extra.trim()}`;
}

// ── Audio player helper ───────────────────────────────────────────────────────
function AudioPlayer({ src }: { src: string }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [paused, setPaused] = useState(false);

  function play() {
    if (!audioRef.current) return;
    if (paused) {
      audioRef.current.play();
      setPaused(false);
      setPlaying(true);
      return;
    }
    if (playing) {
      audioRef.current.pause();
      setPaused(true);
      setPlaying(false);
      return;
    }
    audioRef.current.play();
    setPlaying(true);
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
      <audio ref={audioRef} src={src} onEnded={() => setPlaying(false)} />
      <button
        onClick={play}
        style={{
          padding: "5px 14px", borderRadius: 8, border: "none",
          background: playing ? "#7b4fc4" : paused ? "rgba(123,79,196,0.3)" : "rgba(123,79,196,0.15)",
          color: playing || paused ? "#fff" : "#7b4fc4",
          fontSize: 12, fontWeight: 500, cursor: "pointer",
        }}
      >
        {playing ? "⏸ 播放中" : paused ? "▶ 继续" : "▶ 播放"}
      </button>
    </div>
  );
}

// ── Slider field ──────────────────────────────────────────────────────────────
function SliderField({ label, value, min, max, step, display, onChange }: {
  label: string; value: number; min: number; max: number; step: number;
  display: string; onChange: (v: number) => void;
}) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <label style={{ fontSize: 12, color: "#8a8394" }}>{label}</label>
        <span style={{ fontSize: 12, color: "#7b4fc4", fontWeight: 600 }}>{display}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", accentColor: "#7b4fc4" }}
      />
    </div>
  );
}

// ── Saved config type ──────────────────────────────────────────────────────────
interface SavedConfig {
  id: string;
  name: string;
  params: MusicGenerateParams;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Single music generation tab
// ─────────────────────────────────────────────────────────────────────────────
function SingleMusicTab() {
  const [params, setParams] = useState<MusicGenerateParams>({ ...DEFAULT_PARAMS });
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [result, setResult] = useState<{ run_id: string; file_path: string; prompt_text: string } | null>(null);
  const [savedConfigs, setSavedConfigs] = useState<SavedConfig[]>([]);

  // Quick param update
  function update(key: keyof MusicGenerateParams, value: unknown) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  // Save current params as config
  function saveConfig() {
    if (!params.prompt.trim()) return;
    const name = prompt("输入配置名称：")?.trim();
    if (!name) return;
    const config: SavedConfig = {
      id: Date.now().toString(),
      name,
      params: { ...params },
      created_at: new Date().toISOString(),
    };
    setSavedConfigs((prev) => [config, ...prev]);
    localStorage.setItem("music_configs", JSON.stringify([config, ...savedConfigs]));
  }

  // Load config
  function loadConfig(cfg: SavedConfig) {
    setParams({ ...cfg.params });
  }

  // Delete config
  function deleteConfig(id: string) {
    const updated = savedConfigs.filter((c) => c.id !== id);
    setSavedConfigs(updated);
    localStorage.setItem("music_configs", JSON.stringify(updated));
  }

  // Import params from result (prompt + lyrics -> params)
  function importFromResult() {
    if (!result) return;
    setParams((p) => ({
      ...p,
      prompt: result.prompt_text,
      lyrics: "",
    }));
  }

  async function handleGenerate() {
    if (!params.prompt.trim()) {
      setGenError("请输入音乐描述（prompt）");
      return;
    }
    if (params.model?.includes("cover") && !params.audio_url?.trim()) {
      setGenError("翻唱模型需要填写参考音频 URL");
      return;
    }
    if (!params.is_instrumental && !params.lyrics.trim() && !params.lyrics_optimizer) {
      setGenError("请输入歌词，或选择纯音乐，或开启歌词优化");
      return;
    }
    setGenerating(true);
    setGenError(null);
    setResult(null);
    try {
      const resp = await musicApi.generate(params);
      if (resp.assets.length > 0) {
        const asset = resp.assets[0];
        setResult({
          run_id: resp.run_id,
          file_path: asset.file_path,
          prompt_text: asset.prompt_text,
        });
      }
    } catch (e: unknown) {
      setGenError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
      {/* 左侧：参数表单 */}
      <div style={{
        background: "rgba(255,255,255,0.75)",
        borderRadius: 14, border: "1px solid rgba(200,195,215,0.3)",
        padding: "20px 22px",
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#3d3545", marginBottom: 16 }}>
          🎵 音乐生成参数
        </h3>

        {genError && (
          <div style={{
            background: "rgba(239,68,68,0.1)", borderRadius: 8,
            padding: "8px 12px", marginBottom: 12, fontSize: 12, color: "#ef4444",
          }}>
            ⚠️ {genError}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* 模型选择 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>模型</label>
            <select
              value={params.model}
              onChange={(e) => update("model", e.target.value)}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                padding: "6px 10px", fontSize: 13, color: "#3d3545", background: "#fff",
              }}
            >
              {MUSIC_MODELS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}（每日{m.quota}次）
                </option>
              ))}
            </select>
            <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 4 }}>
              {MUSIC_MODELS.find((m) => m.value === params.model)?.desc}
            </div>
          </div>

          {/* music-cover 需要参考音频 URL */}
          {params.model.includes("cover") && (
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>
                参考音频 URL <span style={{ color: "#ef4444" }}>*</span>
                <span style={{ fontWeight: 400, color: "#bdb9c8", marginLeft: 6 }}>6秒~6分钟，≤50MB</span>
              </label>
              <input
                value={params.audio_url || ""}
                onChange={(e) => update("audio_url", e.target.value)}
                placeholder="https://example.com/your-song.mp3"
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "6px 10px", fontSize: 13, color: "#3d3545",
                }}
              />
            </div>
          )}

          {/* 音乐描述 prompt */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>
              音乐描述 <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <textarea
              value={params.prompt}
              onChange={(e) => update("prompt", e.target.value)}
              placeholder="例如：独立民谣,忧郁,内省,渴望,独自漫步,咖啡馆"
              rows={3}
              maxLength={2000}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                padding: "8px 10px", fontSize: 13, color: "#3d3545",
                resize: "vertical", fontFamily: "var(--font-main)",
              }}
            />
            <div style={{ fontSize: 10, color: "#bdb9c8", textAlign: "right", marginTop: 2 }}>
              {params.prompt.length}/2000
            </div>
          </div>

          {/* 纯音乐开关 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              id="is_instrumental"
              checked={params.is_instrumental}
              onChange={(e) => update("is_instrumental", e.target.checked)}
            />
            <label htmlFor="is_instrumental" style={{ fontSize: 13, color: "#8a8394", cursor: "pointer" }}>
              纯音乐（无人声）
            </label>
          </div>

          {/* 歌词 */}
          {!params.is_instrumental && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <label style={{ fontSize: 12, color: "#8a8394" }}>歌词</label>
                <label style={{ fontSize: 11, color: "#8a8394", display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    type="checkbox"
                    checked={params.lyrics_optimizer}
                    onChange={(e) => update("lyrics_optimizer", e.target.checked)}
                    style={{ accentColor: "#7b4fc4" }}
                  />
                  自动生成歌词
                </label>
              </div>
              <textarea
                value={params.lyrics}
                onChange={(e) => update("lyrics", e.target.value)}
                placeholder={'[verse]\n街灯微亮晚风轻抚\n影子拉长独自漫步\n[chorus]\n推开木门香气弥漫'}
                rows={5}
                maxLength={3500}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "8px 10px", fontSize: 13, color: "#3d3545",
                  resize: "vertical", fontFamily: "var(--font-main)",
                }}
              />
              <div style={{ fontSize: 10, color: "#bdb9c8", textAlign: "right", marginTop: 2 }}>
                {params.lyrics.length}/3500
              </div>
              <div style={{ fontSize: 10, color: "#bdb9c8", marginTop: 3 }}>
                结构标签：[Intro] [Verse] [Pre Chorus] [Chorus] [Interlude] [Bridge] [Outro] [Break] [Hook]
              </div>
            </div>
          )}

          {/* 输出格式 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>输出格式</label>
            <div style={{ display: "flex", gap: 8 }}>
              {[
                { value: "url", label: "URL（自动下载）" },
                { value: "hex", label: "HEX（直接返回）" },
              ].map((f) => (
                <button
                  key={f.value}
                  onClick={() => update("output_format", f.value)}
                  style={{
                    flex: 1, padding: "6px 0", borderRadius: 8, border: "none",
                    background: params.output_format === f.value
                      ? "rgba(123,79,196,0.15)" : "rgba(255,255,255,0.5)",
                    color: params.output_format === f.value ? "#7b4fc4" : "#8a8394",
                    fontSize: 12, fontWeight: 500, cursor: "pointer",
                    border: params.output_format === f.value
                      ? "1px solid rgba(123,79,196,0.3)" : "1px solid rgba(200,195,215,0.3)",
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* 音频设置 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>音频设置</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <select
                value={params.audio_setting?.sample_rate || 44100}
                onChange={(e) => update("audio_setting", {
                  ...params.audio_setting,
                  sample_rate: Number(e.target.value),
                })}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "5px 8px", fontSize: 12, color: "#3d3545", background: "#fff",
                }}
              >
                <option value={16000}>16000 Hz</option>
                <option value={24000}>24000 Hz</option>
                <option value={32000}>32000 Hz</option>
                <option value={44100}>44100 Hz</option>
              </select>
              <select
                value={params.audio_setting?.bitrate || 256000}
                onChange={(e) => update("audio_setting", {
                  ...params.audio_setting,
                  bitrate: Number(e.target.value),
                })}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "5px 8px", fontSize: 12, color: "#3d3545", background: "#fff",
                }}
              >
                <option value={32000}>32 kbps</option>
                <option value={64000}>64 kbps</option>
                <option value={128000}>128 kbps</option>
                <option value={256000}>256 kbps</option>
              </select>
              <select
                value={params.audio_setting?.format || "mp3"}
                onChange={(e) => update("audio_setting", {
                  ...params.audio_setting,
                  format: e.target.value,
                })}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "5px 8px", fontSize: 12, color: "#3d3545", background: "#fff",
                }}
              >
                <option value="mp3">MP3</option>
                <option value="wav">WAV</option>
                <option value="pcm">PCM</option>
              </select>
            </div>
          </div>

          {/* AI 水印 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              id="aigc_watermark"
              checked={params.aigc_watermark}
              onChange={(e) => update("aigc_watermark", e.target.checked)}
              style={{ accentColor: "#7b4fc4" }}
            />
            <label htmlFor="aigc_watermark" style={{ fontSize: 13, color: "#8a8394", cursor: "pointer" }}>
              添加 AI 水印标识
            </label>
          </div>

          {/* 变体标记 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>变体标记</label>
            <input
              value={params.variant || ""}
              onChange={(e) => update("variant", e.target.value)}
              placeholder="例如：folk-01"
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                padding: "6px 10px", fontSize: 13, color: "#3d3545",
              }}
            />
          </div>

          {/* 操作按钮 */}
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button
              onClick={handleGenerate}
              disabled={generating}
              style={{
                flex: 1, padding: "10px 0", borderRadius: 10, border: "none",
                background: generating ? "rgba(123,79,196,0.3)" : "rgba(123,79,196,0.85)",
                color: "#fff", fontSize: 14, fontWeight: 600,
                cursor: generating ? "default" : "pointer",
              }}
            >
              {generating ? "🎵 生成中..." : "🎵 生成音乐"}
            </button>
            <button
              onClick={saveConfig}
              style={{
                padding: "10px 16px", borderRadius: 10,
                background: "rgba(255,255,255,0.5)",
                border: "1px solid rgba(200,195,215,0.4)",
                color: "#6b6375", fontSize: 13, cursor: "pointer",
              }}
            >
              💾 保存配置
            </button>
          </div>
        </div>
      </div>

      {/* 右侧：结果 + 配置列表 */}
      <div>
        {/* 生成结果 */}
        <div style={{
          background: "rgba(255,255,255,0.75)",
          borderRadius: 14, border: "1px solid rgba(200,195,215,0.3)",
          padding: "20px 22px", marginBottom: 20,
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: "#3d3545", marginBottom: 12 }}>
            🎵 生成结果
          </h3>
          {result ? (
            <div>
              <div style={{
                background: "rgba(34,197,94,0.08)", borderRadius: 10, padding: "12px 14px",
                border: "1px solid rgba(34,197,94,0.2)", marginBottom: 10,
              }}>
                <div style={{ fontSize: 12, color: "#22c55e", fontWeight: 600, marginBottom: 4 }}>
                  ✅ 生成成功
                </div>
                <div style={{ fontSize: 11, color: "#8a8394", fontFamily: "monospace" }}>
                  {result.run_id}
                </div>
              </div>
              <AudioPlayer src={`${FILE_BASE}/${result.file_path}`} />
              <div style={{ marginTop: 10 }}>
                <button
                  onClick={importFromResult}
                  style={{
                    padding: "6px 14px", borderRadius: 8,
                    background: "rgba(123,79,196,0.1)",
                    border: "1px solid rgba(123,79,196,0.25)",
                    color: "#7b4fc4", fontSize: 12, cursor: "pointer",
                  }}
                >
                  📥 导入参数到表单
                </button>
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#bdb9c8" }}>
                prompt: {result.prompt_text.slice(0, 100)}{result.prompt_text.length > 100 ? "..." : ""}
              </div>
            </div>
          ) : (
            <div style={{ color: "#bdb9c8", fontSize: 13, textAlign: "center", padding: "20px 0" }}>
              {generating ? "生成中，请稍候..." : "配置参数后点击「生成音乐」"}
            </div>
          )}
        </div>

        {/* 保存的配置列表 */}
        {savedConfigs.length > 0 && (
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#6b6375", marginBottom: 8 }}>
              📋 已保存配置（{savedConfigs.length}）
            </div>
            {savedConfigs.map((cfg) => (
              <div
                key={cfg.id}
                style={{
                  background: "rgba(255,255,255,0.6)",
                  borderRadius: 10, border: "1px solid rgba(200,195,215,0.25)",
                  padding: "10px 14px", marginBottom: 6,
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}
              >
                <div
                  onClick={() => loadConfig(cfg)}
                  style={{ cursor: "pointer", flex: 1 }}
                >
                  <div style={{ fontSize: 13, color: "#3d3545", fontWeight: 500 }}>{cfg.name}</div>
                  <div style={{ fontSize: 11, color: "#bdb9c8", marginTop: 2 }}>
                    {cfg.params.model} · {new Date(cfg.created_at).toLocaleDateString("zh-CN")}
                  </div>
                  <div style={{ fontSize: 10, color: "#9b8fc4", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {cfg.params.prompt.slice(0, 50)}{cfg.params.prompt.length > 50 ? "..." : ""}
                  </div>
                </div>
                <button
                  onClick={() => deleteConfig(cfg.id)}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    fontSize: 12, color: "#d98a8a", padding: "4px 8px",
                  }}
                >
                  🗑
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Matrix music generation tab
// ─────────────────────────────────────────────────────────────────────────────
interface MusicCell {
  row: number;
  col: number;
  status: "idle" | "generating" | "done" | "error";
  file_path?: string;
  error?: string;
  prompt_text?: string;
  run_id?: string;
}

function MatrixMusicTab() {
  const [basePrompt, setBasePrompt] = useState("巨树世界，神秘而宁静");
  const [promptRows, setPromptRows] = useState("欢快明亮的旋律\n忧郁沉思的旋律\n史诗般的壮阔\n轻松悠闲的氛围");
  const [styleCols, setStyleCols] = useState("民谣风格\n流行风格\n古典风格\n电子风格");
  const [isInstrumental, setIsInstrumental] = useState(true);
  const [model, setModel] = useState("music-2.6");
  const [cells, setCells] = useState<Record<string, MusicCell>>({});

  const rows = useMemo(() => parseLines(promptRows), [promptRows]);
  const cols = useMemo(() => parseLines(styleCols), [styleCols]);

  function buildCellPrompt(r: number, c: number): string {
    return buildPrompt(basePrompt, `${rows[r]}，${cols[c]}`);
  }

  async function generateCell(r: number, c: number) {
    const key = `${r}-${c}`;
    setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "generating" } }));
    try {
      const prompt = buildCellPrompt(r, c);
      const resp = await musicApi.generate({
        prompt,
        model,
        lyrics: "",
        is_instrumental: true,
        output_format: "url",
        variant: `row${r}-col${c}`,
        theme: "giant-tree",
      });
      const asset = resp.assets[0];
      setCells((prev) => ({
        ...prev,
        [key]: { row: r, col: c, status: "done", file_path: asset.file_path, prompt_text: prompt, run_id: resp.run_id },
      }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setCells((prev) => ({ ...prev, [key]: { row: r, col: c, status: "error", error: msg } }));
    }
  }

  async function generateAll() {
    for (let r = 0; r < rows.length; r++) {
      for (let c = 0; c < cols.length; c++) {
        const key = `${r}-${c}`;
        if (cells[key]?.status === "done" || cells[key]?.status === "generating") continue;
        await generateCell(r, c);
        // Random delay to avoid rate limit
        await new Promise((res) => setTimeout(res, 800 + Math.random() * 1500));
      }
    }
  }

  const doneCount = Object.values(cells).filter((c) => c.status === "done").length;
  const total = rows.length * cols.length;
  const isRunning = Object.values(cells).some((c) => c.status === "generating");
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  function MatrixCell({ cell }: { cell: MusicCell }) {
    const [expanded, setExpanded] = useState(false);
    const bgMap: Record<string, string> = {
      idle: "rgba(200,195,215,0.15)",
      generating: "rgba(155,114,207,0.1)",
      done: "transparent",
      error: "rgba(220,150,150,0.08)",
    };

    return (
      <div
        onClick={() => cell.status === "done" && setExpanded(!expanded)}
        style={{
          minHeight: 80, borderRadius: 10, overflow: "hidden",
          background: bgMap[cell.status],
          border: cell.status === "done"
            ? "1.5px solid rgba(155,114,207,0.3)"
            : "1.5px solid rgba(200,195,215,0.2)",
          cursor: cell.status === "done" ? "pointer" : "default",
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          transition: "all 0.2s", position: "relative", padding: "8px 4px",
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
        {cell.status === "done" && (
          <div style={{ fontSize: 11, color: "#7b4fc4", textAlign: "center" }}>
            <div>🎵</div>
            {expanded && (
              <AudioPlayer src={`${FILE_BASE}/${cell.file_path}`} />
            )}
          </div>
        )}
        {cell.status === "error" && (
          <div title={cell.error || "失败"} style={{ fontSize: 10, color: "#d98a8a", textAlign: "center", padding: 4, cursor: "help" }}>
            ❌ {cell.error ? cell.error.slice(0, 30) : "失败"}
          </div>
        )}
        {cell.status === "idle" && (
          <button
            onClick={(e) => { e.stopPropagation(); generateCell(cell.row, cell.col); }}
            style={{
              position: "absolute", top: 3, right: 3,
              background: "rgba(155,114,207,0.65)", border: "none", borderRadius: 5,
              fontSize: 9, color: "#fff", cursor: "pointer", padding: "2px 5px",
            }}
          >
            生成
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      {/* 通用参数 */}
      <div style={{
        background: "rgba(255,255,255,0.75)",
        borderRadius: 14, border: "1px solid rgba(200,195,215,0.3)",
        padding: "16px 20px", marginBottom: 20,
        display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center",
      }}>
        <div style={{ flex: "1 1 200px" }}>
          <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>基础描述</label>
          <input
            value={basePrompt}
            onChange={(e) => setBasePrompt(e.target.value)}
            style={{
              width: "100%", boxSizing: "border-box",
              border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
              padding: "6px 10px", fontSize: 13, color: "#3d3545",
            }}
          />
        </div>
        <div style={{ flex: "1 1 120px" }}>
          <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>模型</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            style={{
              width: "100%", boxSizing: "border-box",
              border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
              padding: "6px 10px", fontSize: 13, color: "#3d3545", background: "#fff",
            }}
          >
            {MUSIC_MODELS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            id="matrix_instrumental"
            checked={isInstrumental}
            onChange={(e) => setIsInstrumental(e.target.checked)}
            style={{ accentColor: "#7b4fc4" }}
          />
          <label htmlFor="matrix_instrumental" style={{ fontSize: 13, color: "#8a8394", cursor: "pointer" }}>
            纯音乐
          </label>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {doneCount > 0 && (
            <div style={{ fontSize: 12, color: "#8a8394" }}>
              {doneCount}/{total} 已生成 {pct}%
            </div>
          )}
          <button
            onClick={generateAll}
            disabled={isRunning || rows.length === 0 || cols.length === 0}
            style={{
              padding: "8px 20px", borderRadius: 10,
              background: isRunning ? "rgba(123,79,196,0.4)" : "rgba(123,79,196,0.85)",
              border: "none", color: "#fff", fontSize: 13, fontWeight: 600,
              cursor: isRunning ? "not-allowed" : "pointer",
            }}
          >
            {isRunning ? "生成中..." : `🚀 生成全部 ${total} 首`}
          </button>
        </div>
      </div>

      {/* 矩阵配置 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>
        {/* 左侧：行/列配置 */}
        <div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <label style={{ fontSize: 12, color: "#8a8394" }}>音乐主题（每行一个，{rows.length}个）</label>
              <span style={{ fontSize: 11, color: "#bdb9c8" }}>共 {rows.length} 个</span>
            </div>
            <textarea
              value={promptRows}
              onChange={(e) => setPromptRows(e.target.value)}
              rows={6}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)", borderRadius: 12,
                background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                fontFamily: "var(--font-main)", resize: "vertical", outline: "none",
                padding: "10px 12px",
              }}
            />
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <label style={{ fontSize: 12, color: "#8a8394" }}>风格（每列一个，{cols.length}个）</label>
              <span style={{ fontSize: 11, color: "#bdb9c8" }}>共 {cols.length} 个</span>
            </div>
            <textarea
              value={styleCols}
              onChange={(e) => setStyleCols(e.target.value)}
              rows={4}
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)", borderRadius: 12,
                background: "rgba(255,255,255,0.6)", fontSize: 12.5, color: "#3d3545",
                fontFamily: "var(--font-main)", resize: "vertical", outline: "none",
                padding: "10px 12px",
              }}
            />
          </div>
        </div>

        {/* 右侧：矩阵预览 */}
        <div>
          {rows.length > 0 && cols.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "separate", borderSpacing: 5, minWidth: 400 }}>
                <thead>
                  <tr>
                    <th style={{ width: 80, padding: "0 4px 8px", fontSize: 10, color: "#bdb9c8", textAlign: "left" }} />
                    {cols.map((s, c) => (
                      <th key={c} style={{ padding: "0 0 8px" }}>
                        <div style={{
                          fontSize: 11, fontWeight: 700, color: "#7b4fc4",
                          background: "rgba(155,114,207,0.12)",
                          border: "1px solid rgba(155,114,207,0.25)",
                          borderRadius: 8, padding: "4px 8px", cursor: "help",
                          whiteSpace: "nowrap", textAlign: "center",
                        }}>
                          {s.slice(0, 12)}{s.length > 12 ? "…" : ""}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((rowPrompt, r) => (
                    <tr key={r}>
                      <td style={{ padding: "0 4px 0 0" }}>
                        <div style={{
                          background: "rgba(155,114,207,0.08)",
                          border: "1px solid rgba(155,114,207,0.2)",
                          borderRadius: 8, padding: "5px 8px",
                          cursor: "help", minHeight: 80,
                          display: "flex", flexDirection: "column", justifyContent: "center",
                        }}>
                          <div style={{ fontSize: 11, fontWeight: 600, color: "#6b6375" }}>#{r + 1}</div>
                          <div style={{ fontSize: 10, color: "#9b8fc4" }}>
                            {rowPrompt.slice(0, 12)}{rowPrompt.length > 12 ? "…" : ""}
                          </div>
                        </div>
                      </td>
                      {cols.map((_, c) => {
                        const key = `${r}-${c}`;
                        const cell = cells[key] || { row: r, col: c, status: "idle" as const };
                        return (
                          <td key={key} style={{ padding: 0 }}>
                            <MatrixCell cell={cell} />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{
              background: "rgba(255,255,255,0.45)", borderRadius: 16, padding: "40px",
              border: "1px dashed rgba(200,195,215,0.4)", textAlign: "center", color: "#bdb9c8", fontSize: 13,
            }}>
              填写音乐主题和风格配置后，这里将显示矩阵预览
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Lyrics generation tab
// ─────────────────────────────────────────────────────────────────────────────
const TODAY = new Date().toISOString().split("T")[0];

function LyricsTab() {
  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<"write_full_song" | "edit">("write_full_song");
  const [existingLyrics, setExistingLyrics] = useState("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<{ song_title: string; style_tags: string; lyrics: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: lyricsQuota } = useQuery({
    queryKey: ["quota", "lyrics_generation", TODAY],
    queryFn: async () => {
      const all = await quotasApi.listAll(TODAY);
      return all.find((q) => q.model === "lyrics_generation");
    },
  });

  const remaining = lyricsQuota ? lyricsQuota.remaining : 100;

  async function handleGenerate() {
    if (!prompt.trim() && mode === "write_full_song") {
      setError("请输入歌曲主题描述");
      return;
    }
    if (remaining <= 0) {
      setError("歌词生成额度已用完，请明天再来");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const data = await musicApi.generateLyrics({
        mode,
        prompt: prompt || undefined,
        title: title || undefined,
        lyrics: mode === "edit" ? existingLyrics : undefined,
      });
      setResult({
        song_title: data.song_title || "",
        style_tags: data.style_tags || "",
        lyrics: data.lyrics || "",
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function copyLyrics() {
    if (!result) return;
    navigator.clipboard.writeText(result.lyrics);
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <div style={{
        background: "rgba(255,255,255,0.75)",
        borderRadius: 14, border: "1px solid rgba(200,195,215,0.3)",
        padding: "20px 22px", marginBottom: 16,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: "#3d3545", margin: 0 }}>
            🎤 歌词生成
          </h3>
          <span style={{
            fontSize: 11, color: remaining <= 0 ? "#d98a8a" : "#7ab89a",
            background: remaining <= 0 ? "rgba(217,138,138,0.1)" : "rgba(122,184,154,0.1)",
            padding: "2px 8px", borderRadius: 20,
          }}>
            剩余 {remaining}/100 次
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* 模式 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>生成模式</label>
            <div style={{ display: "flex", gap: 8 }}>
              {[
                { value: "write_full_song", label: "写完整歌曲" },
                { value: "edit", label: "编辑/续写歌词" },
              ].map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMode(m.value as typeof mode)}
                  style={{
                    flex: 1, padding: "6px 0", borderRadius: 8, border: "none",
                    background: mode === m.value ? "rgba(123,79,196,0.15)" : "rgba(255,255,255,0.5)",
                    color: mode === m.value ? "#7b4fc4" : "#8a8394",
                    fontSize: 12, fontWeight: 500, cursor: "pointer",
                    border: mode === m.value ? "1px solid rgba(123,79,196,0.3)" : "1px solid rgba(200,195,215,0.3)",
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* 歌曲标题 */}
          <div>
            <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>
              歌曲标题 <span style={{ color: "#bdb9c8", fontWeight: 400 }}>（可选，传入后输出将保持该标题）</span>
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：夏日的海边"
              style={{
                width: "100%", boxSizing: "border-box",
                border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                padding: "6px 10px", fontSize: 13, color: "#3d3545",
              }}
            />
          </div>

          {/* 主题描述（写完整歌曲模式） */}
          {mode === "write_full_song" && (
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>
                歌曲主题 / 风格描述 <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="例如：一首关于夏日海边的轻快情歌"
                rows={3}
                maxLength={2000}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "8px 10px", fontSize: 13, color: "#3d3545",
                  resize: "vertical", fontFamily: "var(--font-main)",
                }}
              />
            </div>
          )}

          {/* 现有歌词（编辑模式） */}
          {mode === "edit" && (
            <div>
              <label style={{ fontSize: 12, color: "#8a8394", marginBottom: 4, display: "block" }}>
                现有歌词 <span style={{ color: "#ef4444" }}>*</span>
                <span style={{ color: "#bdb9c8", fontWeight: 400, marginLeft: 6 }}>用于续写或修改</span>
              </label>
              <textarea
                value={existingLyrics}
                onChange={(e) => setExistingLyrics(e.target.value)}
                placeholder="粘贴现有歌词..."
                rows={5}
                maxLength={3500}
                style={{
                  width: "100%", boxSizing: "border-box",
                  border: "1px solid rgba(200,195,215,0.4)", borderRadius: 8,
                  padding: "8px 10px", fontSize: 13, color: "#3d3545",
                  resize: "vertical", fontFamily: "var(--font-main)",
                }}
              />
            </div>
          )}

          {error && (
            <div style={{ background: "rgba(239,68,68,0.1)", borderRadius: 8, padding: "8px 12px", fontSize: 12, color: "#ef4444" }}>
              ⚠️ {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating || remaining <= 0}
            style={{
              padding: "10px 0", borderRadius: 10, border: "none",
              background: generating || remaining <= 0 ? "rgba(123,79,196,0.3)" : "rgba(123,79,196,0.85)",
              color: "#fff", fontSize: 14, fontWeight: 600, cursor: generating || remaining <= 0 ? "default" : "pointer",
            }}
          >
            {generating ? "🎤 生成中..." : "🎤 生成歌词"}
          </button>
        </div>
      </div>

      {/* 结果展示 */}
      {result && (
        <div style={{
          background: "rgba(255,255,255,0.75)",
          borderRadius: 14, border: "1px solid rgba(200,195,215,0.3)",
          padding: "20px 22px",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "#3d3545", margin: 0 }}>🎵 {result.song_title}</h3>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={copyLyrics}
                style={{
                  padding: "5px 12px", borderRadius: 8,
                  background: "rgba(123,79,196,0.1)",
                  border: "1px solid rgba(123,79,196,0.25)",
                  color: "#7b4fc4", fontSize: 12, cursor: "pointer",
                }}
              >
                📋 复制歌词
              </button>
            </div>
          </div>
          {result.style_tags && (
            <div style={{ fontSize: 11, color: "#9b8fc4", marginBottom: 10 }}>
              风格标签：{result.style_tags}
            </div>
          )}
          <div style={{
            background: "rgba(245,240,255,0.6)", borderRadius: 10,
            padding: "12px 14px", fontSize: 13, color: "#3d3545",
            whiteSpace: "pre-wrap", lineHeight: 1.8, maxHeight: 400, overflowY: "auto",
            fontFamily: "var(--font-main)",
          }}>
            {result.lyrics}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main MusicPage
// ─────────────────────────────────────────────────────────────────────────────
export default function MusicPage() {
  const [tab, setTab] = useState<"single" | "matrix" | "lyrics">("single");

  return (
    <div>
      {/* 标题栏 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 22 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "#3d3545", margin: 0 }}>
          🎵 音乐生成
        </h2>
        <div style={{ display: "flex", gap: 6 }}>
          {[
            { id: "single" as const, label: "单曲生成" },
            { id: "matrix" as const, label: "矩阵生成" },
            { id: "lyrics" as const, label: "歌词生成" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "5px 14px", borderRadius: 50, fontSize: 12, fontWeight: 500,
                cursor: "pointer", transition: "all 0.15s",
                background: tab === t.id ? "rgba(155,114,207,0.18)" : "transparent",
                border: tab === t.id ? "1px solid rgba(155,114,207,0.3)" : "1px solid rgba(200,195,215,0.3)",
                color: tab === t.id ? "#7b4fc4" : "#8a8394",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "single" ? <SingleMusicTab /> : tab === "matrix" ? <MatrixMusicTab /> : <LyricsTab />}
    </div>
  );
}