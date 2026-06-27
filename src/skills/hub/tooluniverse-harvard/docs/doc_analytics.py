#!/usr/bin/env python3
"""
文档使用分析工具
分析文档使用模式，发现改进机会
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re


class DocAnalytics:
    """文档分析工具"""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.analytics_file = docs_dir / "analytics.json"

    def analyze_content_structure(self):
        """分析内容结构"""
        analysis = {
            "pages": {},
            "total_words": 0,
            "code_blocks": 0,
            "external_links": 0,
            "images": 0,
            "tables": 0,
        }

        for rst_file in self.docs_dir.glob("*.rst"):
            with open(rst_file, "r", encoding="utf-8") as f:
                content = f.read()

            page_analysis = {
                "word_count": len(content.split()),
                "lines": len(content.split("\n")),
                "headers": len(re.findall(r'^[=\-~^"]{3,}$', content, re.MULTILINE)),
                "code_blocks": len(re.findall(r".. code-block::", content)),
                "external_links": len(re.findall(r"https?://", content)),
                "internal_refs": len(re.findall(r":doc:`[^`]+`", content)),
                "images": len(re.findall(r".. image::", content)),
                "tables": len(re.findall(r".. list-table::", content)),
                "tabs": len(re.findall(r".. tabs::", content)),
                "notes": len(re.findall(r".. note::", content)),
                "warnings": len(re.findall(r".. warning::", content)),
                "last_modified": datetime.fromtimestamp(
                    rst_file.stat().st_mtime
                ).isoformat(),
            }

            analysis["pages"][rst_file.name] = page_analysis
            analysis["total_words"] += page_analysis["word_count"]
            analysis["code_blocks"] += page_analysis["code_blocks"]
            analysis["external_links"] += page_analysis["external_links"]
            analysis["images"] += page_analysis["images"]
            analysis["tables"] += page_analysis["tables"]

        return analysis

    def calculate_readability_scores(self):
        """计算可读性分数"""
        scores = {}

        for rst_file in self.docs_dir.glob("*.rst"):
            with open(rst_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 简单的可读性指标
            sentences = len(re.findall(r"[.!?]+", content))
            words = len(content.split())
            complex_words = len(re.findall(r"\w{7,}", content))  # 7+字符的词

            if sentences > 0:
                avg_sentence_length = words / sentences
                complex_word_ratio = complex_words / words if words > 0 else 0

                # 简化的可读性分数 (越低越好读)
                readability_score = (avg_sentence_length * 1.5) + (
                    complex_word_ratio * 100
                )

                scores[rst_file.name] = {
                    "readability_score": round(readability_score, 2),
                    "avg_sentence_length": round(avg_sentence_length, 2),
                    "complex_word_ratio": round(complex_word_ratio, 3),
                    "rating": self._get_readability_rating(readability_score),
                }

        return scores

    def _get_readability_rating(self, score):
        """获取可读性等级"""
        if score < 20:
            return "Very Easy"
        elif score < 40:
            return "Easy"
        elif score < 60:
            return "Moderate"
        elif score < 80:
            return "Difficult"
        else:
            return "Very Difficult"

    def analyze_navigation_depth(self):
        """分析导航深度和结构"""
        structure = {"max_depth": 0, "toc_analysis": {}}

        index_file = self.docs_dir / "index.rst"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 分析 toctree 深度
            toctree_pattern = r".. toctree::\s*\n(?:\s+:maxdepth:\s+(\d+)\s*\n)?"
            matches = re.findall(toctree_pattern, content)

            depths = [int(match) for match in matches if match]
            if depths:
                structure["max_depth"] = max(depths)

        return structure

    def identify_content_gaps(self):
        """识别内容空白"""
        gaps = []

        # 检查是否有空的或过短的页面
        for rst_file in self.docs_dir.glob("*.rst"):
            with open(rst_file, "r", encoding="utf-8") as f:
                content = f.read()

            word_count = len(content.split())

            if word_count < 50:
                gaps.append(
                    {
                        "file": rst_file.name,
                        "issue": "Too short",
                        "word_count": word_count,
                        "priority": "high",
                    }
                )
            elif word_count < 100:
                gaps.append(
                    {
                        "file": rst_file.name,
                        "issue": "Very short",
                        "word_count": word_count,
                        "priority": "medium",
                    }
                )

            # 检查是否缺少代码示例
            if (
                "tutorial" in rst_file.name.lower()
                or "example" in rst_file.name.lower()
            ):
                if ".. code-block::" not in content:
                    gaps.append(
                        {
                            "file": rst_file.name,
                            "issue": "No code examples",
                            "priority": "high",
                        }
                    )

        return gaps

    def suggest_improvements(self):
        """生成改进建议"""
        structure = self.analyze_content_structure()
        readability = self.calculate_readability_scores()
        gaps = self.identify_content_gaps()

        suggestions = []

        # 基于内容分析的建议
        if structure["total_words"] < 5000:
            suggestions.append(
                {
                    "category": "Content Volume",
                    "suggestion": "Consider expanding documentation content",
                    "priority": "medium",
                    "details": f"Total words: {structure['total_words']}",
                }
            )

        # 基于可读性的建议
        difficult_pages = [
            page
            for page, score in readability.items()
            if score.get("readability_score", 0) > 60
        ]

        if difficult_pages:
            suggestions.append(
                {
                    "category": "Readability",
                    "suggestion": "Simplify language in difficult pages",
                    "priority": "high",
                    "details": f"Difficult pages: {', '.join(difficult_pages)}",
                }
            )

        # 基于内容空白的建议
        high_priority_gaps = [gap for gap in gaps if gap["priority"] == "high"]
        if high_priority_gaps:
            suggestions.append(
                {
                    "category": "Content Gaps",
                    "suggestion": "Address high-priority content gaps",
                    "priority": "high",
                    "details": f"{len(high_priority_gaps)} high-priority gaps found",
                }
            )

        # 基于代码示例的建议
        if structure["code_blocks"] < 10:
            suggestions.append(
                {
                    "category": "Examples",
                    "suggestion": "Add more code examples",
                    "priority": "medium",
                    "details": f"Current code blocks: {structure['code_blocks']}",
                }
            )

        return suggestions

    def generate_report(self):
        """生成完整分析报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "structure": self.analyze_content_structure(),
            "readability": self.calculate_readability_scores(),
            "navigation": self.analyze_navigation_depth(),
            "gaps": self.identify_content_gaps(),
            "suggestions": self.suggest_improvements(),
        }

        # 保存报告
        with open(self.analytics_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report


def print_analysis_summary(report):
    """打印分析摘要"""
    print("📊 文档分析报告")
    print("=" * 30)

    structure = report["structure"]
    print(f"\n📄 内容概览:")
    print(f"   页面数量: {len(structure['pages'])}")
    print(f"   总词数: {structure['total_words']:,}")
    print(f"   代码块: {structure['code_blocks']}")
    print(f"   外部链接: {structure['external_links']}")

    readability = report["readability"]
    if readability:
        avg_score = sum(
            page["readability_score"] for page in readability.values()
        ) / len(readability)
        print(f"\n📖 可读性:")
        print(f"   平均分数: {avg_score:.1f}")

        ratings = defaultdict(int)
        for page in readability.values():
            ratings[page["rating"]] += 1

        for rating, count in ratings.items():
            print(f"   {rating}: {count} 页")

    gaps = report["gaps"]
    if gaps:
        print(f"\n⚠️  内容空白:")
        high_priority = sum(1 for gap in gaps if gap["priority"] == "high")
        print(f"   高优先级: {high_priority}")
        print(f"   总计: {len(gaps)}")

    suggestions = report["suggestions"]
    if suggestions:
        print(f"\n💡 改进建议:")
        for suggestion in suggestions:
            priority_emoji = (
                "🔴"
                if suggestion["priority"] == "high"
                else "🟡" if suggestion["priority"] == "medium" else "🟢"
            )
            print(f"   {priority_emoji} {suggestion['suggestion']}")


def main():
    """主函数"""
    docs_dir = Path(__file__).parent
    analytics = DocAnalytics(docs_dir)

    print("🔍 正在分析文档...")
    report = analytics.generate_report()

    print_analysis_summary(report)

    print(f"\n📋 详细报告已保存至: {analytics.analytics_file}")


if __name__ == "__main__":
    main()
