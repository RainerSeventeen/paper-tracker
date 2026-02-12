# Plan Feature Requirements (Local Reference)

此文件定义 Step 1 中 `subagent1` 的计划生成规则。  
目标：在不依赖外部规划技能的前提下，稳定产出一致的 feature 实施计划。

## 1. 输入提炼

先提炼以下信息：
- 核心功能：功能目的、用户价值、主要使用方式
- 架构影响：影响的层次（CLI/Config/Core/Data Source 等）、新增依赖、接口变更
- 约束条件：性能、兼容性、时限、禁用方案

若信息不足：
- 优先提出最少且关键的问题
- 或在可接受前提下做合理假设，并显式记录假设

## 2. 分支命名规则

生成计划分支名：`<type>/<feature_name>`

- `type` 可选：`feat` `fix` `refactor` `perf` `test` `docs` `build` `ci` `chore`
- `feature_name` 使用小写下划线，2-4 个词，语义清晰
- 示例：`feat/csv_export`、`refactor/llm_layer`
- 仅在计划文档中记录，不创建或切换分支

## 3. 计划文档路径与命名

- 文档路径：`.ai_docs/plan/current/<feature_name>.md`
- `<feature_name>` 与分支名后缀一致
- 示例：`.ai_docs/plan/current/csv_export.md`

## 4. 计划文档结构（必填）

文档使用中文技术说明（代码示例可用英文），必须包含以下章节：

1. `## 概述`
- Feature Description
- User Benefits（列表）
- Project Alignment
- 计划分支名称

2. `## 需求分析`
- Functional Requirements（编号列表）
- Non-Functional Requirements
- Edge Cases
- Dependencies

3. `## 技术设计`
- Architecture Overview
- Component Breakdown（按层拆分）
- Data Flow
- Configuration Changes
- API/Interface Definitions（必要时给代码片段）

4. `## 实施策略`
- Implementation Phases（分阶段步骤）
- File Structure Changes（新增/修改文件）
- Code Locations
- Integration Points

5. `## 测试计划`
- 默认只写手工测试方案，不设计测试模块（除非用户明确要求）
- Test scenarios
- Test data and expected results

6. `## 验收标准`
- Success Metrics（checkbox）
- User Acceptance

## 5. 质量门禁（提交前自检）

完整性：
- 所有必填章节齐全
- 关键依赖、边界条件、落地步骤齐全

一致性：
- 贴合项目架构与规则文档
- 避免过度设计，保持最小可行实现路径

清晰度：
- 每个关键决策都有理由
- 语句避免歧义
- 实施顺序可执行

## 6. Step 1 输出格式

`subagent1` 在主流程中返回以下内容：
- `plan_path`: 计划文档路径
- `branch_name`: 计划分支名
- `decision_points`: 关键设计决策与备选方案
- `assumptions`: 采用的假设（若有）
- `summary`: 1-2 句摘要

不要在主线程粘贴完整计划正文。
