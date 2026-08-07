import { useState, useEffect } from "react";
import axios from "axios";

interface TestResult {
  test_type: string;
  model: string;
  prompt: string;
  status: string;
  file_path?: string;
  file_size_bytes?: number;
  duration_seconds?: number;
  error_message?: string;
  timestamp: string;
  api_response_raw?: any;
}

interface TestHistory {
  tests: Array<{
    results: TestResult[];
    actual_tokens?: Record<string, number>;
    saved_at: string;
  }>;
}

const TEST_TYPES = [
  { key: "image", label: "🖼️ 图片生成", model: "image-01", color: "#4CAF50" },
  { key: "music", label: "🎵 音乐生成", model: "music-2.6", color: "#9C27B0" },
  { key: "video", label: "🎬 视频生成", model: "Hailuo-2.3", color: "#FF9800" },
  { key: "tts", label: "🔊 语音合成", model: "speech-02", color: "#2196F3" },
  { key: "text", label: "💬 文本生成", model: "MiniMax-M2.7", color: "#607D8B" },
];

export default function QuotaTestPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<TestResult[]>([]);
  const [actualTokens, setActualTokens] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<TestHistory>({ tests: [] });
  const [error, setError] = useState<string | null>(null);
  const [runningSingle, setRunningSingle] = useState<string | null>(null);

  // 加载历史记录
  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await axios.get("/api/quota-test/history");
      setHistory(res.data);
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  // 运行所有测试
  const runAllTests = async () => {
    setLoading(true);
    setError(null);
    setResults([]);
    
    try {
      const res = await axios.post("/api/quota-test/run-all");
      setResults(res.data.results);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "测试失败");
    } finally {
      setLoading(false);
    }
  };

  // 运行单个测试
  const runSingleTest = async (type: string) => {
    setRunningSingle(type);
    setError(null);
    
    try {
      const res = await axios.post(`/api/quota-test/run-single/${type}`);
      // 更新或添加结果
      setResults(prev => {
        const index = prev.findIndex(r => r.test_type === type);
        if (index >= 0) {
          const newResults = [...prev];
          newResults[index] = res.data;
          return newResults;
        }
        return [...prev, res.data];
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || `${type} 测试失败`);
    } finally {
      setRunningSingle(null);
    }
  };

  // 保存实际 token 消耗
  const saveActualTokens = async () => {
    try {
      await axios.post("/api/quota-test/save-history", {
        results,
        actual_tokens: Object.fromEntries(
          Object.entries(actualTokens).map(([k, v]) => [k, parseFloat(v) || 0])
        ),
      });
      alert("保存成功！");
      loadHistory();
    } catch (err: any) {
      alert("保存失败：" + (err.response?.data?.detail || err.message));
    }
  };

  // 格式化文件大小
  const formatSize = (bytes?: number) => {
    if (!bytes) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // 格式化时长
  const formatDuration = (seconds?: number) => {
    if (!seconds) return "-";
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  return (
    <div style={{ padding: "20px", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "20px" }}>🧪 MiniMax API 额度测试</h1>
      
      <div style={{ 
        background: "#f5f5f5", 
        padding: "15px", 
        borderRadius: "8px",
        marginBottom: "20px"
      }}>
        <p style={{ margin: 0, color: "#666" }}>
          测试各种 MiniMax API 的实际消耗，生成结果会保存到 works/ 目录。
          测试完成后，你可以在下方输入实际的 token 消耗量，便于后续参考。
        </p>
      </div>

      {/* 操作按钮 */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
        <button
          onClick={runAllTests}
          disabled={loading}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            background: loading ? "#ccc" : "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "⏳ 测试中..." : "🚀 运行所有测试"}
        </button>
        
        {TEST_TYPES.map(type => (
          <button
            key={type.key}
            onClick={() => runSingleTest(type.key)}
            disabled={runningSingle === type.key}
            style={{
              padding: "8px 16px",
              background: runningSingle === type.key ? "#ccc" : type.color,
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: runningSingle === type.key ? "not-allowed" : "pointer",
            }}
          >
            {runningSingle === type.key ? "⏳" : type.label}
          </button>
        ))}
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{
          background: "#ffebee",
          color: "#c62828",
          padding: "12px",
          borderRadius: "6px",
          marginBottom: "20px"
        }}>
          ❌ {error}
        </div>
      )}

      {/* 测试结果 */}
      {results.length > 0 && (
        <div style={{ marginBottom: "30px" }}>
          <h2>📊 测试结果</h2>
          
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f0f0f0" }}>
                <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #ddd" }}>类型</th>
                <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #ddd" }}>模型</th>
                <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #ddd" }}>状态</th>
                <th style={{ padding: "12px", textAlign: "right", borderBottom: "2px solid #ddd" }}>文件大小</th>
                <th style={{ padding: "12px", textAlign: "right", borderBottom: "2px solid #ddd" }}>耗时</th>
                <th style={{ padding: "12px", textAlign: "right", borderBottom: "2px solid #ddd" }}>实际 Token 消耗</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result, index) => (
                <tr key={index} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "12px" }}>
                    {TEST_TYPES.find(t => t.key === result.test_type)?.label || result.test_type}
                  </td>
                  <td style={{ padding: "12px", fontFamily: "monospace" }}>
                    {result.model}
                  </td>
                  <td style={{ padding: "12px" }}>
                    {result.status === "success" ? (
                      <span style={{ color: "#4CAF50" }}>✅ 成功</span>
                    ) : (
                      <span style={{ color: "#f44336" }} title={result.error_message}>
                        ❌ 失败
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "12px", textAlign: "right" }}>
                    {formatSize(result.file_size_bytes)}
                  </td>
                  <td style={{ padding: "12px", textAlign: "right" }}>
                    {formatDuration(result.duration_seconds)}
                  </td>
                  <td style={{ padding: "12px", textAlign: "right" }}>
                    <input
                      type="number"
                      value={actualTokens[result.test_type] || ""}
                      onChange={(e) => setActualTokens(prev => ({
                        ...prev,
                        [result.test_type]: e.target.value
                      }))}
                      placeholder="输入 token 数"
                      style={{
                        width: "120px",
                        padding: "6px",
                        border: "1px solid #ddd",
                        borderRadius: "4px",
                        textAlign: "right"
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* 文件预览 */}
          <div style={{ marginTop: "20px" }}>
            <h3>📁 生成的文件</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
              {results.filter(r => r.file_path).map((result, index) => (
                <div key={index} style={{
                  border: "1px solid #ddd",
                  borderRadius: "6px",
                  padding: "10px",
                  background: "#fafafa"
                }}>
                  <div style={{ fontWeight: "bold", marginBottom: "5px" }}>
                    {TEST_TYPES.find(t => t.key === result.test_type)?.label}
                  </div>
                  {result.test_type === "image" ? (
                    <img
                      src={`/files/${result.file_path}`}
                      alt="Generated"
                      style={{ maxWidth: "200px", maxHeight: "150px", borderRadius: "4px" }}
                    />
                  ) : result.test_type === "music" || result.test_type === "tts" ? (
                    <audio controls src={`/files/${result.file_path}`} style={{ width: "250px" }} />
                  ) : null}
                  <div style={{ fontSize: "12px", color: "#666", marginTop: "5px" }}>
                    {result.file_path}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 保存按钮 */}
          <div style={{ marginTop: "20px", textAlign: "right" }}>
            <button
              onClick={saveActualTokens}
              style={{
                padding: "10px 20px",
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              💾 保存实际 Token 消耗
            </button>
          </div>
        </div>
      )}

      {/* 历史记录 */}
      {history.tests.length > 0 && (
        <div style={{ marginTop: "40px" }}>
          <h2>📜 历史测试记录</h2>
          
          {history.tests.slice().reverse().map((record, index) => (
            <div key={index} style={{
              border: "1px solid #ddd",
              borderRadius: "8px",
              padding: "15px",
              marginBottom: "15px",
              background: "#fafafa"
            }}>
              <div style={{ 
                display: "flex", 
                justifyContent: "space-between",
                marginBottom: "10px",
                color: "#666"
              }}>
                <span>🕐 {new Date(record.saved_at).toLocaleString()}</span>
                <span>
                  成功: {record.results.filter(r => r.status === "success").length}/{record.results.length}
                </span>
              </div>
              
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
                <thead>
                  <tr style={{ background: "#f0f0f0" }}>
                    <th style={{ padding: "8px", textAlign: "left" }}>类型</th>
                    <th style={{ padding: "8px", textAlign: "left" }}>模型</th>
                    <th style={{ padding: "8px", textAlign: "right" }}>文件大小</th>
                    <th style={{ padding: "8px", textAlign: "right" }}>耗时</th>
                    {record.actual_tokens && (
                      <th style={{ padding: "8px", textAlign: "right" }}>实际 Token</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {record.results.map((result, rIndex) => (
                    <tr key={rIndex} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "8px" }}>
                        {TEST_TYPES.find(t => t.key === result.test_type)?.label}
                      </td>
                      <td style={{ padding: "8px", fontFamily: "monospace" }}>
                        {result.model}
                      </td>
                      <td style={{ padding: "8px", textAlign: "right" }}>
                        {formatSize(result.file_size_bytes)}
                      </td>
                      <td style={{ padding: "8px", textAlign: "right" }}>
                        {formatDuration(result.duration_seconds)}
                      </td>
                      {record.actual_tokens && (
                        <td style={{ padding: "8px", textAlign: "right" }}>
                          {record.actual_tokens[result.test_type] ?? "-"}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* 说明 */}
      <div style={{ 
        marginTop: "40px", 
        padding: "20px",
        background: "#fff3e0",
        borderRadius: "8px",
        borderLeft: "4px solid #FF9800"
      }}>
        <h3 style={{ margin: "0 0 10px 0" }}>📝 说明</h3>
        <ul style={{ margin: 0, paddingLeft: "20px" }}>
          <li>图片生成 (image-01) 和音乐生成 (music-2.6) 从 Token Plan 总余额扣费</li>
          <li>视频生成 (Hailuo) 有独立的按次额度池</li>
          <li>语音合成 (speech-02) 和文本生成 (M2.7) 也从 Token Plan 扣费</li>
          <li>登录 <a href="https://platform.minimaxi.com" target="_blank">MiniMax 控制台</a> 查看实际 token 消耗</li>
          <li>输入实际 token 消耗后点击"保存"，便于后续参考对比</li>
        </ul>
      </div>
    </div>
  );
}
