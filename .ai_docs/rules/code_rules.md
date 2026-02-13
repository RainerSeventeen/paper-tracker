# Paper Tracker 代码规范（唯一编码规则来源）

## 1. 设计原则

### 1.1 职责分离
- CLI 层保持薄：仅做参数入口、调用 runner/command。
- 业务编排在 command/service，I/O 在 source/storage/renderer。
- 输出格式逻辑不得侵入服务层。

### 1.2 组合与扩展
- 优先依赖注入，避免隐式全局状态。
- 通过协议/工厂扩展能力，避免在核心流程堆叠 if/else。
- 保持模块内聚，避免循环依赖。

### 1.3 配置驱动
- 新行为应可由配置控制，并提供安全默认值。
- 配置解析集中在 `config/`，禁止在业务层散落读取 YAML/ENV。

### 1.4 可靠性与可测试性
- 资源生命周期可控（创建/释放路径明确）。
- 核心逻辑可替换、可注入、可测试。

## 2. 编写规则

### 2.1 导入规范
- 必须使用绝对导入：`from PaperTracker.xxx import y`。
- 禁止相对导入。

### 2.2 模块头与导入顺序
- 除 `__init__.py` 外，`*.py` 文件应以模块 docstring 开头（说明模块职责）。
- `__init__.py` 不强制模块 docstring。
- `from __future__ import annotations` 必须放在模块 docstring 之后。
- 导入顺序统一为：
  - `from __future__ import annotations`
  - 标准库
  - 第三方库
  - 本地模块

### 2.3 Docstring 规则
- 公共接口（对外可调用的函数/方法/类）必须有 docstring。
- 复杂逻辑函数（存在关键分支、状态转换、非直观约束）必须有 docstring。
- 简单工具函数可简化 docstring；如语义已足够直观，可不强制完整 Google 风格。
- 文档注释统一使用英文。

### 2.4 函数与方法组织
- 模块内顺序：公共接口 -> 模块内协作函数 -> `_` 前缀工具函数。
- 类内顺序：公共接口方法在前，内部辅助方法在后。

### 2.5 CLI 约束
- CLI 仅接受 `--config` 参数；其余行为通过 YAML 配置控制。

### 2.6 Git 沟通
- commit、PR、review 等 Git 沟通统一使用英文。
