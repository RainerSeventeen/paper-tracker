# Pipeline 测试脚本

这个目录包含独立的测试脚本，用于测试 Paper Tracker 的输出管道功能。

## 测试脚本说明

### test_output_standalone.py

**功能：** 测试所有输出格式的基本功能

**包含的测试：**
1. Console 输出测试
2. JSON 文件输出测试
3. Markdown 文件输出测试
4. HTML 文件输出测试
5. 多种格式同时输出测试

**运行方式：**
```bash
python test/pipeline/test_output_standalone.py
```

**输出位置：**
- `output/test/json/` - JSON 文件
- `output/test/markdown/` - Markdown 文件
- `output/test/html/` - HTML 文件
- 控制台 - Console 输出

### test_json_reload.py

**功能：** 从 JSON 文件重新加载数据并输出到其他格式

**测试流程：**
1. 从指定或自动查找最新的 JSON 文件
2. 加载并验证 JSON 数据
3. 重新输出到所有格式（Console、Markdown、HTML）

**运行方式：**
```bash
# 先生成测试数据
python test/pipeline/test_output_standalone.py

# 使用最新的 JSON 文件（自动查找）
python test/pipeline/test_json_reload.py

# 指定具体的 JSON 文件
python test/pipeline/test_json_reload.py --input output/test/json/search_20240115_143022.json

# 使用简写形式
python test/pipeline/test_json_reload.py -i output/test/json/search_20240115_143022.json

# 查看帮助信息
python test/pipeline/test_json_reload.py --help
```

**命令行参数：**
- `-i, --input FILE` - 指定输入的 JSON 文件路径（可选，不指定则使用最新文件）

**输出位置：**
- `output/test/reloaded/markdown/` - 重新生成的 Markdown 文件
- `output/test/reloaded/html/` - 重新生成的 HTML 文件
- 控制台 - Console 输出

## 配置说明

两个测试脚本都在文件开头定义了配置参数，可以修改这些参数来自定义测试：

### test_output_standalone.py 配置

```python
OUTPUT_BASE_DIR = "output/test"           # 测试输出的基础目录
OUTPUT_FORMATS = ["console", "json", "markdown", "html"]  # 要测试的输出格式

MARKDOWN_TEMPLATE_DIR = "template/markdown"
MARKDOWN_DOCUMENT_TEMPLATE = "document.md"
MARKDOWN_PAPER_TEMPLATE = "paper.md"
MARKDOWN_PAPER_SEPARATOR = "\n\n---\n\n"

HTML_TEMPLATE_DIR = "template/html/scholar"
HTML_DOCUMENT_TEMPLATE = "document.html"
HTML_PAPER_TEMPLATE = "paper.html"

TEST_ACTION_NAME = "test"               # 测试的命令名称（用于文件名）
```

### test_json_reload.py 配置

```python
INPUT_JSON_DIR = "output/test/json"     # 源 JSON 文件的目录
OUTPUT_BASE_DIR = "output/test/reloaded" # 重新输出的目录
OUTPUT_FORMATS = ["console", "markdown", "html"]  # 输出格式（不包括 json）

# Markdown 和 HTML 模板配置...
```

## 测试数据

两个脚本都使用相同的硬编码测试数据，包含 3 篇模拟论文：

1. **深度学习在自然语言处理中的应用** - 包含完整的翻译和摘要增强
2. **Quantum Computing Applications in Cryptography** - 仅包含翻译
3. **Neural Architecture Search: Methods and Applications** - 仅包含摘要增强

这样设计的目的是测试不同情况下的输出渲染。

## 用途

这些独立测试脚本的主要用途：

1. **开发调试** - 快速测试输出功能的修改
2. **功能验证** - 验证所有输出格式正常工作
3. **示例参考** - 展示如何使用输出 API
4. **集成测试** - 不依赖外部 API 的完整输出流程测试
