#!/usr/bin/env python3
"""
测试 MCP stdio 模式下关闭和开启 hooks 的情况
"""
import subprocess
import json
import time
import sys


def run_stdio_test(hooks_enabled=False):
    """运行 stdio 测试"""
    print(f"\n{'='*60}")
    print(f"测试模式: {'开启 hooks' if hooks_enabled else '关闭 hooks'}")
    print(f"{'='*60}")

    # 构建命令
    cmd = [
        sys.executable,
        "-c",
        f"""
import sys
sys.path.insert(0, 'src')
from tooluniverse.smcp_server import run_stdio_server
sys.argv = ['tooluniverse-smcp-stdio'] + (['--hooks'] if {hooks_enabled} else [])
run_stdio_server()
""",
    ]

    print(f"启动命令: {' '.join(cmd[:3])} ...")

    # 启动服务器进程
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
    )

    try:
        # 等待服务器启动并读取启动日志
        time.sleep(3)

        # 读取并丢弃启动日志
        print("读取启动日志...")
        while True:
            line = process.stdout.readline()
            if not line:
                break
            print(f"启动日志: {line.strip()}")
            if "Starting ToolUniverse SMCP Server" in line:
                break

        # 发送初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        print("发送初始化请求...")
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()

        # 读取初始化响应
        init_response = process.stdout.readline()
        print(f"初始化响应: {init_response.strip()}")

        # 发送 tools/list 请求
        list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        print("发送 tools/list 请求...")
        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        # 读取 tools/list 响应
        list_response = process.stdout.readline()
        print(f"tools/list 响应长度: {len(list_response)} 字符")

        # 发送测试工具调用请求
        test_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
                "arguments": {"ensemblId": "ENSG00000012048"},
            },
        }

        print("发送测试工具调用请求...")
        process.stdin.write(json.dumps(test_request) + "\n")
        process.stdin.flush()

        # 读取工具调用响应（可能需要等待更长时间）
        print("等待工具调用响应...")
        start_time = time.time()

        # 读取多行响应，直到找到 JSON 响应
        tool_response = ""
        timeout = 30  # 30秒超时
        while time.time() - start_time < timeout:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue

            tool_response += line
            print(f"收到响应行: {repr(line)}")

            # 检查是否是 JSON 响应
            try:
                json.loads(line.strip())
                break
            except json.JSONDecodeError:
                continue

        end_time = time.time()
        response_time = end_time - start_time
        response_length = len(tool_response)

        print(f"工具调用响应时间: {response_time:.2f} 秒")
        print(f"工具调用响应长度: {response_length} 字符")
        print(f"原始响应内容: {repr(tool_response)}")

        # 尝试解析 JSON 响应
        json_response = None
        for line in tool_response.split("\n"):
            if line.strip().startswith('{"jsonrpc"'):
                try:
                    json_response = json.loads(line.strip())
                    break
                except json.JSONDecodeError:
                    continue

        if json_response:
            print("✅ 成功解析 JSON 响应")
            print(f"响应 ID: {json_response.get('id')}")
            if "result" in json_response:
                print("✅ 工具调用成功")
            elif "error" in json_response:
                print(f"❌ 工具调用失败: {json_response['error']}")
        else:
            print("⚠️ 未找到有效的 JSON 响应")

        # 继续等待实际的工具调用响应
        print("等待工具调用完成...")
        time.sleep(5)  # 等待工具执行完成

        # 读取工具调用的实际响应
        actual_response = ""
        while True:
            line = process.stdout.readline()
            if not line:
                break
            actual_response += line
            print(f"工具响应行: {repr(line)}")

            # 检查是否是 JSON 响应
            try:
                json.loads(line.strip())
                break
            except json.JSONDecodeError:
                continue

        if actual_response:
            print(f"工具调用实际响应长度: {len(actual_response)} 字符")

            # 尝试解析工具调用响应
            tool_json_response = None
            for line in actual_response.split("\n"):
                if line.strip().startswith('{"jsonrpc"'):
                    try:
                        tool_json_response = json.loads(line.strip())
                        break
                    except json.JSONDecodeError:
                        continue

            if tool_json_response and "result" in tool_json_response:
                result_content = tool_json_response["result"]
                if "content" in result_content:
                    content_text = str(result_content["content"])
                    content_length = len(content_text)
                    print(f"工具响应内容长度: {content_length} 字符")

                    # 检查是否是摘要
                    if "summary" in content_text.lower() or "摘要" in content_text:
                        print("✅ 检测到摘要内容")
                    else:
                        print("📄 原始内容（未摘要）")
                else:
                    print("⚠️ 工具响应中没有 content 字段")
            else:
                print("⚠️ 无法解析工具调用响应")

        return {
            "hooks_enabled": hooks_enabled,
            "response_time": response_time,
            "response_length": response_length,
            "success": True,
        }

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {
            "hooks_enabled": hooks_enabled,
            "response_time": None,
            "response_length": None,
            "success": False,
            "error": str(e),
        }
    finally:
        # 清理进程
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            process.kill()


def main():
    """主函数"""
    print("MCP stdio 模式 hooks 测试")
    print("测试工具: OpenTargets_get_target_gene_ontology_by_ensemblID")
    print("测试参数: ensemblId=ENSG00000012048")

    # 测试关闭 hooks
    result_no_hooks = run_stdio_test(hooks_enabled=False)

    # 测试开启 hooks
    result_with_hooks = run_stdio_test(hooks_enabled=True)

    # 对比结果
    print(f"\n{'='*60}")
    print("测试结果对比")
    print(f"{'='*60}")

    print("关闭 hooks:")
    if result_no_hooks["success"]:
        print(
            f"  ✅ 成功 - 响应时间: {result_no_hooks['response_time']:.2f}s, 长度: {result_no_hooks['response_length']} 字符"
        )
    else:
        print(f"  ❌ 失败 - {result_no_hooks.get('error', '未知错误')}")

    print("开启 hooks:")
    if result_with_hooks["success"]:
        print(
            f"  ✅ 成功 - 响应时间: {result_with_hooks['response_time']:.2f}s, 长度: {result_with_hooks['response_length']} 字符"
        )
    else:
        print(f"  ❌ 失败 - {result_with_hooks.get('error', '未知错误')}")

    # 性能对比
    if result_no_hooks["success"] and result_with_hooks["success"]:
        time_diff = (
            result_with_hooks["response_time"] - result_no_hooks["response_time"]
        )
        length_diff = (
            result_with_hooks["response_length"] - result_no_hooks["response_length"]
        )

        print("\n性能对比:")
        print(
            f"  时间差异: {time_diff:+.2f}s ({'hooks 更慢' if time_diff > 0 else 'hooks 更快'})"
        )
        print(
            f"  长度差异: {length_diff:+d} 字符 ({'hooks 更长' if length_diff > 0 else 'hooks 更短'})"
        )

        if abs(time_diff) < 1.0:
            print("  ✅ 时间差异在可接受范围内")
        else:
            print("  ⚠️ 时间差异较大，需要进一步优化")


if __name__ == "__main__":
    main()
