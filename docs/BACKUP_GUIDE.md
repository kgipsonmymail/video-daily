# Video Daily 素材备份与合并指南

## 概述

本指南用于将 Video Daily 的历史素材备份到网盘，以及从网盘恢复后合并素材。

---

## 一、备份到网盘

### 1.1 需要备份的内容

| 内容 | 路径 | 说明 |
|------|------|------|
| 素材文件 | `works/` | 所有生成的图片、视频、音乐、语音 |
| 数据库 | MySQL `minimax-take` | 记录素材元数据、提示词、额度等 |
| 环境配置 | `.env` | API Key、数据库连接信息 |

### 1.2 备份步骤

#### 步骤 1：导出数据库

```bash
# 在服务器上执行
cd /www/wwwroot/video-daily

# 导出整个数据库（包含结构和数据）
mysqldump -h YOUR_DB_HOST \
  -u wind -p minimax-take > backup/minimax-take_$(date +%Y%m%d).sql

# 只导出结构（可选，用于参考）
mysqldump -h YOUR_DB_HOST \
  -u wind -p --no-data minimax-take > backup/schema.sql
```

#### 步骤 2：打包素材文件

```bash
# 创建备份目录
mkdir -p backup

# 打包整个 works 目录
cd /www/wwwroot/video-daily
tar czf backup/works_$(date +%Y%m%d).tar.gz works/

# 或者按类型分别打包（便于管理）
tar czf backup/works-t2i_$(date +%Y%m%d).tar.gz works/t2i/
tar czf backup/works-i2i_$(date +%Y%m%d).tar.gz works/i2i/
tar czf backup/works-t2v_$(date +%Y%m%d).tar.gz works/t2v/
tar czf backup/works-i2v_$(date +%Y%m%d).tar.gz works/i2v/
tar czf backup/works-tts_$(date +%Y%m%d).tar.gz works/tts/
tar czf backup/works-music_$(date +%Y%m%d).tar.gz works/music/
tar czf backup/works-voice-samples_$(date +%Y%m%d).tar.gz works/voice-samples/
```

#### 步骤 3：备份配置文件

```bash
cp .env backup/.env_$(date +%Y%m%d)
```

#### 步骤 4：上传到网盘

```bash
# 备份目录结构
backup/
├── minimax-take_20260527.sql    # 数据库备份
├── works_20260527.tar.gz        # 全量素材打包
├── .env_20260527                # 配置备份
└── README.md                    # 备份说明（可选）
```

将 `backup/` 目录上传到网盘即可。

### 1.3 增量备份（推荐）

如果素材量大，可以只备份新增部分：

```bash
# 备份最近 7 天的素材
find works/ -mtime -7 -type f | tar czf backup/works-recent_$(date +%Y%m%d).tar.gz -T -

# 或者按日期目录备份
tar czf backup/works-2026-05_$(date +%Y%m%d).tar.gz works/*/2026-05-*/
```

---

## 二、从网盘恢复并合并

### 2.1 恢复场景

- 场景 A：新机器部署，需要恢复全部历史素材
- 场景 B：已有部分素材，需要合并网盘上的历史素材

### 2.2 恢复步骤

#### 步骤 1：下载备份文件

从网盘下载备份文件到本地或服务器。

#### 步骤 2：恢复数据库

```bash
# 如果是新机器，先创建数据库
mysql -h <host> -u <user> -p -e "CREATE DATABASE IF NOT EXISTS minimax-take CHARACTER SET utf8mb4;"

# 恢复数据库
mysql -h <host> -u <user> -p minimax-take < backup/minimax-take_YYYYMMDD.sql
```

#### 步骤 3：恢复素材文件

```bash
cd /www/wwwroot/video-daily

# 解压全量备份
tar xzf backup/works_YYYYMMDD.tar.gz

# 或者按类型解压
tar xzf backup/works-t2i_YYYYMMDD.tar.gz
tar xzf backup/works-music_YYYYMMDD.tar.gz
# ... 以此类推
```

#### 步骤 4：合并多个备份（如果有多个时间点的备份）

```bash
# 假设有两个备份：backup-May/ 和 backup-June/
# 解压到临时目录
mkdir -p /tmp/merge
tar xzf backup-May/works_20260501.tar.gz -C /tmp/merge/
tar xzf backup-June/works_20260601.tar.gz -C /tmp/merge/

# rsync 合并（新文件覆盖旧文件，但不删除已有文件）
rsync -av /tmp/merge/works/ /www/wwwroot/video-daily/works/
```

### 2.3 合并数据库记录

如果多次备份的数据库需要合并：

```bash
# 方法 1：全量导入（覆盖）
mysql -h <host> -u <user> -p minimax-take < backup/minimax-take_latest.sql

# 方法 2：只导入新增记录（需要手动处理冲突）
# 先导出差异记录，再导入
```

### 2.4 修复文件路径（如果路径格式变了）

如果备份时的路径格式与当前代码不一致，需要更新数据库：

