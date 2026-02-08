"""独立测试脚本：测试 output_writer 输出功能

该脚本使用硬编码的测试数据，独立测试各种格式的输出功能。
测试包括：Console、JSON、Markdown 三种输出格式。
不依赖外部配置文件，所有测试数据都在代码中定义。
"""

from pathlib import Path

from PaperTracker.core.query import FieldQuery, SearchQuery
from PaperTracker.renderers.view_models import PaperView
from PaperTracker.renderers.console import ConsoleOutputWriter, render_text
from PaperTracker.renderers.json import JsonFileWriter, render_json
from PaperTracker.renderers.markdown import MarkdownFileWriter
from PaperTracker.config import OutputConfig

# ============================================================================
# 全局配置参数 - 可根据需要修改
# ============================================================================

# 输出目录配置
OUTPUT_BASE_DIR = "output/test"           # 测试输出的基础目录
OUTPUT_FORMATS = ["console", "json", "markdown"]  # 要测试的输出格式

# Markdown 模板配置
MARKDOWN_TEMPLATE_DIR = "template/markdown"
MARKDOWN_DOCUMENT_TEMPLATE = "document.md"
MARKDOWN_PAPER_TEMPLATE = "paper.md"
MARKDOWN_PAPER_SEPARATOR = "\n\n---\n\n"

# 测试数据配置
TEST_ACTION_NAME = "search"               # 测试的命令名称（用于文件名）


def create_test_paper_views():
    """创建测试用的 PaperView 对象列表"""

    # 测试论文 1: 包含完整的 LLM 增强数据
    view1 = PaperView(
        source="arxiv",
        id="2401.12345",
        title="深度学习在自然语言处理中的应用",
        authors=["张三", "李四", "Wang Wu"],
        abstract="This paper presents a comprehensive survey of deep learning techniques "
                "for natural language processing. We review recent advances in "
                "transformer architectures, pre-training methods, and their applications.",
        published="2024-01-15",
        updated="2024-01-20",
        primary_category="cs.CL",
        categories=["cs.CL", "cs.AI", "cs.LG"],
        abstract_url="https://arxiv.org/abs/2401.12345",
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        doi="10.48550/arXiv.2401.12345",
        abstract_translation="本文全面综述了用于自然语言处理的深度学习技术。"
                            "我们回顾了 Transformer 架构、预训练方法及其应用的最新进展。",
        tldr="对 NLP 领域深度学习技术的全面综述，重点关注 Transformer 和预训练",
        motivation="随着深度学习的快速发展，需要系统性地总结和归纳 NLP 领域的最新成果",
        method="通过文献调研和分类整理，系统性地回顾了 Transformer 架构和预训练方法",
        result="总结了 50+ 篇重要论文，构建了完整的技术演进脉络",
        conclusion="深度学习已经成为 NLP 的主流范式，未来研究应关注效率和可解释性"
    )

    # 测试论文 2: 仅包含翻译，没有摘要增强
    view2 = PaperView(
        source="arxiv",
        id="2401.67890",
        title="Quantum Computing Applications in Cryptography",
        authors=["Alice Johnson", "Bob Smith"],
        abstract="We explore the potential of quantum computing in breaking classical "
                "cryptographic systems and propose quantum-resistant algorithms.",
        published="2024-01-10",
        updated=None,
        primary_category="quant-ph",
        categories=["quant-ph", "cs.CR"],
        abstract_url="https://arxiv.org/abs/2401.67890",
        pdf_url="https://arxiv.org/pdf/2401.67890.pdf",
        doi=None,
        abstract_translation="我们探索了量子计算在破解经典密码系统方面的潜力，并提出了抗量子算法。"
    )

    # 测试论文 3: 仅包含摘要增强，没有翻译
    view3 = PaperView(
        source="arxiv",
        id="2401.11111",
        title="Neural Architecture Search: Methods and Applications",
        authors=["Charlie Chen"],
        abstract="This work surveys neural architecture search methods and their "
                "practical applications in computer vision and NLP tasks.",
        published="2024-01-05",
        updated="2024-01-06",
        primary_category="cs.LG",
        categories=["cs.LG", "cs.CV"],
        abstract_url="https://arxiv.org/abs/2401.11111",
        pdf_url=None,
        doi=None,
        tldr="NAS 方法及其在 CV 和 NLP 中的应用综述",
        motivation="自动化神经网络架构设计可以降低人工成本并提升性能",
        method="系统性回顾了基于强化学习、进化算法和梯度的 NAS 方法",
        result="总结了各类 NAS 方法的优缺点和适用场景",
        conclusion="NAS 在实际应用中仍面临计算成本高的挑战"
    )

    return [view1, view2, view3]


