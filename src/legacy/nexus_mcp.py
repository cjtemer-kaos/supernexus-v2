import sys
import json
import requests
import os
import logging

# NEXUS MCP Bridge
# This script acts as a stdio MCP server for Antigravity,
# forwarding tool calls to the Nexus IA local API (port 9000).

NEXUS_URL = "http://localhost:9000/api"
LOG_FILE = os.path.join(os.path.dirname(__file__), "nexus_mcp.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_tools():
    return {
        "tools": [
            {
                "name": "nexus_chat",
                "description": "Send a prompt to the local Nexus IA (uses local models like Qwen/DeepSeek).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "gem": {"type": "string", "enum": ["auto", "architect", "developer", "creative", "scholar", "prompter", "sage", "codex", "sentinel", "synthesizer", "narrator"]},
                        "engine": {"type": "string", "default": "local"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "nexus_skill",
                "description": "Execute a specific Nexus skill method.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string"},
                        "method": {"type": "string"},
                        "params": {"type": "object"}
                    },
                    "required": ["skill", "method"]
                }
            },
            {
                "name": "opencode_task",
                "description": "Execute a task using the OpenCode engine (supports Minimax m2.5).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "model": {"type": "string", "default": "minimax-m2.5"},
                        "workspace": {"type": "string"},
                        "node": {"type": "string", "enum": ["local", "pc2", "auto"], "default": "local"}
                    },
                    "required": ["task"]
                }
            },
            {
                "name": "pc2_chat",
                "description": "Delegate a task to the Nexus IA running on PC2 (Linux node).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "gem": {"type": "string", "default": "auto"}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "pc2_minimax",
                "description": "Use PC2's power to generate code using the Minimax m2.5 model.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"}
                    },
                    "required": ["task"]
                }
            },
            {
                "name": "nexus_vision",
                "description": "Capture screen and analyze with PC2 local vision model. Use this to 'see' ComfyUI or errors.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "What to look for in the screenshot."}
                    }
                }
            },
            {
                "name": "nexus_status",
                "description": "Get detailed health status of all nodes in the Nexus distributed system.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "tavily_search",
                "description": "Advanced web search using Tavily API for highly accurate and research-oriented results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "search_depth": {"type": "string", "enum": ["basic", "advanced"], "default": "basic"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "agent_blame",
                "description": "Analyze code history and identify the cause of specific issues or bugs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "line_number": {"type": "integer"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "whisper_transcribe",
                "description": "Transcribe audio files using OpenAI's Whisper model (local or cloud).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "audio_path": {"type": "string"}
                    },
                    "required": ["audio_path"]
                }
            }
        ]
    }

