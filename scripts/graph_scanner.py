"""扫描项目Python文件，提取import关系，生成vis.js可用的JSON图数据。

用法:
    python scripts/graph_scanner.py
    python scripts/graph_scanner.py --project D:\ias\proyectos\supernexus-v2 --output static/graph.json
"""

import ast
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 排除的目录
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".nexus", "node_modules", ".venv", "venv",
    "env", ".env", "dist", "build", ".mypy_cache", ".pytest_cache",
    "screenshots", "data", "static", "skills", "hub", "tests",
    "test", "examples", "docs", "doc", "migrations",
}
# 只扫描这些顶层目录
SCAN_DIRS = {"src", "scripts"}
# 排除的文件模式
EXCLUDE_FILES = {"__init__.py", "conftest.py"}

# 颜色方案（按目录层级）
LAYER_COLORS = {
    0: "#e74c3c",  # root - red
    1: "#3498db",  # src/ - blue
    2: "#2ecc71",  # src/core/ - green
    3: "#f39c12",  # src/core/xxx/ - orange
    4: "#9b59b6",  # deeper - purple
    5: "#1abc9c",  # deeper - teal
}


def get_layer_color(depth: int) -> str:
    """根据深度获取节点颜色。"""
    d = min(depth, max(LAYER_COLORS.keys()))
    return LAYER_COLORS.get(d, "#95a5a6")


def get_module_name(filepath: Path) -> str:
    """将文件路径转换为Python模块名。"""
    try:
        rel = filepath.relative_to(PROJECT_ROOT)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    except ValueError:
        return filepath.stem


# Python标准库模块（常见的）
_STDLIB_MODULES = {
    "abc", "aifc", "argparse", "ast", "asyncio", "atexit", "base64",
    "binascii", "bisect", "builtins", "calendar", "cgi", "cmath",
    "codecs", "collections", "colorsys", "compileall", "concurrent",
    "configparser", "contextlib", "contextvars", "copy", "copyreg",
    "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "email", "encodings", "enum", "errno", "faulthandler",
    "fcntl", "filecmp", "fileinput", "fnmatch", "fractions", "ftplib",
    "functools", "gc", "getopt", "getpass", "gettext", "glob", "gzip",
    "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
    "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "linecache", "locale", "logging", "lzma", "mailbox",
    "mimetypes", "mmap", "multiprocessing", "numbers", "operator",
    "optparse", "os", "pathlib", "pdb", "pickle", "pkgutil", "platform",
    "plistlib", "poplib", "posixpath", "pprint", "profile", "pstats",
    "py_compile", "pydoc", "queue", "quopri", "random", "re",
    "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil",
    "signal", "site", "smtplib", "sndhdr", "socket", "socketserver",
    "sqlite3", "ssl", "stat", "statistics", "string", "struct",
    "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "types", "typing", "unicodedata", "unittest", "urllib", "uuid",
    "venv", "warnings", "wave", "weakref", "webbrowser", "winreg",
    "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib",
    # common short names
    "_thread", "__future__", "_io", "_collections_abc",
}