def create_test_queries():
    """创建测试用的 SearchQuery 对象列表"""

    # Query 1: 深度学习相关
    query1 = SearchQuery(
        name="深度学习与NLP",
        fields={
            "TEXT": FieldQuery(
                OR=["deep learning", "neural network"],
                AND=["natural language processing"],
                NOT=["image", "vision"]
            ),
            "CATEGORY": FieldQuery(
                OR=["cs.CL", "cs.AI"]
            )
        }
    )

    # Query 2: 量子计算相关
    query2 = SearchQuery(
        name="量子计算应用",
        fields={
            "TEXT": FieldQuery(
                OR=["quantum computing", "quantum algorithm"],
                AND=["cryptography"]
            ),
            "CATEGORY": FieldQuery(
                OR=["quant-ph", "cs.CR"]
            )
        }
    )

    # Query 3: 神经架构搜索
    query3 = SearchQuery(
        name="神经架构搜索",
        fields={
            "TITLE": FieldQuery(
                OR=["Neural Architecture Search", "NAS", "AutoML"]
            )
        }
    )

    return [query1, query2, query3]


def test_console_output():
    """测试控制台输出"""
    print("\n" + "=" * 80)
    print("测试 1: Console 输出格式")
    print("=" * 80)

    views = create_test_paper_views()
    queries = create_test_queries()

    # 测试 render_text 函数
    text_output = render_text(views)
    print("\n--- render_text 函数输出 ---")
    print(text_output)

    # 测试 ConsoleOutputWriter
    print("\n--- ConsoleOutputWriter 类输出 ---")
    writer = ConsoleOutputWriter()

    # 写入多个查询结果
    for view, query in zip(views, queries):
        print(f"\n查询名称: {query.name}")
        writer.write_query_result([view], query, scope=None)

    writer.finalize(TEST_ACTION_NAME)
    print("\n✓ Console 输出测试完成")


def test_json_output():
    """测试 JSON 文件输出"""
    print("\n" + "=" * 80)
    print("测试 2: JSON 文件输出格式")
    print("=" * 80)

    views = create_test_paper_views()
    queries = create_test_queries()

    # 测试 render_json 函数
    json_data = render_json(views)
    print(f"\n✓ render_json 生成了 {len(json_data)} 个论文对象")
    print(f"示例数据字段: {list(json_data[0].keys())}")

    # 使用配置的输出目录测试 JsonFileWriter
    output_dir = Path(OUTPUT_BASE_DIR)
    print(f"\n使用输出目录: {output_dir}")

    writer = JsonFileWriter(base_dir=str(output_dir))

    # 写入多个查询结果
    for view, query in zip(views, queries):
        writer.write_query_result([view], query, scope=None)

    # 最终化写入文件
    writer.finalize(TEST_ACTION_NAME)

    # 验证文件是否生成
    json_dir = output_dir / "json"
    json_files = list(json_dir.glob("*.json"))
    print(f"\n✓ 生成了 {len(json_files)} 个 JSON 文件:")
    for f in json_files:
        print(f"  - {f.name} (大小: {f.stat().st_size} 字节)")

        # 读取并显示文件内容摘要
        import json
        content = json.loads(f.read_text(encoding="utf-8"))
        print(f"    包含 {len(content)} 个查询结果")
        for i, result in enumerate(content, 1):
            print(f"    查询 {i}: {result['name']} - {len(result['papers'])} 篇论文")

    print("\n✓ JSON 文件输出测试完成")


