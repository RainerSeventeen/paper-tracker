# Paper Tracker

- 原始项目仓库：https://github.com/colorfulandcjy0806/Arxiv-tracker

本仓库从零重新整理，仅保留核心功能与配置，来源如下：

## 核心功能（当前已实现）

- 根据关键词（可选分类/排除词）调用 arXiv API 抓取论文列表
- 在命令行输出（支持 `text` / `json`）

### 快速开始

安装（推荐用虚拟环境）：
```bash
python -m pip install -e .
```
准备配置文件（参考 `config/default.yml`），然后运行：

- `paper-tracker --config config/default.yml search`

配置文件写法与字段说明见：`docs/configuration.md`

测试说明见：`docs/testing.md`

## 来源与说明

本项目基于原仓库改造与裁剪，功能与实现细节参考原项目

为避免 Git 仓库冗余，这里只保留必要内容并重新组织结构

## 版权与许可

本仓库 **继承原仓库的版权与许可**, 使用 MIT 开源协议，详见 [LICENSE](./LICENSE)
