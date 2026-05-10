// API 配置文件
// 部署到 Netlify 时，修改这里的 API_BASE 为你的后端服务地址
// 例如: "https://your-backend.herokuapp.com/api"

window.T2S_CONFIG = {
  // 本地开发使用 localhost
  // 生产环境需要改为实际的后端API地址
  API_BASE: "http://localhost:8000/api",

  // 如果后端未部署，可以设置为 demo 模式（仅展示UI，不调用API）
  DEMO_MODE: false
};