def test_markdown_output():
    """测试 Markdown 文件输出"""
    print("\n" + "=" * 80)
    print("测试 3: Markdown 文件输出格式")
    print("=" * 80)

    views = create_test_paper_views()
    queries = create_test_queries()

    # 使用配置的输出目录和模板
    output_dir = Path(OUTPUT_BASE_DIR)
    print(f"\n使用输出目录: {output_dir}")
    print(f"使用模板目录: {MARKDOWN_TEMPLATE_DIR}")

    # 创建 OutputConfig，使用全局配置
    output_config = OutputConfig(
        formats=["markdown"],
        base_dir=str(output_dir),
        markdown_template_dir=MARKDOWN_TEMPLATE_DIR,
        markdown_document_template=MARKDOWN_DOCUMENT_TEMPLATE,
        markdown_paper_template=MARKDOWN_PAPER_TEMPLATE,
        markdown_paper_separator=MARKDOWN_PAPER_SEPARATOR
    )

    writer = MarkdownFileWriter(output_config)

    # 写入多个查询结果
    for view, query in zip(views, queries):
        print(f"处理查询: {query.name}")
        writer.write_query_result([view], query, scope=None)

    # 最终化写入文件
    writer.finalize(TEST_ACTION_NAME)

    # 验证文件是否生成
    markdown_dir = output_dir / "markdown"
    markdown_files = list(markdown_dir.glob("*.md"))
    print(f"\n✓ 生成了 {len(markdown_files)} 个 Markdown 文件:")
    for f in markdown_files:
        file_size = f.stat().st_size
        print(f"  - {f.name} (大小: {file_size} 字节)")

        # 读取并显示文件内容摘要
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")
        print(f"    行数: {len(lines)}")
        print(f"    前 5 行预览:")
        for line in lines[:5]:
            print(f"      {line}")

    print("\n✓ Markdown 文件输出测试完成")


def test_multiple_formats():
    """测试同时使用多种输出格式"""
    print("\n" + "=" * 80)
    print("测试 4: 多种格式同时输出")
    print("=" * 80)

    views = create_test_paper_views()
    queries = create_test_queries()

    output_dir = Path(OUTPUT_BASE_DIR)
    print(f"\n使用输出目录: {output_dir}")
    print(f"使用模板目录: {MARKDOWN_TEMPLATE_DIR}")
    print(f"输出格式: {', '.join(OUTPUT_FORMATS)}")

    # 创建配置，使用全局变量
    output_config = OutputConfig(
        formats=tuple(OUTPUT_FORMATS),
        base_dir=str(output_dir),
        markdown_template_dir=MARKDOWN_TEMPLATE_DIR,
        markdown_document_template=MARKDOWN_DOCUMENT_TEMPLATE,
        markdown_paper_template=MARKDOWN_PAPER_TEMPLATE,
        markdown_paper_separator=MARKDOWN_PAPER_SEPARATOR
    )

    # 创建所有 writer
    writers = []
    if "console" in OUTPUT_FORMATS:
        writers.append(ConsoleOutputWriter())
    if "json" in OUTPUT_FORMATS:
        writers.append(JsonFileWriter(str(output_dir)))
    if "markdown" in OUTPUT_FORMATS:
        writers.append(MarkdownFileWriter(output_config))

    # 写入数据到所有 writer
    for view, query in zip(views, queries):
        print(f"\n写入查询: {query.name}")
        for writer in writers:
            writer.write_query_result([view], query, scope=None)

    # 最终化所有 writer
    for writer in writers:
        writer.finalize(TEST_ACTION_NAME)

    # 验证生成的文件
    if "json" in OUTPUT_FORMATS:
        json_files = list((output_dir / "json").glob("*.json"))
        print(f"\n✓ 生成了 {len(json_files)} 个 JSON 文件")
    if "markdown" in OUTPUT_FORMATS:
        markdown_files = list((output_dir / "markdown").glob("*.md"))
        print(f"✓ 生成了 {len(markdown_files)} 个 Markdown 文件")
    if "console" in OUTPUT_FORMATS:
        print("✓ Console 输出已显示在标准输出")

    print("\n✓ 多格式同时输出测试完成")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("开始测试 OutputWriter 输出模块")
    print("=" * 80)

    test_console_output()
    test_json_output()
    test_markdown_output()
    test_multiple_formats()

    print("\n" + "=" * 80)
    print("所有输出格式测试通过！✓")
    print("=" * 80)


if __name__ == "__main__":
    main()
