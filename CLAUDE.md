# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paper Tracker 是一个从零重构的最小化论文追踪工具,核心功能是根据关键词查询 arXiv API 并输出论文列表。

## 开发命令

### 安装
```bash
python -m pip install -e .
```

推荐使用虚拟环境(项目使用 `.venv/`)。

### 环境变量配置
```bash
cp .env.example .env
# 编辑 .env 文件，填入 API 密钥等敏感信息
```

详细说明参考 `docs/environment-variables.md`。

### 运行
```bash
paper-tracker --config config/default.yml search
```

配置文件为 YAML 格式,参考 `config/default.yml`。

### 测试
```bash
python -m unittest discover -s test -p "test_*.py"
```

测试配置文件位于 `config/test/`,测试脚本位于 `test/`。

## 说明文档

- 如果你的工作涉及到了下面的模块, 可以阅读以下文档

### 规则索引（按路径导入）

- 项目架构与调用链: `.ai_docs/rules/project_overview.md`
- 编码与实现规范（唯一编码规则来源）: `.ai_docs/rules/code_rules.md`
- 测试策略与测试范围: `.ai_docs/rules/testing_rules.md`
- 代码结构审查流程与分级标准: `.ai_docs/rules/code_review_structure_rules.md`
- Git 沟通与 PR 摘要格式: `.ai_docs/rules/git_rules.md`

### 撰写新功能

- 注意: 当前位于开发阶段, 不用保留前向兼容性, 保证代码逻辑最优即可
- 撰写新功能, 或者代码时, 阅读 `.ai_docs/rules/code_rules.md`, 遵守其中的约定
- 涉及测试设计与是否补测时, 阅读 `.ai_docs/rules/testing_rules.md`

### 代码评审

- 做结构性评审时, 阅读 `.ai_docs/rules/code_review_structure_rules.md`
- 评审中的编码细则统一以 `.ai_docs/rules/code_rules.md` 为准

### git 操作

- 撰写 commit, 提 pr 等操作, 阅读 `.ai_docs/rules/git_rules.md`

### 文档工作

- 项目文档位于 `docs/` 下方, 当前阶段不撰写英文文档, 只考虑在 `docs/` 下写中文文档, 不考虑写到 `docs/en` 下