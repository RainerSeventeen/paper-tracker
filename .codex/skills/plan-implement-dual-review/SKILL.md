---
name: plan-implement-dual-review
description: 当用户提供项目计划文件并希望按计划落地代码时使用。该技能用于主agent编排两个subagent：subagent1读取计划并在新分支实现代码、随后依据 .ai_docs/rules/code_rules.md 自审并直接修复；subagent2再依据 .ai_docs/rules/code_review_structure_rules.md 做结构性审查并上报问题；主agent最终仅向用户汇报第三步的结构性问题。
---

# Plan Implement Dual Review

## Overview

将“按计划实现代码 + 规则自修复 + 结构性复审 + 主线程最小汇报”变成固定流程。
目标是让主线程只承载高价值决策信息，不重复展开实现细节。
其中：
- 撰写/实现阶段统一遵守 `.ai_docs/rules/code_rules.md`。
- 结构性审查阶段统一遵守 `.ai_docs/rules/code_review_structure_rules.md`。

## Required Inputs

在开始前收集并确认：
- 计划文件路径（用户提供）
- 是否允许创建并切换新分支（默认允许）
- 验证方式（优先执行计划中要求的测试；若未定义，执行项目默认测试）

若计划缺失关键约束，先补最少问题；其余采用显式假设并继续。

## Workflow

### Step 1: Subagent1 implement plan on a new branch

创建 `subagent1` 并分配唯一职责：按计划实现。

对 `subagent1` 的明确要求：
- 完整阅读计划文件，不得只读摘要
- 开始实现前先阅读 `.ai_docs/rules/code_rules.md`，并在整个实现阶段持续遵守
- 基于计划创建新分支并实现代码改动
- 分支命名优先遵循计划内约定；若计划未给出，使用 `codex/<feature-summary>`
- 在实现过程中记录：改动文件、关键设计决策、测试结果

可直接复用的指令模板：

```text
你负责按计划落地实现，不做结构性审查。请完成：
1) 读取计划文件：<PLAN_PATH>
2) 阅读并严格遵守 .ai_docs/rules/code_rules.md
3) 创建并切换新分支（遵循计划命名；无命名时用需要遵守 .ai_docs/rules/git_rules.md）
4) 按计划完成代码修改并执行必要测试
5) 输出：分支名、变更文件列表、测试结果、剩余风险
```

### Step 2: Subagent1 self-review by code rules and fix directly

在 Step 1 完成后，继续让 `subagent1` 执行规则自审并直接修复问题。

对 `subagent1` 的明确要求：
- 读取并严格遵守 `.ai_docs/rules/code_rules.md`
- 逐项检查刚完成的改动，发现问题直接修复，不进入上报
- 修复后重新执行受影响测试
- 输出：自审发现项、对应修复、最终测试结果

可直接复用的指令模板：

```text
继续处理你刚才的改动：
1) 阅读 .ai_docs/rules/code_rules.md
2) 按规则审查你的所有改动
3) 有问题直接修正并重新测试
4) 输出：发现的问题与修复清单、最终测试结果
```

### Step 3: Subagent2 perform structural review and report

创建 `subagent2`，只做结构性审查，不直接改代码。

对 `subagent2` 的明确要求：
- 阅读 `.ai_docs/rules/code_review_structure_rules.md`
- 审查范围仅限当前分支改动
- 仅输出“结构性问题”与证据，不输出风格性建议
- 每条问题包含：严重级别、文件路径、问题描述、影响、建议方向

可直接复用的指令模板：

```text
你只做结构性审查，不要修改代码：
1) 阅读 .ai_docs/rules/code_review_structure_rules.md
2) 仅审查当前分支改动的结构性问题
3) 输出问题清单：severity/file/issue/impact/suggestion
4) 若无结构性问题，明确输出“无结构性问题”
```

### Step 4: Main agent report only structural issues

主agent只向用户汇报 Step 3 的结果。

必须遵守：
- 仅汇报结构性问题清单（或“无结构性问题”）
- 不展开 Step 1/2 的实现过程细节
- 不追加与结构无关的建议

## Output Contract

主线程固定输出：

1. `结构性问题`：按严重级别排序（高 -> 中 -> 低）
2. `结论`：
   - 有问题：`请你拍板是否先修复以上结构性问题再继续。`
   - 无问题：`本轮结构性审查通过。`

## Standard Reply Template

在主线程汇报时，直接套用以下模板之一。

### Template A: 有结构性问题

```markdown
结构性问题
1. [高|中|低] <问题标题>
   - 文件: `<absolute-or-workspace-path>:<line>`
   - 问题: <结构性问题描述>
   - 影响: <可能导致的行为/维护风险>
   - 建议方向: <修复方向，不展开实现细节>

2. [高|中|低] <问题标题>
   - 文件: `<absolute-or-workspace-path>:<line>`
   - 问题: <结构性问题描述>
   - 影响: <可能导致的行为/维护风险>
   - 建议方向: <修复方向，不展开实现细节>

结论
请你拍板是否先修复以上结构性问题再继续。
```

### Template B: 无结构性问题

```markdown
结构性问题
无结构性问题。

结论
本轮结构性审查通过。
```

## Guardrails

- Step 1 的实现必须以 `.ai_docs/rules/code_rules.md` 为编码准绳，不能跳过。
- Step 2 必须由 `subagent1` 执行且“发现即修复”，不能跳过。
- Step 3 必须以 `.ai_docs/rules/code_review_structure_rules.md` 为审查准绳，且由独立的 `subagent2` 执行，不能复用 `subagent1` 结论替代。
- 主agent最终输出不得混入实现细节、风格性意见、或非结构问题。
- 若 Step 3 证据不足，标记为“待确认”，不得伪造确定性结论。
