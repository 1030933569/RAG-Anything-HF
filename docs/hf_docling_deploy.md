# 使用 Docling 部署到 Hugging Face Space（Docker）

本仓库已提供可直接部署的文件：

- `Dockerfile`
- `app.py`
- `requirements-hf-docling.txt`

目标：在 HF 上使用 `docling` 作为解析器，不依赖本地 `MinerU`。

## 1. 创建 Space

1. 进入 Hugging Face，创建新 Space。
2. 选择 `Docker` SDK（不是 Gradio SDK）。
3. 将当前仓库推送到该 Space 仓库。

## 2. 配置 Secrets（必填）

在 Space Settings -> Variables and secrets 中添加：

- `LLM_BINDING_API_KEY`
- `EMBEDDING_BINDING_API_KEY`

常见可选配置：

- `LLM_BINDING_HOST`（默认 `https://api.openai.com/v1`）
- `EMBEDDING_BINDING_HOST`（默认跟随 LLM Host）
- `LLM_MODEL`（默认 `gpt-4o-mini`）
- `VISION_MODEL`（默认 `gpt-4o`）
- `EMBEDDING_MODEL`（默认 `text-embedding-3-large`）
- `EMBEDDING_DIM`（默认 `3072`）
- `PARSE_METHOD`（默认 `auto`）

## 3. 部署后使用

1. 打开 Space 页面。
2. 上传文档（PDF / Office / HTML 等）。
3. 点击“解析并入库”。
4. 输入问题并点击“查询”。

## 4. 说明与限制

- 当前 `app.py` 固定使用 `parser=\"docling\"`。
- 文档会存放在容器内 `/data` 目录（`WORKING_DIR`、`OUTPUT_DIR`）。
- 如果你使用免费 Space，数据通常不是长期持久化，重启后可能丢失。

## 5. 常见问题

1. `缺少 LLM_BINDING_API_KEY`
   - 说明未配置 Secrets，按上文补齐即可。

2. `docling command not found`
   - 说明镜像构建异常，检查 Space Build Logs，确认 `requirements-hf-docling.txt` 安装成功。

3. 首次启动慢
   - 正常现象，首次会安装依赖并初始化模型相关组件。
