"""独立测试脚本：从 JSON 文件加载数据并重新输出

该脚本演示如何将之前输出的 JSON 文件作为数据源，
重新加载并输出到其他格式（Console、Markdown、HTML）。

功能：
1. 从 JSON 文件读取论文数据
2. 将数据输出到所有格式（除 JSON 本身）
3. 验证数据完整性

使用方式：
    python test/pipeline/test_json_reload.py                           # 使用最新的 JSON 文件
    python test/pipeline/test_json_reload.py --input path/to/file.json  # 指定 JSON 文件
"""

import argparse
from pathlib import Path

from PaperTracker.renderers.json import load_query_results
from PaperTracker.renderers.console import ConsoleOutputWriter
from PaperTracker.renderers.markdown import MarkdownFileWriter
from PaperTracker.renderers.html import HtmlFileWriter
from PaperTracker.config import OutputConfig

# ============================================================================
# 全局配置参数
# ============================================================================

# JSON 输入文件配置
INPUT_JSON_DIR = "database"  # 存放源 JSON 文件的目录

# 输出目录配置
OUTPUT_BASE_DIR = "output/test/reloaded"  # 重新输出的目录
OUTPUT_FORMATS = ["console", "markdown", "html"]  # 要输出的格式（不包括 json）

# Markdown 模板配置
MARKDOWN_TEMPLATE_DIR = "template/markdown"
MARKDOWN_DOCUMENT_TEMPLATE = "document.md"
MARKDOWN_PAPER_TEMPLATE = "paper.md"
MARKDOWN_PAPER_SEPARATOR = "\n\n---\n\n"

# HTML 模板配置
HTML_TEMPLATE_DIR = "template/html/interactive"
HTML_DOCUMENT_TEMPLATE = "document.html"
HTML_PAPER_TEMPLATE = "paper.html"