# 第三方库（已知的）
_THIRD_PARTY = {
    "fastapi", "uvicorn", "pydantic", "httpx", "aiohttp", "requests",
    "flask", "django", "starlette", "websocket", "websockets",
    "torch", "tensorflow", "numpy", "pandas", "scipy", "sklearn",
    "transformers", "sentence_transformers", "sentencepiece",
    "dotenv", "click", "typer", "rich", "colorama", "tabulate",
    "jinja2", "mako", "yaml", "toml", "tomli",
    "git", "github", "ghapi",
    "pytest", "unittest", "coverage", "tox",
    "celery", "redis", "rabbitmq", "kafka",
    "docker", "kubernetes", "boto3", "azure",
    "sqlalchemy", "alembic", "peewee", "tortoise",
    "pillow", "opencv", "pygame", "pyglet",
    "ddgs", "duckduckgo_search", "bs4", "beautifulsoup4",
    "lxml", "html5lib", "cssselect",
    "matplotlib", "plotly", "seaborn", "bokeh",
    "scrapy", "selenium", "playwright",
    "paramiko", "fabric", "invoke",
    "pymongo", "elasticsearch", "meilisearch",
    "jwt", "passlib", "bcrypt", "cryptography",
    "loguru", "structlog", "colorlog",
    "aiosqlite", "databases", "asyncpg", "aiomysql",
    "marshmallow", "cerberus", "voluptuous",
    "xmltodict", "python_dateutil", "pytz", "dateparser",
    "fpdf", "reportlab", "weasyprint", "pdfminer",
    "markdown", "mistune", "commonmark",
    "pypdf", "pikepdf", "fitz",
    "openai", "anthropic", "groq", "together",
    "sentence_transformers", "chromadb", "faiss",
    "networkx", "graphviz", "pydot",
    "sympy", "networkx",
    "sentry_sdk", "bugsnag", "rollbar",
    "newrelic", "datadog", "prometheus_client",
    "watchdog", "inotify", "watchfiles",
    "httpcore", "h11", "h2", "hpack",
    "certifi", "urllib3", "chardet", "idna",
    "cffi", "pycparser",
    "greenlet", "gevent", "eventlet",
    "msgpack", "orjson", "ujson", "simplejson",
    "pyyaml", "ruamel.yaml",
    "python_multipart", "python_jose", "python_dotenv",
    "gunicorn", "hypercorn", "daphne",
    "typer", "rich", "textual", "urwid",
    "blessed", "curses",
}


def extract_imports(filepath: Path) -> dict:
    """从Python文件中提取import信息。"""
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return {"imports": [], "from_imports": [], "classes": [], "functions": [], "executes": [], "dynamic_imports": [], "file_refs": []}

    imports = []
    from_imports = []
    classes = []
    functions = []
    executes = []  # subprocess.run(["python", "scripts/xxx.py"]) 等
    dynamic_imports = []  # importlib.import_module("src.core.xxx")
    file_refs = []  # Path("src/core/xxx.py"), open("data/xxx")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                from_imports.append(node.module)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        # Detect subprocess.run(["python", "file.py"]) or os.system("python file.py")
        elif isinstance(node, ast.Call):
            exec_file = _detect_exec_call(node)
            if exec_file:
                executes.append(exec_file)
            # Detect dynamic imports: importlib.import_module("src.core.xxx")
            dyn = _detect_dynamic_import(node)
            if dyn:
                dynamic_imports.append(dyn)
            # Detect file references: Path("src/core/xxx.py"), open("data/xxx")
            refs = _detect_file_refs(node)
            file_refs.extend(refs)
        # Detect __import__("src.core.xxx")
        elif isinstance(node, ast.Assign):
            dyn = _detect_import_assign(node)
            if dyn:
                dynamic_imports.append(dyn)

    return {
        "imports": imports,
        "from_imports": from_imports,
        "classes": classes,
        "functions": functions,
        "executes": executes,
        "dynamic_imports": dynamic_imports,
        "file_refs": file_refs,
    }


def _detect_exec_call(node) -> str | None:
    """检测 subprocess.run(["python", "file.py"]) 等调用。"""
    func = node.func
    # subprocess.run / subprocess.Popen / os.system
    if isinstance(func, ast.Attribute) and func.attr in ("run", "Popen", "system", "call"):
        args = node.args
        if args:
            first = args[0]
            # subprocess.run(["python", "scripts/xxx.py"])
            if isinstance(first, ast.List) and len(first.elts) >= 2:
                second = first.elts[1]
                if isinstance(second, ast.Constant) and isinstance(second.value, str):
                    val = second.value
                    if val.endswith(".py") or "/" in val or "\\" in val:
                        return val
            # os.system("python scripts/xxx.py")
            elif isinstance(first, ast.Constant) and isinstance(first.value, str):
                val = first.value
                if ".py" in val:
                    # extract filename
                    for part in val.split():
                        if part.endswith(".py"):
                            return part
    return None