```sql
-- 查看当前路径分布
SELECT 
    CASE 
        WHEN file_path LIKE 'works/t2i/%' THEN 't2i'
        WHEN file_path LIKE 'works/i2i/%' THEN 'i2i'
        WHEN file_path LIKE 'works/t2v/%' THEN 't2v'
        WHEN file_path LIKE 'works/i2v/%' THEN 'i2v'
        WHEN file_path LIKE 'works/music/%' THEN 'music'
        ELSE 'other'
    END as category,
    COUNT(*)
FROM assets
GROUP BY category;

-- 修复反斜杠路径（Windows → Linux）
UPDATE assets SET file_path = REPLACE(file_path, '\\', '/');
UPDATE voice_samples SET file_path = REPLACE(file_path, '\\', '/');

-- 修复旧路径格式（如果需要）
-- 旧格式: works/YYYY-MM-DD/assets/images/t2i/...
-- 新格式: works/t2i/YYYY-MM-DD/...
UPDATE assets 
SET file_path = CONCAT(
    'works/t2i/',
    SUBSTRING(file_path, 7, 10),
    '/',
    SUBSTRING_INDEX(file_path, '/', -1)
)
WHERE file_path LIKE 'works/%/assets/images/t2i/%';
```

### 2.5 验证恢复结果

```bash
# 检查文件数量
echo "=== 素材文件统计 ==="
for dir in t2i i2i t2v i2v tts music voice-samples; do
    count=$(find works/$dir -type f 2>/dev/null | wc -l)
    echo "$dir: $count"
done

# 检查数据库记录
echo "=== 数据库记录统计 ==="
mysql -h <host> -u <user> -p minimax-take -e "
    SELECT modality, sub_type, COUNT(*) 
    FROM assets 
    GROUP BY modality, sub_type;
"

# 检查文件是否存在
echo "=== 检查文件完整性 ==="
mysql -h <host> -u <user> -p minimax-take -e "
    SELECT file_path FROM assets 
    WHERE file_path NOT LIKE 'works/%' 
    LIMIT 10;
"
```

---

## 三、目录结构参考

### 当前结构（2026-05-27 重构后）

```
works/
├── t2i/                    # 文生图
│   └── YYYY-MM-DD/
│       ├── {run_id}.png
│       └── {run_id}.prompt.txt
├── i2i/                    # 图生图
│   └── YYYY-MM-DD/
├── t2v/                    # 文生视频（含 fl2v、s2v）
│   └── YYYY-MM-DD/
├── i2v/                    # 图生视频
│   └── YYYY-MM-DD/
├── tts/                    # 文本转语音
│   └── YYYY-MM-DD/
├── music/                  # 音乐生成
│   └── YYYY-MM-DD/
│       └── matrix-{name}/  # 矩阵第四层
│           ├── config.json
│           └── r0c0.mp3
├── voice-samples/          # 音色样本
│   └── {voice_id}/
│       └── sample.mp3
└── uploads/                # 用户上传文件
```

### 旧结构（2026-05-27 之前）

```
works/
└── YYYY-MM-DD/
    ├── prompts/            # 提示词（已废弃，现与素材同目录）
    │   ├── t2i/
    │   └── music/
    └── assets/
        ├── images/
        │   ├── t2i/
        │   └── i2i/
        ├── videos/
        │   ├── t2v/
        │   └── i2v/
        └── music/

ref/api/voice/
├── samples/                # 音色样本（已迁移到 works/voice-samples/）
└── audio_studio/           # 音频工坊输出（已废弃）
```

---

## 四、注意事项

1. **数据库优先**：恢复时先恢复数据库，再恢复文件，确保路径一致
2. **路径格式**：统一使用 POSIX 正斜杠 `/`，不要用 Windows 反斜杠 `\`
3. **文件编码**：文件名可能包含中文，打包时注意编码（推荐用 `tar` 而不是 `zip`）
4. **磁盘空间**：全量打包前检查磁盘空间，预估大小：
   ```bash
   du -sh works/
   ```
5. **增量备份**：建议每月全量备份，每周增量备份
6. **备份验证**：定期验证备份文件的完整性

---

## 五、快速备份脚本

```bash
#!/bin/bash
# backup-video-daily.sh
# 用法: ./backup-video-daily.sh [备份目录]

BACKUP_DIR="${1:-/www/wwwroot/video-daily/backup}"
DATE=$(date +%Y%m%d)
PROJECT_DIR="/www/wwwroot/video-daily"

mkdir -p "$BACKUP_DIR"

echo "=== 备份数据库 ==="
mysqldump -h YOUR_DB_HOST \
  -u wind -p minimax-take > "$BACKUP_DIR/minimax-take_$DATE.sql"

echo "=== 备份素材文件 ==="
cd "$PROJECT_DIR"
tar czf "$BACKUP_DIR/works_$DATE.tar.gz" works/

echo "=== 备份配置 ==="
cp .env "$BACKUP_DIR/.env_$DATE"

echo "=== 备份完成 ==="
echo "备份目录: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*_$DATE*
```

---

## 六、快速恢复脚本

```bash
#!/bin/bash
# restore-video-daily.sh
# 用法: ./restore-video-daily.sh <备份目录>

BACKUP_DIR="$1"
PROJECT_DIR="/www/wwwroot/video-daily"

if [ -z "$BACKUP_DIR" ]; then
    echo "用法: $0 <备份目录>"
    exit 1
fi

echo "=== 恢复数据库 ==="
mysql -h YOUR_DB_HOST \
  -u wind -p minimax-take < "$BACKUP_DIR/minimax-take_"*.sql

echo "=== 恢复素材文件 ==="
cd "$PROJECT_DIR"
tar xzf "$BACKUP_DIR/works_"*.tar.gz

echo "=== 恢复完成 ==="
echo "请检查: ls -la works/"
```
