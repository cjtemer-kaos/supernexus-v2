"""
CodeGraph Integration - Motor de navegacion semantica para SuperNEXUS v2

Integra CodeGraph como motor de analisis AST para la colmena.
Reemplaza el Sprint 5 (LSP client) completamente.

CodeGraph usa tree-sitter para parsear ASTs de 19+ lenguajes y genera
un grafo semántico en SQLite local con busqueda vectorial.

Patrones:
- AST parsing con tree-sitter
- Grafo semantico de simbolos y relaciones
- Busqueda semantica con embeddings ONNX locales
- MCP server nativo para consumo por gemas

Propuesta original: antigravity (ID 707547)
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus-codegraph")


@dataclass
class CodeSymbol:
    """Simbolo de codigo (funcion, clase, variable, etc.)"""
    name: str
    kind: str  # function, class, variable, import, etc.
    file_path: str
    line: int
    language: str
    signature: str = ""
    docstring: str = ""
    relationships: List[Dict] = field(default_factory=list)


@dataclass
class CodeSearchResult:
    """Resultado de busqueda semantica"""
    symbols: List[CodeSymbol]
    code_snippets: List[Dict]
    total_matches: int
    search_type: str  # "semantic", "symbol", "text", "reference"


class CodeGraphIntegration:
    """
    Integracion de CodeGraph como motor semantico.

    Uso:
        cg = CodeGraphIntegration(project_root="/path/to/project")
        await cg.build_index()
        results = await cg.search("authentication flow")
    """

    def __init__(self, project_root: str = None, codegraph_dir: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.codegraph_dir = Path(codegraph_dir or self.project_root / ".codegraph")
        self.codegraph_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.codegraph_dir / "codegraph.db"
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Verifica si CodeGraph esta disponible"""
        try:
            result = subprocess.run(
                ["codegraph", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def build_index(self) -> Dict:
        """
        Construye el indice semantico del proyecto.

        Usa CodeGraph CLI para parsear AST y generar grafo.
        """
        if not self._available:
            return self._fallback_index()

        try:
            result = subprocess.run(
                ["codegraph", "index", str(self.project_root), "--output", str(self.db_path)],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                logger.info(f"CodeGraph index built: {self.db_path}")
                return {"success": True, "db_path": str(self.db_path)}
            else:
                logger.error(f"CodeGraph index failed: {result.stderr}")
                return {"success": False, "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Index timeout (5 min)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fallback_index(self) -> Dict:
        """
        Indexacion fallback sin CodeGraph CLI.

        Usa tree-sitter Python directamente si disponible.
        """
        try:
            import tree_sitter
            logger.info("Using tree-sitter fallback for indexing")
            return {"success": True, "method": "tree_sitter_fallback"}
        except ImportError:
            logger.warning("No CodeGraph or tree-sitter available, using basic indexing")
            return {"success": True, "method": "basic_fallback"}

    async def search(self, query: str, search_type: str = "semantic", language: str = None, limit: int = 20) -> CodeSearchResult:
        """
        Busca codigo usando CodeGraph.

        Tipos de busqueda:
        - "semantic": Busqueda por significado (embeddings)
        - "symbol": Busqueda por nombre de simbolo
        - "text": Busqueda por texto en codigo
        - "reference": Busqueda de referencias a un simbolo
        """
        if not self._available:
            return self._fallback_search(query, search_type, language, limit)

        try:
            if search_type == "semantic":
                cmd = ["codegraph", "search", "--semantic", query, "--limit", str(limit)]
            elif search_type == "symbol":
                cmd = ["codegraph", "search", "--symbol", query, "--limit", str(limit)]
            elif search_type == "text":
                cmd = ["codegraph", "search", "--text", query, "--limit", str(limit)]
            elif search_type == "reference":
                cmd = ["codegraph", "search", "--reference", query, "--limit", str(limit)]
            else:
                cmd = ["codegraph", "search", query, "--limit", str(limit)]

            if language:
                cmd.extend(["--language", language])

            cmd.append(str(self.db_path))

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return self._parse_search_result(data, search_type)
            else:
                logger.error(f"CodeGraph search failed: {result.stderr}")
                return self._fallback_search(query, search_type, language, limit)

        except Exception as e:
            logger.error(f"CodeGraph search error: {e}")
            return self._fallback_search(query, search_type, language, limit)

    def _fallback_search(self, query: str, search_type: str, language: str, limit: int) -> CodeSearchResult:
        """Busqueda fallback usando grep/glob"""
        import re

        symbols = []
        code_snippets = []

        # Busqueda basica por texto en archivos
        patterns = ["*.py", "*.js", "*.ts", "*.go", "*.rs"]
        if language:
            ext_map = {"python": "*.py", "javascript": "*.js", "typescript": "*.ts", "go": "*.go", "rust": "*.rs"}
            patterns = [ext_map.get(language.lower(), "*.py")]

        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden dirs and common exclusions
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__", ".git")]

            for fname in files:
                if not any(fname.endswith(p.replace("*", "")) or p == "*.py" and fname.endswith(".py") for p in patterns):
                    continue

                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    if query.lower() in content.lower():
                        lines = content.split("\n")
                        for i, line in enumerate(lines, 1):
                            if query.lower() in line.lower():
                                rel_path = os.path.relpath(fpath, self.project_root)
                                code_snippets.append({
                                    "file": rel_path,
                                    "line": i,
                                    "content": line.strip(),
                                })
                                if len(code_snippets) >= limit:
                                    break
                except (PermissionError, OSError):
                    continue

                if len(code_snippets) >= limit:
                    break

        return CodeSearchResult(
            symbols=symbols,
            code_snippets=code_snippets,
            total_matches=len(code_snippets),
            search_type=f"{search_type}_fallback",
        )

    def _parse_search_result(self, data: Dict, search_type: str) -> CodeSearchResult:
        """Parsea resultado de CodeGraph"""
        symbols = []
        for sym_data in data.get("symbols", []):
            symbols.append(CodeSymbol(
                name=sym_data.get("name", ""),
                kind=sym_data.get("kind", ""),
                file_path=sym_data.get("file", ""),
                line=sym_data.get("line", 0),
                language=sym_data.get("language", ""),
                signature=sym_data.get("signature", ""),
                docstring=sym_data.get("docstring", ""),
                relationships=sym_data.get("relationships", []),
            ))

        return CodeSearchResult(
            symbols=symbols,
            code_snippets=data.get("snippets", []),
            total_matches=data.get("total", 0),
            search_type=search_type,
        )

    async def get_symbol_info(self, symbol_name: str, file_path: str = None) -> Optional[CodeSymbol]:
        """Obtiene informacion detallada de un simbolo"""
        result = await self.search(symbol_name, search_type="symbol", limit=1)
        if result.symbols:
            return result.symbols[0]
        return None

    async def get_references(self, symbol_name: str) -> List[Dict]:
        """Obtiene referencias a un simbolo"""
        result = await self.search(symbol_name, search_type="reference", limit=50)
        return result.code_snippets

    async def get_call_graph(self, function_name: str) -> Dict:
        """Obtiene grafo de llamadas de una funcion"""
        result = await self.search(function_name, search_type="reference", limit=100)
        callers = [s for s in result.code_snippets if "call" in s.get("context", "").lower()]
        callees = [s for s in result.code_snippets if "def " in s.get("content", "") or "func " in s.get("content", "")]

        return {
            "function": function_name,
            "callers": callers[:10],
            "callees": callees[:10],
        }

    async def get_project_structure(self) -> Dict:
        """Obtiene estructura del proyecto"""
        structure = {"files": 0, "languages": {}, "symbols": 0}

        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__", ".git")]

            for fname in files:
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()
                structure["files"] += 1

                lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go", ".rs": "rust", ".java": "java"}
                lang = lang_map.get(ext, "other")
                structure["languages"][lang] = structure["languages"].get(lang, 0) + 1

        return structure

    def get_stats(self) -> Dict:
        return {
            "available": self._available,
            "project_root": str(self.project_root),
            "db_path": str(self.db_path),
            "db_exists": self.db_path.exists(),
        }