def call_nexus_chat(params):
    try:
        r = requests.post(f"{NEXUS_URL}/chat", json=params, timeout=120)
        return {"content": [{"type": "text", "text": r.json().get("response", "No response")}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def call_nexus_skill(params):
    try:
        r = requests.post(f"{NEXUS_URL}/skills/execute", json=params, timeout=120)
        return {"content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def call_opencode(params):
    node = params.get("node", "local")
    task = params.get("task")
    model = params.get("model", "minimax-m2.5")
    workspace = params.get("workspace", os.getcwd())
    
    if node == "pc2":
        pc2_ip = os.getenv("SUPER_NEXUS_PC2_IP", "")
        if not pc2_ip:
            return {"content": [{"type": "text", "text": "Remote node not configured. Set SUPER_NEXUS_PC2_IP in .env"}]}
        pc2_url = f"http://{pc2_ip}:9000/api/opencode/run"
        try:
            r = requests.post(pc2_url, json={
                "task": task,
                "model": model,
                "workspace": os.getenv("NEXUS_REMOTE_WORKSPACE", "/home/user/nexus_node/")
            }, timeout=300)
            if r.status_code == 200:
                res = r.json()
                output = f"--- [Remote OpenCode Output] ---\n{res.get('stdout', '')}\n{res.get('stderr', '')}"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Remote Error ({r.status_code}): {r.text}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error connecting to remote node: {str(e)}"}]}

    # Default: Local execution
    if sys.platform == "win32":
        cli = os.getenv("OPENCODE_CLI", "opencode")
    else:
        cli = "opencode"
    
    cmd = [cli, "run", task, "--model", model, "--dir", workspace, "--dangerously-skip-permissions"]
    try:
        import subprocess
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        output = result.stdout if result.returncode == 0 else result.stderr
        if not output and result.stderr:
            output = result.stderr
        return {"content": [{"type": "text", "text": output or "Task completed with no output."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

def call_pc2_chat(params):
    pc2_ip = os.getenv("SUPER_NEXUS_PC2_IP", "")
    if not pc2_ip:
        return {"content": [{"type": "text", "text": "Remote node not configured. Set SUPER_NEXUS_PC2_IP in .env"}]}
    pc2_url = f"http://{pc2_ip}:9000/api/chat"
    try:
        r = requests.post(pc2_url, json=params, timeout=120)
        if r.status_code == 200:
            try:
                return {"content": [{"type": "text", "text": r.json().get("response", "No response from remote node")}]}
            except:
                return {"content": [{"type": "text", "text": f"Remote returned non-JSON response: {r.text[:500]}"}]}
        return {"content": [{"type": "text", "text": f"Remote Error ({r.status_code}): {r.text[:200]}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error connecting to remote node: {str(e)}"}]}

def call_pc2_minimax(params):
    pc2_ip = os.getenv("SUPER_NEXUS_PC2_IP", "")
    if not pc2_ip:
        return {"content": [{"type": "text", "text": "Remote node not configured. Set SUPER_NEXUS_PC2_IP in .env"}]}
    pc2_url = f"http://{pc2_ip}:9000/api/chat"
    payload = {
        "prompt": params.get("task"),
        "engine": "auto", 
        "gem": "developer"
    }
    try:
        r = requests.post(pc2_url, json=payload, timeout=120)
        if r.status_code == 200:
            try:
                return {"content": [{"type": "text", "text": r.json().get("response", "No response from PC2 Minimax")}]}
            except:
                return {"content": [{"type": "text", "text": f"PC2 returned non-JSON response: {r.text[:500]}"}]}
        return {"content": [{"type": "text", "text": f"PC2 Error ({r.status_code}): {r.text[:200]}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error connecting to PC2: {str(e)}"}]}

def call_nexus_vision(params):
    prompt = params.get("prompt", "Describe what you see on the screen.")
    try:
        # We call the local vision skill which we've already redirected to PC2
        skill_payload = {
            "skill": "screen_capture",
            "method": "capture_and_analyze",
            "params": {"prompt": prompt}
        }
        r = requests.post(f"{NEXUS_URL}/skills/execute", json=skill_payload, timeout=120)
        return {"content": [{"type": "text", "text": json.dumps(r.json(), indent=2)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error in Vision Bridge: {str(e)}"}]}

def call_nexus_status():
    status = {}
    # Check Local
    try:
        r = requests.get("http://localhost:9000/health", timeout=5)
        status["local"] = r.json()
    except:
        status["local"] = {"status": "offline"}
    
    # Check Remote
    try:
        pc2_ip = os.getenv("SUPER_NEXUS_PC2_IP", "")
        if pc2_ip:
            r = requests.get(f"http://{pc2_ip}:9000/health", timeout=5)
            status["remote"] = r.json()
        else:
            status["remote"] = {"status": "not configured"}
    except:
        status["remote"] = {"status": "offline"}
        
    return {"content": [{"type": "text", "text": json.dumps(status, indent=2)}]}

def call_tavily_search(params):
    # Usar el backend de Nexus que ya tiene integrados los skills de búsqueda
    return call_nexus_skill({"skill": "tavily-web", "method": "search", "params": params})

def call_agent_blame(params):
    # Skill de análisis de código de ClawHub
    return call_nexus_skill({"skill": "agent-blame", "method": "analyze", "params": params})

def call_whisper_transcribe(params):
    # Skill de audio/voz
    return call_nexus_skill({"skill": "whisper", "method": "transcribe", "params": params})

def main():
    logging.info("Nexus IA MCP Server started")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            logging.debug(f"Received: {line.strip()}")
            request = json.loads(line)
            req_id = request.get("id")
            method = request.get("method")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True}
                        },
                        "serverInfo": {
                            "name": "nexus-ia",
                            "version": "1.0.1"
                        }
                    }
                }
            elif method == "notifications/initialized" or method == "initialized":
                logging.info("Client acknowledged initialization")
                continue
            elif method == "tools/list" or method == "listTools":
                response = {"jsonrpc": "2.0", "id": req_id, "result": get_tools()}
            elif method == "tools/call" or method == "callTool":
                tool_name = request["params"]["name"]
                tool_params = request["params"].get("arguments", {})
                
                logging.info(f"Calling tool: {tool_name}")
                if tool_name == "nexus_chat":
                    result = call_nexus_chat(tool_params)
                elif tool_name == "nexus_skill":
                    result = call_nexus_skill(tool_params)
                elif tool_name == "opencode_task":
                    result = call_opencode(tool_params)
                elif tool_name == "pc2_chat":
                    result = call_pc2_chat(tool_params)
                elif tool_name == "pc2_minimax":
                    result = call_pc2_minimax(tool_params)
                elif tool_name == "nexus_vision":
                    result = call_nexus_vision(tool_params)
                elif tool_name == "nexus_status":
                    result = call_nexus_status()
                elif tool_name == "tavily_search":
                    result = call_tavily_search(tool_params)
                elif tool_name == "agent_blame":
                    result = call_agent_blame(tool_params)
                elif tool_name == "whisper_transcribe":
                    result = call_whisper_transcribe(tool_params)
                else:
                    result = {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}
                
                response = {"jsonrpc": "2.0", "id": req_id, "result": result}
            else:
                if req_id is not None:
                    response = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method {method} not found"}}
                else:
                    continue
            
            output = json.dumps(response)
            logging.debug(f"Sending: {output}")
            sys.stdout.write(output + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            # No rompemos el bucle para mantener el servidor vivo
            continue

if __name__ == "__main__":
    main()
