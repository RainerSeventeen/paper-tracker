# 环境变量配置

本文档说明 PaperTracker 中使用的环境变量及其配置方法。

## 概述

PaperTracker 使用环境变量来存储敏感信息（如 API 密钥），避免将这些信息硬编码到配置文件或代码中。

项目使用 [python-dotenv](https://github.com/theskumar/python-dotenv) 库来自动加载 `.env` 文件中的环境变量。

## 配置步骤

### 1. 创建 .env 文件

首次使用时，需要从示例文件创建 `.env` 文件：

```bash
cp .env.example .env
```

### 2. 编辑 .env 文件

在 `.env` 文件中填入你的 API 密钥：

```bash
# .env 文件内容示例
LLM_API_KEY=sk-your-actual-api-key-here
```

**重要提示**：
- `.env` 文件包含敏感信息，已被添加到 `.gitignore` 中，**不会**被提交到 Git 仓库
- 请妥善保管你的 API 密钥，不要分享或公开

### 3. 运行程序

配置好 `.env` 文件后，正常运行程序即可：

```bash
paper-tracker --config config/default.yml search
```

程序启动时会自动加载 `.env` 文件中的环境变量。

## 支持的环境变量

### LLM_API_KEY

**用途**：LLM 服务的 API 密钥

**必需性**：当 `llm.enabled: true` 时必需（`config/default.yml` 默认启用）

**说明**：
- 适用于所有 OpenAI 兼容的 API 提供商（OpenAI、DeepSeek、SiliconFlow 等）
- 具体使用哪个提供商由配置文件中的 `llm.base_url` 决定
- 环境变量名称可以在配置文件中通过 `llm.api_key_env` 自定义（默认为 `LLM_API_KEY`）

**获取方式**：

- **OpenAI**: https://platform.openai.com/api-keys
- **DeepSeek**: https://platform.deepseek.com/api_keys
- **SiliconFlow**: https://cloud.siliconflow.cn/account/ak

**示例**：
```bash
# OpenAI
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx

# DeepSeek
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# SiliconFlow
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

## 环境变量加载机制

### 加载顺序

`python-dotenv` 按以下优先级加载环境变量：

1. **已存在的环境变量**（Shell 中已设置的）- 优先级最高
2. **`.env` 文件中的变量**
3. **代码中的默认值**

这意味着：
- 如果你在 Shell 中已经设置了 `LLM_API_KEY`，`.env` 文件中的同名变量会被忽略
- 你可以临时在命令行中覆盖 `.env` 中的设置：
  ```bash
  LLM_API_KEY=sk-temporary-key paper-tracker search
  ```

### 加载时机

环境变量在 CLI 入口处（`src/PaperTracker/cli/ui.py:cli()`）被加载，在配置文件解析之前完成。

这确保了配置文件中引用的环境变量（如 `llm.api_key_env`）能够正确读取。

## 自定义环境变量名

如果你需要使用不同的环境变量名（例如同时管理多个项目），可以在配置文件中修改：

```yaml
llm:
  enabled: true
  api_key_env: MY_CUSTOM_API_KEY  # 自定义环境变量名
  # ... 其他配置
```

然后在 `.env` 文件中使用对应的变量名：

```bash
MY_CUSTOM_API_KEY=sk-your-api-key
```

## 最佳实践

### 1. 不要提交 .env 文件

`.env` 文件已在 `.gitignore` 中，确保不要将其提交到版本控制系统。

### 2. 保持 .env.example 更新

当添加新的环境变量时，记得更新 `.env.example` 文件（使用占位符值），方便其他开发者了解需要哪些配置。

### 3. 使用不同环境的 .env 文件

对于不同的环境（开发、测试、生产），可以使用不同的 `.env` 文件：

```bash
.env              # 默认（开发环境）
.env.test         # 测试环境
.env.production   # 生产环境
```

然后在运行时指定：

```bash
# 手动加载测试环境配置
export $(cat .env.test | xargs)
paper-tracker search
```

### 4. 定期轮换 API 密钥

为了安全起见，建议定期更换 API 密钥，特别是当密钥可能泄露时。

## 故障排查

### 错误："LLM_API_KEY environment variable not set"

**原因**：启用了 LLM 功能但未设置 API 密钥

**解决方法**：
1. 确认 `.env` 文件存在且包含 `LLM_API_KEY`
2. 检查 `.env` 文件权限（应该可读）
3. 验证环境变量名与配置文件中 `llm.api_key_env` 一致

### 无法读取 .env 文件

**检查项**：
1. 确认 `.env` 文件位于项目根目录
2. 确认文件编码为 UTF-8
3. 确认文件格式正确（`KEY=value`，每行一个变量）
4. 确认没有使用引号包裹值（除非引号是值的一部分）

### 环境变量未生效

如果 `.env` 文件中的变量似乎没有被加载：

1. 检查是否有同名的 Shell 环境变量（优先级更高）：
   ```bash
   echo $LLM_API_KEY
   ```

2. 验证 `python-dotenv` 已安装：
   ```bash
   python -m pip show python-dotenv
   ```

3. 检查是否有语法错误（例如等号前后的空格）：
   ```bash
   # 错误
   LLM_API_KEY = sk-xxxxx

   # 正确
   LLM_API_KEY=sk-xxxxx
   ```

## 相关文档

- [配置文件说明](configuration.md)
- [python-dotenv 官方文档](https://github.com/theskumar/python-dotenv)