def find_latest_json_file() -> Path | None:
    """查找最新的 JSON 文件

    Returns:
        最新的 JSON 文件路径，如果未找到返回 None
    """
    json_dir = Path(INPUT_JSON_DIR)
    if not json_dir.exists():
        print(f"✗ JSON 目录不存在: {json_dir}")
        return None

    json_files = sorted(json_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_files:
        print(f"✗ 未在 {json_dir} 中找到 JSON 文件")
        return None

    return json_files[0]


def load_and_display_query_results(json_file: Path) -> list:
    """加载并显示 JSON 文件中的查询结果

    Args:
        json_file: JSON 文件路径

    Returns:
        加载的 (SearchQuery, list[PaperView]) 元组列表
    """
    print("\n" + "=" * 80)
    print("步骤 1: 从 JSON 文件加载数据")
    print("=" * 80)

    print(f"\n读取文件: {json_file}")
    print(f"文件大小: {json_file.stat().st_size} 字节")

    # 加载完整的查询结果
    query_results = load_query_results(json_file)

    total_papers = sum(len(papers) for _, papers in query_results)
    print(f"\n✓ 成功加载 {len(query_results)} 个查询，共 {total_papers} 篇论文")

    # 显示每个查询的信息
    for i, (query, papers) in enumerate(query_results, 1):
        print(f"\n【查询 {i}: {query.name}】")
        print(f"  论文数量: {len(papers)}")

        # 显示查询字段
        if query.fields:
            print(f"  查询字段:")
            for field_name, field_query in query.fields.items():
                conditions = []
                if field_query.AND:
                    conditions.append(f"AND={list(field_query.AND)}")
                if field_query.OR:
                    conditions.append(f"OR={list(field_query.OR)}")
                if field_query.NOT:
                    conditions.append(f"NOT={list(field_query.NOT)}")
                print(f"    {field_name}: {', '.join(conditions)}")

        # 显示论文列表
        for j, paper in enumerate(papers, 1):
            print(f"\n  论文 {j}:")
            print(f"    ID: {paper.id}")
            print(f"    标题: {paper.title}")
            print(f"    作者: {', '.join(paper.authors[:2])}{'...' if len(paper.authors) > 2 else ''}")
            print(f"    发布: {paper.published}")

            # 检查增强字段
            has_translation = paper.abstract_translation is not None
            has_summary = any([paper.tldr, paper.motivation, paper.method, paper.result, paper.conclusion])
            print(f"    增强: {'翻译✓' if has_translation else '翻译✗'} {'摘要✓' if has_summary else '摘要✗'}")

    return query_results


def output_to_console(query_results: list):
    """输出到控制台

    Args:
        query_results: (SearchQuery, list[PaperView]) 元组列表
    """
    print("\n" + "=" * 80)
    print("步骤 2: 输出到 Console")
    print("=" * 80)

    writer = ConsoleOutputWriter()
    for query, papers in query_results:
        print(f"\n输出查询: {query.name} ({len(papers)} 篇论文)")
        writer.write_query_result(papers, query, scope=None)
    writer.finalize("reloaded_from_json")

    print("\n✓ Console 输出完成")


def output_to_markdown(query_results: list, output_dir: Path):
    """输出到 Markdown 文件

    Args:
        query_results: (SearchQuery, list[PaperView]) 元组列表
        output_dir: 输出目录
    """
    print("\n" + "=" * 80)
    print("步骤 3: 输出到 Markdown")
    print("=" * 80)

    print(f"\n输出目录: {output_dir}")
    print(f"模板目录: {MARKDOWN_TEMPLATE_DIR}")

    config = OutputConfig(
        formats=["markdown"],
        base_dir=str(output_dir),
        markdown_template_dir=MARKDOWN_TEMPLATE_DIR,
        markdown_document_template=MARKDOWN_DOCUMENT_TEMPLATE,
        markdown_paper_template=MARKDOWN_PAPER_TEMPLATE,
        markdown_paper_separator=MARKDOWN_PAPER_SEPARATOR
    )

    writer = MarkdownFileWriter(config)
    for query, papers in query_results:
        print(f"  处理查询: {query.name} ({len(papers)} 篇论文)")
        writer.write_query_result(papers, query, scope=None)
    writer.finalize("reloaded_from_json")

    # 验证输出
    markdown_dir = output_dir / "markdown"
    markdown_files = list(markdown_dir.glob("*.md"))
    print(f"\n✓ 生成了 {len(markdown_files)} 个 Markdown 文件:")
    for f in sorted(markdown_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
        print(f"  - {f.name} ({f.stat().st_size} 字节)")


def output_to_html(query_results: list, output_dir: Path):
    """输出到 HTML 文件

    Args:
        query_results: (SearchQuery, list[PaperView]) 元组列表
        output_dir: 输出目录
    """
    print("\n" + "=" * 80)
    print("步骤 4: 输出到 HTML")
    print("=" * 80)

    print(f"\n输出目录: {output_dir}")
    print(f"模板目录: {HTML_TEMPLATE_DIR}")

    config = OutputConfig(
        formats=["html"],
        base_dir=str(output_dir),
        html_template_dir=HTML_TEMPLATE_DIR,
        html_document_template=HTML_DOCUMENT_TEMPLATE,
        html_paper_template=HTML_PAPER_TEMPLATE,
    )

    writer = HtmlFileWriter(config)
    for query, papers in query_results:
        print(f"  处理查询: {query.name} ({len(papers)} 篇论文)")
        writer.write_query_result(papers, query, scope=None)
    writer.finalize("reloaded_from_json")

    # 验证输出
    html_dir = output_dir / "html"
    html_files = list(html_dir.glob("*.html"))
    print(f"\n✓ 生成了 {len(html_files)} 个 HTML 文件:")
    for f in sorted(html_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
        print(f"  - {f.name} ({f.stat().st_size} 字节)")


def parse_args():
    """解析命令行参数

    Returns:
        解析后的命令行参数
    """
    parser = argparse.ArgumentParser(
        description="从 JSON 文件重新加载论文数据并输出到其他格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 使用最新的 JSON 文件
  python test/pipeline/test_json_reload.py

  # 指定 JSON 文件路径
  python test/pipeline/test_json_reload.py --input output/test/json/search_20240115_143022.json

  # 使用简写形式
  python test/pipeline/test_json_reload.py -i output/test/json/search_20240115_143022.json
        """
    )

    parser.add_argument(
        "-i", "--input",
        type=str,
        metavar="FILE",
        help="指定输入的 JSON 文件路径（如果不指定，则使用最新的 JSON 文件）"
    )

    return parser.parse_args()


def main():
    """主函数：从 JSON 加载并重新输出到所有格式"""
    print("\n" + "=" * 80)
    print("从 JSON 重新加载并输出测试")
    print("=" * 80)

    # 解析命令行参数
    args = parse_args()

    # 确定要使用的 JSON 文件
    if args.input:
        # 使用命令行指定的文件
        json_file = Path(args.input)
        if not json_file.exists():
            print(f"\n✗ 指定的文件不存在: {json_file}")
            return
        if not json_file.is_file():
            print(f"\n✗ 指定的路径不是文件: {json_file}")
            return
        if json_file.suffix != ".json":
            print(f"\n✗ 文件不是 JSON 格式: {json_file}")
            return
        print(f"\n使用指定的 JSON 文件: {json_file}")
    else:
        # 自动查找最新的 JSON 文件
        json_file = find_latest_json_file()
        if not json_file:
            print("\n✗ 找不到 JSON 文件，请先运行 test_output_standalone.py 生成测试数据")
            print("或者使用 --input 参数指定 JSON 文件路径")
            return

    # 加载数据（包含完整的查询信息）
    query_results = load_and_display_query_results(json_file)
    if not query_results:
        print("\n✗ JSON 文件中没有查询数据")
        return

    # 输出目录
    output_dir = Path(OUTPUT_BASE_DIR)

    # 依次输出到各种格式
    if "console" in OUTPUT_FORMATS:
        output_to_console(query_results)

    if "markdown" in OUTPUT_FORMATS:
        output_to_markdown(query_results, output_dir)

    if "html" in OUTPUT_FORMATS:
        output_to_html(query_results, output_dir)

    # 最终总结
    total_papers = sum(len(papers) for _, papers in query_results)
    print("\n" + "=" * 80)
    print("所有格式输出完成！✓")
    print("=" * 80)
    print(f"\n源文件: {json_file}")
    print(f"输出目录: {output_dir}")
    print(f"输出格式: {', '.join(OUTPUT_FORMATS)}")
    print(f"查询数量: {len(query_results)}")
    print(f"论文总数: {total_papers}")


if __name__ == "__main__":
    main()
