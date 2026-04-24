# 代码规范

## Python 代码规范

1. 使用 type hints
2. 类名大驼峰，函数/变量小写下划线
3. docstring 使用三引号简洁描述
4. 相对导入，src/ 内模块互相引用

## 配置规范

- API Key 不硬编码，使用环境变量或 .env
- 路径使用 Path 对象
- 敏感配置与代码分离

## 命名规则

| 类型 | 规则 | 示例 |
|------|------|------|
| 类 | 大驼峰 | `MiniMaxClient` |
| 函数/变量 | 小写下划线 | `create_video_task` |
| 常量 | 全大写下划线 | `API_BASE_URL` |
| 配置文件 | 小写下划线 | `config.py` |