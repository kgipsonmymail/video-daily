import { useState, useEffect, useCallback } from "react";

const API = "/api/consistency";

interface Variation {
  id: number;
  type: string;
  prompt: string;
  image: string | null;
  score: number | null;
  notes: string;
  order: number;
}

interface Character {
  id: number;
  name: string;
  prompt: string;
  base_image: string | null;
  order: number;
  variations: Variation[];
}

interface Test {
  id: number;
  name: string;
  status: string;
  notes: string;
  created_at: string;
  characters?: Character[];
}

export default function ConsistencyPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [activeTest, setActiveTest] = useState<Test | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  // 创建表单
  const [formName, setFormName] = useState("");
  const [formChars, setFormChars] = useState([
    { name: "角色A", prompt: "a brave warrior with short black hair, wearing silver armor" },
    { name: "角色B", prompt: "a young sorceress with long flowing red hair, wearing blue robes" },
    { name: "角色C", prompt: "a mysterious rogue with dark hood and green eyes" },
    { name: "角色D", prompt: "an old wise dwarf with a long braided beard, wearing leather apron" },
  ]);
  const [formVarTypes, setFormVarTypes] = useState("微笑表情,愤怒表情,战斗姿态,坐姿休息,穿戴头盔,穿着便装");

  // 加载列表
  const loadTests = useCallback(async () => {
    const res = await fetch(`${API}/tests`);
    setTests(await res.json());
  }, []);

  useEffect(() => { loadTests(); }, [loadTests]);

  // 加载详情
  const loadTest = async (id: number) => {
    const res = await fetch(`${API}/tests/${id}`);
    setActiveTest(await res.json());
  };

  // 创建测试
  const createTest = async () => {
    const res = await fetch(`${API}/tests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: formName || `一致性测试-${new Date().toLocaleDateString()}`,
        characters: formChars.filter(c => c.name && c.prompt),
        variation_types: formVarTypes.split(",").map(s => s.trim()).filter(Boolean),
      }),
    });
    const data = await res.json();
    if (data.id) {
      setShowCreate(false);
      loadTests();
      loadTest(data.id);
    }
  };

  // 生成基础图
  const generateBase = async () => {
    if (!activeTest) return;
    await fetch(`${API}/tests/${activeTest.id}/generate-base`, { method: "POST" });
    // 轮询状态
    pollStatus(activeTest.id);
  };

  // 生成变体图
  const generateVariations = async () => {
    if (!activeTest) return;
    await fetch(`${API}/tests/${activeTest.id}/generate-variations`, { method: "POST" });
    pollStatus(activeTest.id);
  };

  // 轮询状态
  const pollStatus = (testId: number) => {
    const interval = setInterval(async () => {
      const res = await fetch(`${API}/tests/${testId}`);
      const data = await res.json();
      setActiveTest(data);
      if (!data.status.includes("generating")) {
        clearInterval(interval);
      }
    }, 3000);
  };

  // 更新评分
  const updateScore = async (variationId: number, score: number, notes: string) => {
    await fetch(`${API}/variations/${variationId}/score`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score, notes }),
    });
    if (activeTest) loadTest(activeTest.id);
  };

  // 删除测试
  const deleteTest = async (id: number) => {
    if (!confirm("确定删除？")) return;
    await fetch(`${API}/tests/${id}`, { method: "DELETE" });
    if (activeTest?.id === id) setActiveTest(null);
    loadTests();
  };

  // 获取变体类型列表
  const getVariationTypes = (): string[] => {
    if (!activeTest?.characters?.length) return [];
    return activeTest.characters[0].variations.map(v => v.type);
  };

  return (
    <div style={{ padding: 16, maxWidth: 1400, margin: "0 auto" }}>
      <h2 style={{ margin: "0 0 16px", fontSize: 20, fontWeight: 700 }}>
        🎭 角色一致性测试
      </h2>

      {/* 工具栏 */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            padding: "8px 16px", borderRadius: 8, border: "1px solid #ddd",
            background: showCreate ? "#f0f0f0" : "#1677ff", color: showCreate ? "#333" : "#fff",
            cursor: "pointer", fontWeight: 600,
          }}
        >
          {showCreate ? "取消" : "＋ 新建测试"}
        </button>
      </div>

      {/* 创建表单 */}
      {showCreate && (
        <div style={{
          padding: 16, borderRadius: 12, border: "1px solid #e0e0e0",
          background: "#fafafa", marginBottom: 16,
        }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>创建一致性测试</h3>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, color: "#666", marginBottom: 4 }}>
              测试名称
            </label>
            <input
              value={formName}
              onChange={e => setFormName(e.target.value)}
              placeholder="自动命名"
              style={{ width: "100%", padding: "6px 10px", borderRadius: 6, border: "1px solid #ddd" }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, color: "#666", marginBottom: 4 }}>
              角色定义（名称 + 英文描述）
            </label>
            {formChars.map((c, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                <input
                  value={c.name}
                  onChange={e => {
                    const next = [...formChars];
                    next[i].name = e.target.value;
                    setFormChars(next);
                  }}
                  placeholder="角色名"
                  style={{ width: 100, padding: "6px 10px", borderRadius: 6, border: "1px solid #ddd" }}
                />
                <input
                  value={c.prompt}
                  onChange={e => {
                    const next = [...formChars];
                    next[i].prompt = e.target.value;
                    setFormChars(next);
                  }}
                  placeholder="英文描述（用于生成基础图）"
                  style={{ flex: 1, padding: "6px 10px", borderRadius: 6, border: "1px solid #ddd" }}
                />
                <button
                  onClick={() => setFormChars(formChars.filter((_, j) => j !== i))}
                  style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #ddd", cursor: "pointer" }}
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              onClick={() => setFormChars([...formChars, { name: "", prompt: "" }])}
              style={{ padding: "6px 12px", borderRadius: 6, border: "1px dashed #aaa", cursor: "pointer", background: "transparent" }}
            >
              + 添加角色
            </button>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 13, color: "#666", marginBottom: 4 }}>
              变体类型（逗号分隔）
            </label>
            <input
              value={formVarTypes}
              onChange={e => setFormVarTypes(e.target.value)}
              style={{ width: "100%", padding: "6px 10px", borderRadius: 6, border: "1px solid #ddd" }}
            />
          </div>

          <button
            onClick={createTest}
            style={{
              padding: "8px 20px", borderRadius: 8, border: "none",
              background: "#1677ff", color: "#fff", cursor: "pointer", fontWeight: 600,
            }}
          >
            创建测试
          </button>
        </div>
      )}

      {/* 测试列表 */}
      {!activeTest && tests.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: 12 }}>
          {tests.map(t => (
            <div
              key={t.id}
              onClick={() => loadTest(t.id)}
              style={{
                padding: 16, borderRadius: 12, border: "1px solid #e0e0e0",
                cursor: "pointer", background: "#fff",
                transition: "box-shadow 0.2s",
              }}
              onMouseEnter={e => (e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.1)")}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = "none")}
            >
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{t.name}</div>
              <div style={{ fontSize: 12, color: "#999" }}>
                {t.created_at} · {t.status}
              </div>
              <button
                onClick={e => { e.stopPropagation(); deleteTest(t.id); }}
                style={{
                  marginTop: 8, padding: "4px 8px", borderRadius: 4,
                  border: "1px solid #ff4d4f", color: "#ff4d4f",
                  background: "transparent", cursor: "pointer", fontSize: 12,
                }}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 测试详情 - 一致性表格 */}
      {activeTest && (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <button
              onClick={() => setActiveTest(null)}
              style={{
                padding: "6px 12px", borderRadius: 6, border: "1px solid #ddd",
                cursor: "pointer", background: "transparent",
              }}
            >
              ← 返回列表
            </button>
            <h3 style={{ margin: 0, fontSize: 18 }}>{activeTest.name}</h3>
            <span style={{ fontSize: 12, color: "#999" }}>{activeTest.status}</span>
          </div>

          {/* 操作按钮 */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <button
              onClick={generateBase}
              disabled={activeTest.status.includes("generating")}
              style={{
                padding: "8px 16px", borderRadius: 8, border: "none",
                background: activeTest.status.includes("generating") ? "#ccc" : "#52c41a",
                color: "#fff", cursor: "pointer", fontWeight: 600,
              }}
            >
              {activeTest.status === "generating_base" ? "生成中..." : "1⃣ 生成基础图"}
            </button>
            <button
              onClick={generateVariations}
              disabled={!activeTest.characters?.some(c => c.base_image) || activeTest.status.includes("generating")}
              style={{
                padding: "8px 16px", borderRadius: 8, border: "none",
                background: !activeTest.characters?.some(c => c.base_image) ? "#ccc" : "#fa8c16",
                color: "#fff", cursor: "pointer", fontWeight: 600,
              }}
            >
              {activeTest.status === "generating_variations" ? "生成中..." : "2⃣ 生成变体图"}
            </button>
          </div>

          {/* 一致性评分表格 */}
          {activeTest.characters && activeTest.characters.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", width: "100%" }}>
                <thead>
                  <tr>
                    <th style={{ padding: 12, border: "1px solid #e0e0e0", background: "#fafafa", textAlign: "left", minWidth: 120 }}>
                      角色
                    </th>
                    <th style={{ padding: 12, border: "1px solid #e0e0e0", background: "#fafafa", textAlign: "center", minWidth: 120 }}>
                      基础图
                    </th>
                    {getVariationTypes().map((type, i) => (
                      <th key={i} style={{ padding: 12, border: "1px solid #e0e0e0", background: "#fafafa", textAlign: "center", minWidth: 160 }}>
                        {type}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeTest.characters.map(char => (
                    <tr key={char.id}>
                      <td style={{ padding: 12, border: "1px solid #e0e0e0", fontWeight: 600 }}>
                        {char.name}
                      </td>
                      <td style={{ padding: 8, border: "1px solid #e0e0e0", textAlign: "center" }}>
                        {char.base_image ? (
                          <img
                            src={`/files/${char.base_image}`}
                            alt={char.name}
                            style={{ width: 100, height: 100, objectFit: "cover", borderRadius: 8 }}
                          />
                        ) : (
                          <div style={{ width: 100, height: 100, background: "#f0f0f0", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "#999", fontSize: 12 }}>
                            待生成
                          </div>
                        )}
                      </td>
                      {char.variations.map(v => (
                        <td key={v.id} style={{ padding: 8, border: "1px solid #e0e0e0", textAlign: "center" }}>
                          {/* 变体图 */}
                          {v.image ? (
                            <img
                              src={`/files/${v.image}`}
                              alt={`${char.name} - ${v.type}`}
                              style={{ width: 120, height: 120, objectFit: "cover", borderRadius: 8, marginBottom: 6 }}
                            />
                          ) : (
                            <div style={{ width: 120, height: 120, background: "#f0f0f0", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: "#999", fontSize: 12, margin: "0 auto 6px" }}>
                              待生成
                            </div>
                          )}

                          {/* 评分星星 */}
                          <div style={{ display: "flex", justifyContent: "center", gap: 2, marginBottom: 4 }}>
                            {[1, 2, 3, 4, 5].map(s => (
                              <button
                                key={s}
                                onClick={() => updateScore(v.id, s, v.notes)}
                                style={{
                                  background: "none", border: "none", cursor: "pointer",
                                  fontSize: 18, color: (v.score || 0) >= s ? "#ffd700" : "#ddd",
                                  padding: 0, lineHeight: 1,
                                }}
                              >
                                ★
                              </button>
                            ))}
                          </div>

                          {/* 备注 */}
                          <input
                            value={v.notes || ""}
                            onChange={e => updateScore(v.id, v.score || 0, e.target.value)}
                            placeholder="备注..."
                            style={{
                              width: "100%", padding: "3px 6px", borderRadius: 4,
                              border: "1px solid #e0e0e0", fontSize: 11, boxSizing: "border-box",
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