def _detect_dynamic_import(node) -> str | None:
    """检测 importlib.import_module("src.core.xxx") 或 __import__("src.core.xxx")。"""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "import_module":
        args = node.args
        if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
            return args[0].value
    elif isinstance(func, ast.Name) and func.id == "__import__":
        args = node.args
        if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
            return args[0].value
    return None


def _detect_import_assign(node) -> str | None:
    """检测 xxx = importlib.import_module("src.core.xxx")。"""
    if isinstance(node.value, ast.Call):
        func = node.value.func
        if isinstance(func, ast.Attribute) and func.attr == "import_module":
            args = node.value.args
            if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                return args[0].value
    return None


def _detect_file_refs(node) -> list:
    """检测 Path("src/core/xxx.py") 或 open("data/xxx") 中的文件引用。"""
    refs = []
    func = node.func
    func_name = ""
    if isinstance(func, ast.Name):
        func_name = func.id
    elif isinstance(func, ast.Attribute):
        func_name = func.attr

    if func_name in ("open", "Path", "PurePath"):
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                val = arg.value
                # Only include project-internal paths
                if (val.startswith("src/") or val.startswith("scripts/") or
                    val.startswith("data/") or val.startswith("static/") or
                    val.endswith(".py")):
                    refs.append(val)
    return refs


def _resolve_script_path(path_str: str, all_modules: dict) -> str | None:
    """Resolve a script path like 'scripts/xxx.py' to a module name."""
    # Normalize separators
    path_str = path_str.replace("\\", "/")
    # Strip .py extension
    if path_str.endswith(".py"):
        path_str = path_str[:-3]
    # Convert to module format
    mod = path_str.replace("/", ".")
    # Try direct match
    if mod in all_modules:
        return mod
    # Try with scripts. prefix
    if f"scripts.{mod}" in all_modules:
        return f"scripts.{mod}"
    # Try parent module
    parts = mod.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in all_modules:
            return candidate
    return None


def resolve_import_to_file(module_name: str, all_modules: dict) -> str | None:
    """尝试将import名称解析为项目内的文件路径。
    
    Python import解析规则:
      import foo.bar  -> foo.bar 或 foo (package __init__)
      from foo import bar -> foo.bar 或 foo (package __init__)
    """
    # 直接匹配模块名
    if module_name in all_modules:
        return module_name
    
    # 尝试作为包的 __init__.py
    pkg_init = f"{module_name}.__init__"
    if pkg_init in all_modules:
        return pkg_init
    
    # 尝试父模块（import src.core.xxx -> src.core 或 src）
    parts = module_name.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in all_modules:
            return candidate
        pkg = candidate + ".__init__"
        if pkg in all_modules:
            return pkg
    
    return None


