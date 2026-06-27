#!/usr/bin/env python3
"""
自动化文档同步工具
确保文档始终与源代码保持同步
"""

import os
import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Tuple


class DocSyncTool:
    """文档同步工具类"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src" / "tooluniverse"
        self.docs_dir = project_root / "docs"

    def extract_docstrings(self) -> Dict[str, Dict]:
        """提取所有Python文件的docstring"""
        docstrings = {}

        for py_file in self.src_dir.glob("**/*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                module_name = (
                    str(py_file.relative_to(self.src_dir))
                    .replace("/", ".")
                    .replace(".py", "")
                )
                docstrings[module_name] = self._extract_module_docstrings(tree)

            except Exception as e:
                print(f"⚠️  Could not parse {py_file}: {e}")

        return docstrings

    def _extract_module_docstrings(self, tree: ast.AST) -> Dict:
        """提取单个模块的docstring"""
        result = {}

        # 模块docstring
        if ast.get_docstring(tree):
            result["module"] = ast.get_docstring(tree)

        # 类和函数docstring
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if ast.get_docstring(node):
                    result[f"class_{node.name}"] = ast.get_docstring(node)

                # 类方法
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and ast.get_docstring(
                        method
                    ):
                        result[f"method_{node.name}.{method.name}"] = ast.get_docstring(
                            method
                        )

            elif isinstance(node, ast.FunctionDef) and not any(
                isinstance(parent, ast.ClassDef)
                for parent in ast.walk(tree)
                if hasattr(parent, "body") and node in getattr(parent, "body", [])
            ):
                if ast.get_docstring(node):
                    result[f"function_{node.name}"] = ast.get_docstring(node)

        return result

    def check_api_consistency(self) -> List[str]:
        """检查API一致性"""
        issues = []

        # 检查ToolUniverse类的主要方法
        tooluniverse_file = self.src_dir / "execute_function.py"
        if tooluniverse_file.exists():
            with open(tooluniverse_file, "r") as f:
                content = f.read()

            # 提取实际方法名
            method_pattern = r"def\s+(\w+)\s*\("
            actual_methods = re.findall(method_pattern, content)

            # 检查文档中提到的方法
            doc_files = list(self.docs_dir.glob("*.rst"))
            for doc_file in doc_files:
                with open(doc_file, "r") as f:
                    doc_content = f.read()

                # 查找文档中提到的方法调用
                doc_method_pattern = r"\.(\w+)\("
                doc_methods = re.findall(doc_method_pattern, doc_content)

                for method in doc_methods:
                    if method not in actual_methods and method not in [
                        "run",
                        "load_tools",
                        "list_built_in_tools",
                    ]:
                        issues.append(
                            f"📄 {doc_file.name}: 方法 '{method}' 在源代码中未找到"
                        )

        return issues

    def generate_api_reference(self) -> str:
        """生成API快速参考"""
        docstrings = self.extract_docstrings()

        reference = "API Quick Reference\n"
        reference += "=" * 20 + "\n\n"
        reference += ".. note::\n"
        reference += "   此页面自动生成，与源代码保持同步。\n\n"

        for module, content in docstrings.items():
            if content:
                reference += f"{module}\n"
                reference += "-" * len(module) + "\n\n"

                if "module" in content:
                    reference += f"{content['module'][:200]}...\n\n"

                # 添加类和函数
                for key, docstring in content.items():
                    if key.startswith("class_"):
                        class_name = key.replace("class_", "")
                        reference += f"**{class_name}**\n\n"
                        reference += f"   {docstring[:100]}...\n\n"
                    elif key.startswith("function_"):
                        func_name = key.replace("function_", "")
                        reference += f"- ``{func_name}()``\n"

                reference += "\n"

        return reference

    def update_tool_list(self) -> List[str]:
        """更新工具列表"""
        tools = []

        # 从工具注册表获取工具
        registry_file = self.src_dir / "tool_registry.py"
        if registry_file.exists():
            with open(registry_file, "r") as f:
                content = f.read()

            # 查找@register_tool装饰器
            tool_pattern = r"@register_tool\(['\"]([^'\"]+)['\"]\)"
            registered_tools = re.findall(tool_pattern, content)
            tools.extend(registered_tools)

        # 从各个工具文件获取
        for tool_file in self.src_dir.glob("*_tool.py"):
            with open(tool_file, "r") as f:
                content = f.read()

            class_pattern = r"class\s+(\w+Tool)\s*\("
            tool_classes = re.findall(class_pattern, content)
            tools.extend(tool_classes)

        return sorted(list(set(tools)))

    def validate_examples(self) -> Dict[str, List[str]]:
        """验证文档示例"""
        issues = {}

        for rst_file in self.docs_dir.glob("*.rst"):
            file_issues = []

            with open(rst_file, "r") as f:
                content = f.read()

            # 查找代码块
            code_pattern = r".. code-block:: python\s*\n\n((?:   .*\n)*)"
            code_blocks = re.findall(code_pattern, content, re.MULTILINE)

            for i, code_block in enumerate(code_blocks):
                # 清理缩进
                lines = code_block.split("\n")
                cleaned_lines = [
                    line[3:] if line.startswith("   ") else line for line in lines
                ]
                code = "\n".join(cleaned_lines).strip()

                if code:
                    # 语法检查
                    try:
                        ast.parse(code)
                    except SyntaxError as e:
                        file_issues.append(f"代码块 {i+1}: 语法错误 - {e}")

                    # 导入检查
                    if "from tooluniverse import" in code and "ToolUniverse" in code:
                        if "load_tools()" not in code:
                            file_issues.append(f"代码块 {i+1}: 缺少 load_tools() 调用")

            if file_issues:
                issues[rst_file.name] = file_issues

        return issues


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    sync_tool = DocSyncTool(project_root)

    print("🔄 文档同步检查")
    print("=" * 30)

    # 1. API一致性检查
    print("\n📋 检查API一致性...")
    api_issues = sync_tool.check_api_consistency()
    if api_issues:
        for issue in api_issues:
            print(f"   ⚠️  {issue}")
    else:
        print("   ✅ API一致性良好")

    # 2. 验证示例代码
    print("\n🧪 验证示例代码...")
    example_issues = sync_tool.validate_examples()
    if example_issues:
        for file, issues in example_issues.items():
            print(f"   📄 {file}:")
            for issue in issues:
                print(f"      ❌ {issue}")
    else:
        print("   ✅ 所有示例代码有效")

    # 3. 工具列表更新
    print("\n🔧 检查工具列表...")
    tools = sync_tool.update_tool_list()
    print(f"   📊 发现 {len(tools)} 个工具")

    # 4. 生成报告
    total_issues = len(api_issues) + sum(
        len(issues) for issues in example_issues.values()
    )

    print(f"\n📈 同步检查完成")
    print(f"   🔍 发现 {total_issues} 个问题")

    if total_issues == 0:
        print("   🎉 文档与代码完全同步！")
    else:
        print("   💡 建议修复发现的问题以提高文档质量")


if __name__ == "__main__":
    main()
