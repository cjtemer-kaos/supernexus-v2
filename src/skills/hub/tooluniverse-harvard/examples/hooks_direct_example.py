#!/usr/bin/env python3
"""
简化的 MCP stdio 模式 hooks 测试
直接测试工具调用功能
"""
import subprocess
import sys
import signal
import time


def test_tool_call_directly(hooks_enabled=False, timeout=30):
    """直接测试工具调用"""
    print(f"\n{'='*60}")
    print(f"测试模式: {'开启 hooks' if hooks_enabled else '关闭 hooks'}")
    print(f"超时设置: {timeout}秒")
    print(f"{'='*60}")

    # 构建命令
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
import time
sys.path.insert(0, 'src')
from tooluniverse.execute_function import ToolUniverse

# 创建 ToolUniverse 实例
tooluniverse = ToolUniverse()

# 配置 hooks
if {hooks_enabled}:
    print("启用 hooks...")
    tooluniverse.toggle_hooks(True)
else:
    print("禁用 hooks...")
    tooluniverse.toggle_hooks(False)

# 加载工具
print("加载工具...")
tooluniverse.load_tools()

# 测试工具调用
function_call = {{
    "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
    "arguments": {{"ensemblId": "ENSG00000012048"}}
}}

print("开始工具调用...")
start_time = time.time()
result = tooluniverse.run_one_function(function_call)
end_time = time.time()

response_time = end_time - start_time
result_str = str(result)
result_length = len(result_str)

print(f"工具调用完成")
print(f"响应时间: {{response_time:.2f}} 秒")
print(f"响应长度: {{result_length}} 字符")
print(f"响应类型: {{type(result)}}")

# 检查是否是摘要
if "summary" in result_str.lower() or "摘要" in result_str:
    print("✅ 检测到摘要内容")
else:
    print("📄 原始内容（未摘要）")

# 输出结果的前200个字符
print(f"结果预览: {{result_str[:200]}}...")
""",
    ]

    print(f"启动命令: {' '.join(cmd[:3])} ...")

    # 启动进程
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
    )

    try:
        # 等待执行完成
        stdout, stderr = process.communicate(timeout=timeout)

        print("标准输出:")
        print(stdout)

        if stderr:
            print("标准错误:")
            print(stderr)

        # 解析结果
        lines = stdout.split("\n")
        response_time = None
        result_length = None
        is_summary = False

        for line in lines:
            if "响应时间:" in line:
                try:
                    response_time = float(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            elif "响应长度:" in line:
                try:
                    result_length = int(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            elif "检测到摘要内容" in line:
                is_summary = True

        return {
            "hooks_enabled": hooks_enabled,
            "response_time": response_time,
            "result_length": result_length,
            "is_summary": is_summary,
            "success": process.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
        }

    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        process.kill()
        return {
            "hooks_enabled": hooks_enabled,
            "response_time": None,
            "result_length": None,
            "is_summary": False,
            "success": False,
            "error": "超时",
        }
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {
            "hooks_enabled": hooks_enabled,
            "response_time": None,
            "result_length": None,
            "is_summary": False,
            "success": False,
            "error": str(e),
        }


def main():
    """主函数"""
    print("MCP stdio 模式 hooks 直接测试")
    print("测试工具: OpenTargets_get_target_gene_ontology_by_ensemblID")
    print("测试参数: ensemblId=ENSG00000012048")

    # 测试关闭 hooks (减少超时时间)
    result_no_hooks = test_tool_call_directly(hooks_enabled=False, timeout=20)

    # 测试开启 hooks (减少超时时间)
    result_with_hooks = test_tool_call_directly(hooks_enabled=True, timeout=20)

    # 对比结果
    print(f"\n{'='*60}")
    print("测试结果对比")
    print(f"{'='*60}")

    print("关闭 hooks:")
    if result_no_hooks["success"]:
        print(
            f"  ✅ 成功 - 响应时间: {result_no_hooks['response_time']:.2f}s, 长度: {result_no_hooks['result_length']} 字符"
        )
        if result_no_hooks["is_summary"]:
            print("  📄 检测到摘要内容")
        else:
            print("  📄 原始内容（未摘要）")
    else:
        print(f"  ❌ 失败 - {result_no_hooks.get('error', '未知错误')}")

    print("开启 hooks:")
    if result_with_hooks["success"]:
        print(
            f"  ✅ 成功 - 响应时间: {result_with_hooks['response_time']:.2f}s, 长度: {result_with_hooks['result_length']} 字符"
        )
        if result_with_hooks["is_summary"]:
            print("  ✅ 检测到摘要内容")
        else:
            print("  📄 原始内容（未摘要）")
    else:
        print(f"  ❌ 失败 - {result_with_hooks.get('error', '未知错误')}")

    # 性能对比
    if result_no_hooks["success"] and result_with_hooks["success"]:
        time_diff = (
            result_with_hooks["response_time"] - result_no_hooks["response_time"]
        )
        length_diff = (
            result_with_hooks["result_length"] - result_no_hooks["result_length"]
        )

        print("\n性能对比:")
        print(
            f"  时间差异: {time_diff:+.2f}s ({'hooks 更慢' if time_diff > 0 else 'hooks 更快'})"
        )
        print(
            f"  长度差异: {length_diff:+d} 字符 ({'hooks 更长' if length_diff > 0 else 'hooks 更短'})"
        )

        if abs(time_diff) < 5.0:
            print("  ✅ 时间差异在可接受范围内")
        else:
            print("  ⚠️ 时间差异较大，需要进一步优化")

        # 检查 hooks 是否生效
        if result_with_hooks["is_summary"] and not result_no_hooks["is_summary"]:
            print("  ✅ Hooks 功能正常工作")
        elif result_with_hooks["is_summary"] == result_no_hooks["is_summary"]:
            print("  ⚠️ Hooks 功能可能未生效")


if __name__ == "__main__":
    main()
