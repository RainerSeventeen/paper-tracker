# Paper Tracker

PaperTracker 是一个最小化论文追踪工具，核心功能是根据关键词查询 arXiv API 并输出论文列表

## 核心功能

功能尚未开发完毕......

目前支持:

- 关键词检索（支持分类、标题、作者等字段）
- 去重与可选内容的存储（SQLite）
- 多种输出格式（console/json/markdown）
- 可选 LLM 增强（翻译与结构化摘要）


## 快速开始

**1. 安装**（推荐使用虚拟环境）：
```bash
python -m pip install -e .
```

**2. 配置环境变量**（如使用 LLM）：
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

**3. 运行**：
```bash
paper-tracker --config config/default.yml search
```

更多说明见 [使用指南](./docs/zh/guide_user.md)

## 文档入口
- [使用指南](./docs/zh/guide_user.md)
- [详细参数配置说明](./guide_configuration.md)
- [arXiv 查询语法说明](./source_arxiv_api_query.md)

## 版权与许可

本仓库为独立实现，基于开源项目的功能思路进行重构
当前仓库使用 MIT 协议，详见 `LICENSE`。

本项目使用了 `libs/` 下以下 submodule 的部分功能思路:（保持原仓库许可证与版权信息）：

- `libs/Arxiv-tracker`（https://github.com/colorfulandcjy0806/Arxiv-tracker）
- `libs/daily-arXiv-ai-enhanced`（https://github.com/zhengqinjian/daily-arXiv-ai-enhanced）
