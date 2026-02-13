---
name: feat-plan-challenge
description: 当用户给出一个 feat 并希望通过多 agent 产出高质量实现计划时使用。该技能用于主 agent 编排两个 subagent：先由 subagent1 读取本技能附属规划规则文件生成计划，再由 subagent2 对计划进行挑战审查，最后由 subagent1评估是否合并建议；主 agent 只向用户汇报冲突点、无法自动决策点和需要用户拍板的选项。
---

# Feat Plan Challenge

## Overview

将“计划生成 + 对抗式审查 + 回合式合并 + 冲突上报”变成固定流程。
默认目标是降低一次成稿风险，不在主对话里铺陈完整计划正文，只上报关键分歧。

必读附属文件：
- `references/plan_feature_requirements.md`：Step 1 生成计划时的本地规则来源。

## Workflow

### Step 0: Clarify feat input

读取用户提供的 feat 描述，并提炼以下输入：
- Feature 目标与边界
- 非功能性约束（性能、兼容性、时限）
- 已知技术限制（依赖、目录、禁用方案）

若关键信息缺失，先补充最少问题；若可合理假设，则记录假设并继续。

### Step 1: Subagent1 generate plan via local requirements

创建 `subagent1`，明确其职责：
- 读取 `references/plan_feature_requirements.md`，按其中规则生成完整实现计划
- 输出初稿计划文档路径与摘要（不在主线程展开全文）
- 标注关键设计决策及备选方案

对 `subagent1` 的要求：
- 严格遵守项目规则文档
- 计划结构完整（需求、设计、实施、测试、验收）
- 任何假设必须显式记录

### Step 2: Subagent2 challenge the plan

创建 `subagent2`，对 Step 1 计划执行“挑战式审查”：
- 查找逻辑漏洞、缺失场景、过度设计、实现顺序风险
- 给出替代方案与代价比较
- 逐条产出修改建议，标注优先级（高/中/低）

对 `subagent2` 的要求：
- 不重复改写整份计划，仅输出 challenge 清单
- 每条建议必须有“理由 + 影响范围”

### Step 3: Subagent1 reconcile suggestions

将 Step 2 的建议回传给 `subagent1` 进行合并决策：
- `accept`: 明确合并并更新计划
- `reject`: 明确拒绝并说明理由
- `escalate`: 无法判定或两案均可，升级给主 agent

合并结果要求：
- 输出“已合并建议列表”
- 输出“已拒绝建议列表（含理由）”
- 输出“待用户决策列表”

### Step 4: Main agent report only decision points

主 agent 面向用户只输出：
- 冲突点（建议与原计划的不可兼容点）
- 待决策点（subagent1 标记 `escalate` 的事项）
- 每个待决策点的可选项与影响

主 agent 不输出：
- 完整计划正文（用户自行阅读文档）
- 冗长背景解释

## Output Contract

最终主线程响应使用固定结构：

1. `计划文档`：路径 + 一句话状态（已更新/待更新）
2. `冲突点`：按严重级别排序（高 -> 中 -> 低）
3. `待你决策`：每项包含
   - 决策问题
   - 选项 A/B（或更多）
   - 各选项代价与收益
   - 默认建议选项（若存在）

若无冲突且无待决策点，明确写：
- `无需你拍板，计划已完成合并。`

## Main Agent Reply Template

主 agent 对用户回复时，使用以下固定模板。

### Case A: 有冲突或有待决策

```markdown
计划文档：
- 路径：<plan_path>
- 状态：<已更新/待更新>（<一句话说明>）

冲突点：
1. [高|中|低] <冲突标题>
- 背景：<一句话背景>
- 冲突内容：<不可兼容点>
- 影响：<范围/风险>
- 当前建议：<推荐处理方式>

待你决策：
1. <决策问题>
- 选项 A：<方案>（代价：<...>；收益：<...>）
- 选项 B：<方案>（代价：<...>；收益：<...>）
- 建议选择：<A/B/暂不建议>
- 原因：<1-2 句>
```

### Case B: 无冲突且无需决策

```markdown
计划文档：
- 路径：<plan_path>
- 状态：已更新（挑战建议已完成合并）

无需你拍板，计划已完成合并。
```

### Formatting Rules

- 只保留与决策相关的信息，不展开完整计划正文。
- `冲突点` 与 `待你决策` 按优先级排序。
- 每条决策项必须包含“选项、代价、收益、建议选择”四个字段。
- 若某项信息未知，写 `待补充`，不要省略字段。

## Guardrails

- 不跳过 Step 2，必须有独立挑战过程。
- 不让 subagent2 直接改主计划正文。
- Step 3 若出现“证据不足”或“取舍依赖业务偏好”，必须升级给用户。
- 始终保留决策溯源：每条 challenge 建议要能回溯到处理结论（accept/reject/escalate）。
- Step 1 必须优先使用本技能内的 `references/plan_feature_requirements.md`，不要改为依赖外部规划技能。

## Example Trigger Phrases

- “我给你一个 feat，你走一轮计划+挑战+合并流程”
- “先用一个 agent 出计划，再用另一个 agent 挑战它”
- “只把需要我拍板的点告诉我，计划正文我自己看”