def scan_project(project_root: Path) -> dict:
    """扫描项目，构建图数据。"""
    all_modules = {}  # module_name -> filepath
    file_info = {}    # module_name -> import info

    # 第一遍：收集所有Python文件（只扫描指定目录）
    py_files = []
    for scan_dir in SCAN_DIRS:
        dir_path = project_root / scan_dir
        if dir_path.exists():
            py_files.extend(dir_path.rglob("*.py"))

    for pyfile in py_files:
        # 排除不需要的目录
        parts = pyfile.relative_to(project_root).parts
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        if pyfile.name in EXCLUDE_FILES:
            continue
        # 跳过太深的文件
        if len(parts) > 6:
            continue

        mod_name = get_module_name(pyfile)
        all_modules[mod_name] = pyfile
        file_info[mod_name] = extract_imports(pyfile)

    # 构建图数据
    nodes = []
    edges = []
    node_ids = set()

    # 添加节点
    for mod_name, pyfile in all_modules.items():
        rel = pyfile.relative_to(project_root)
        depth = len(rel.parts) - 1
        info = file_info[mod_name]

        # 统计
        edge_count = 0  # 将在下面计算

        node = {
            "id": mod_name,
            "label": pyfile.stem,
            "title": f"{rel}\nClasses: {len(info['classes'])}\nFunctions: {len(info['functions'])}\nImports: {len(info['imports']) + len(info['from_imports'])}",
            "group": str(depth),
            "color": get_layer_color(depth),
            "size": 10 + len(info["classes"]) * 3 + len(info["functions"]) * 2,
            "font": {"size": max(8, 14 - depth)},
            "file": str(rel),
            "classes": info["classes"],
            "functions": info["functions"],
            "import_count": len(info["imports"]) + len(info["from_imports"]),
        }
        nodes.append(node)
        node_ids.add(mod_name)

    # 添加边（import关系）
    edge_set = set()
    for mod_name, info in file_info.items():
        all_imports = set(info["imports"] + info["from_imports"])

        for imp in all_imports:
            # 跳过标准库和第三方库
            top = imp.split(".")[0]
            if top in _STDLIB_MODULES or top in _THIRD_PARTY:
                continue
            target = resolve_import_to_file(imp, all_modules)
            if target and target != mod_name:
                edge_key = (mod_name, target)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "from": mod_name,
                        "to": target,
                        "arrows": "to",
                        "color": {"color": "#888", "highlight": "#e74c3c"},
                        "width": 1,
                    })

        # Dynamic imports: importlib.import_module("src.core.xxx")
        for dyn in info.get("dynamic_imports", []):
            if dyn.startswith("src.") or dyn.startswith("scripts."):
                target = resolve_import_to_file(dyn, all_modules)
                if target and target != mod_name:
                    edge_key = (mod_name, target)
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "from": mod_name,
                            "to": target,
                            "arrows": "to",
                            "color": {"color": "#e67e22", "highlight": "#e74c3c"},
                            "width": 2,
                            "dashes": True,
                            "label": "dynamic",
                        })

        # Subprocess calls
        for exe in info.get("executes", []):
            # Try to resolve script path
            exe_mod = _resolve_script_path(exe, all_modules)
            if exe_mod and exe_mod != mod_name:
                edge_key = (mod_name, exe_mod)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "from": mod_name,
                        "to": exe_mod,
                        "arrows": "to",
                        "color": {"color": "#9b59b6", "highlight": "#e74c3c"},
                        "width": 2,
                        "dashes": True,
                        "label": "subprocess",
                    })

        # File references
        for ref in info.get("file_refs", []):
            ref_mod = _resolve_script_path(ref, all_modules)
            if ref_mod and ref_mod != mod_name:
                edge_key = (mod_name, ref_mod)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "from": mod_name,
                        "to": ref_mod,
                        "arrows": "to",
                        "color": {"color": "#1abc9c", "highlight": "#e74c3c"},
                        "width": 1,
                        "dashes": True,
                        "label": "file ref",
                    })

    # 更新节点的连接数
    conn_count = defaultdict(int)
    for e in edges:
        conn_count[e["from"]] += 1
        conn_count[e["to"]] += 1

    for node in nodes:
        c = conn_count.get(node["id"], 0)
        node["size"] = max(8, 10 + c * 2)
        node["title"] += f"\nConnections: {c}"

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_files": len(nodes),
            "total_edges": len(edges),
            "total_classes": sum(len(n["classes"]) for n in nodes),
            "total_functions": sum(len(n["functions"]) for n in nodes),
        },
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scan project and generate graph JSON")
    parser.add_argument("--project", default=str(PROJECT_ROOT), help="Project root")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "static" / "graph.json"), help="Output JSON")
    args = parser.parse_args()

    project = Path(args.project)
    output = Path(args.output)

    print(f"Scanning {project}...")
    data = scan_project(project)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Done! {data['stats']['total_files']} files, {data['stats']['total_edges']} edges")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
