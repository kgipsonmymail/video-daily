# 批量图生图（I2I Matrix）SOP

> 本文档描述如何使用批量图生图功能：从一张参考图出发，用多套提示词生成多张变体图，并保存配置以便回顾历史批次任务。

---

## 前置条件

1. `.env` 已配置 `MINIMAX_API_KEY`
2. 后端服务已启动：`uvicorn backend.main:app --host 0.0.0.0 --port 8000`
3. 前端已启动：`cd frontend && npm run dev`（端口 5173）

---

## 方式一：Web 界面操作

### Step 1 — 打开页面

访问 `http://localhost:5173/matrix`，点击顶部 tab 切换到 **`image-i2i`**。

### Step 2 — 输入参考图

**方式 A：上传新图**
点击「上传参考图」按钮，选择本地图片，图片将保存到 `works/uploads/` 目录。

**方式 B：从历史图库选择**
点击「从图库选择」，在弹出浮层中搜索或浏览已有图片资产，点击选中后参考图路径自动填入。

### Step 3 — 配置主体和风格

与 T2I 矩阵相同，在左侧编辑区填写：

- **主体列表**（每行一个，如）：
  ```
  A cozy cabin in a forest clearing
  A mountain village at sunrise
  An ancient stone bridge over a river
  ```

- **风格列表**（每行一个，如）：
  ```
  Fantasy art, vibrant colors, dramatic lighting
  Soft watercolor painting, pastel tones
  Classical oil painting, rich texture
  ```

**行列数**由主体数量 × 风格数量决定（如上例为 3×3=9 张图）。

### Step 4 — 保存配置（可选）

点击「💾 保存配置」，配置将存入数据库，可在下次从历史记录中加载。

配置字段：

| 字段 | 说明 |
|------|------|
| `name` | 配置名称 |
| `category` | `i2i`（自动） |
| `reference_image` | 参考图路径 |
| `subjects_text` | 主体提示词列表 |
| `styles_text` | 风格提示词列表 |
| `rows_count` | 主体数量 |
| `cols_count` | 风格数量 |

### Step 5 — 生成

点击「🚀 生成全部 N 张」，前端按矩阵顺序依次调用 `/api/generate/image`（每次传入参考图 base64），后端以 `subject_reference` 参数调用 MiniMax I2I API。

进度条实时更新，完成后可点击任意格子查看大图。

### Step 6 — 导出 / 导入

- **导出 JSON**：点击「📋 导出 JSON」，下载包含参考图路径的完整配置
- **导入 JSON**：点击「📂 导入 JSON」，选择之前导出的配置文件，自动回填所有字段和参考图预览

---

## 方式二：Claude Code 后台生成

适用于需要自动化或批量生成的场景。

### 直接用 Python 执行

```python
import base64, pathlib, requests
from tools.image_tasks import submit_i2i_matrix_batch  # 后端提供

# 准备参考图（转 base64）
ref_path = pathlib.Path("works/2026-05-01/assets/images/t2i/ref.png")
with open(ref_path, "rb") as f:
    ref_b64 = base64.b64encode(f.read()).decode()
reference = f"data:image/png;base64,{ref_b64}"

# 提交批量任务
result = submit_i2i_matrix_batch(
    reference_image=reference,
    subjects=[
        "A cozy cabin in a forest clearing",
        "A mountain village at sunrise",
        "An ancient stone bridge over a river",
    ],
    styles=[
        "Fantasy art, vibrant colors, dramatic lighting",
        "Soft watercolor painting, pastel tones",
        "Classical oil painting, rich texture",
    ],
    name="my-i2i-batch",
    model="image-01",
    theme="rv-themed",
)

print(f"已提交 {result['total']} 个任务，config_id={result['config_id']}")
```

### 轮询状态

```python
import time, requests

config_id = result["config_id"]
while True:
    r = requests.get(f"http://localhost:8000/api/matrix/configs/{config_id}/assets")
    assets = r.json()
    done = [a for a in assets if a.get("status") == "success"]
    print(f"{len(done)}/{len(assets)} 完成")
    if len(done) == len(assets):
        break
    time.sleep(10)
```

---

## 数据模型

### `matrix_configs` 表新增字段

| 列名 | 类型 | 说明 |
|------|------|------|
| `category` | VARCHAR(16) | `t2i` 或 `i2i` |
| `reference_image` | TEXT | 参考图路径（i2i 用） |
| `rows_count` | INT | 主体数量，默认 6 |
| `cols_count` | INT | 风格数量，默认 6 |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/matrix/configs` | 列出所有矩阵配置（含 i2i） |
| POST | `/api/matrix/configs` | 创建配置（含 category/i2i 字段） |
| GET | `/api/matrix/configs/{id}/assets` | 获取该配置关联的所有资产 |
| DELETE | `/api/matrix/configs/{id}` | 删除配置 |
| POST | `/api/generate/image` | 生成图片（支持 `reference_image` 参数） |
| GET | `/api/assets/picker` | 图片选择器（支持搜索） |
| POST | `/api/generate/upload` | 上传参考图，返回路径 |

---

## 文件变更清单

```
backend/
├── schemas.py          # MatrixConfigCreate/Response 新增字段
├── routers/
│   ├── matrix.py       # create/list/config-assets 新增字段写入
│   ├── generate.py     # /image 支持 reference_image + subject_reference
│   └── assets.py       # 新增 /picker 端点
frontend/src/
├── api/
│   ├── matrix.ts       # 类型更新 + createConfig 参数扩展
│   ├── assets.ts       # 新增 picker 方法
│   └── generate.ts     # image() 参数扩展
└── pages/
    └── MatrixPage.tsx   # 新增 image-i2i tab（含参考图输入+图片选择器浮层）
tools/
└── image_tasks.py       # 可选：submit_i2i_matrix_batch 后台批量函数
docs/
└── i2i-matrix-sop.md   # 本文档
```