"""Tests para los 4 workers estándar: AyudaGem, ScholarGem, SageGem, BibliotecaGem."""
import asyncio
from pathlib import Path

from gemas_core.workers.ayuda import AyudaGem
from gemas_core.workers.scholar import ScholarGem
from gemas_core.workers.sage import SageGem
from gemas_core.workers.biblioteca import BibliotecaGem


# ============================================================
# AyudaGem
# ============================================================

def test_ayuda_instantiation(tmp_path: Path):
    g = AyudaGem(data_dir=tmp_path / "profiles")
    assert g.profile["user_level"] == "novice"
    assert g.profile["sessions"] == 0
    assert g.profile_file.exists()


def test_ayuda_analyze_intent_help():
    g = AyudaGem()
    intent = asyncio.run(g.analyze_intent("que puedes hacer?"))
    assert intent["is_help_request"] is True
    assert intent["user_level"] == "novice"


def test_ayuda_analyze_intent_feature_mention():
    g = AyudaGem()
    intent = asyncio.run(g.analyze_intent("necesito un code review y un tester"))
    assert "code" in intent["features_mentioned"]
    assert "tester" in intent["features_mentioned"]


def test_ayuda_level_escalation():
    g = AyudaGem()
    # Simulate many features used
    g.profile["features_used"] = [f"feat_{i}" for i in range(10)]
    g._auto_escalate_level()
    assert g.profile["user_level"] == "intermediate"
    g.profile["features_used"] = [f"feat_{i}" for i in range(20)]
    g._auto_escalate_level()
    assert g.profile["user_level"] == "advanced"


def test_ayuda_full_catalog_default():
    g = AyudaGem()
    catalog = asyncio.run(g.full_catalog())
    assert catalog["llm_role_count"] == 18  # v1.1.0: prompter moved to dedicated
    assert len(catalog["llm_dedicated"]) == 6  # v1.6.0: +1 web_research
    assert "client_operatives" not in catalog
    assert catalog["total"] == 24  # 6 dedicated + 18 role-LLM


def test_ayuda_full_catalog_with_client_gemas():
    g = AyudaGem()
    client = [
        {"id": "rcon_commander", "name": "RCON", "description": "RCON ops",
         "category": "server_control"},
        {"id": "discord", "name": "Discord", "description": "Discord ops",
         "category": "discord"},
    ]
    catalog = asyncio.run(g.full_catalog(client_gemas=client))
    assert "client_operatives" in catalog
    assert len(catalog["client_operatives"]) == 2
    assert catalog["total"] == 26  # 24 + 2 (v1.6.0: 6 dedicated + 18 role)


def test_ayuda_execute():
    g = AyudaGem()
    result = asyncio.run(g.execute("hola"))
    assert result["success"] is True
    assert "intent" in result
    assert "profile" in result


def test_ayuda_reset_profile(tmp_path: Path):
    g = AyudaGem(data_dir=tmp_path / "p")
    g.profile["sessions"] = 100
    result = asyncio.run(g.reset_profile())
    assert result["success"] is True
    assert g.profile["sessions"] == 0
    assert g.profile["user_level"] == "novice"


def test_ayuda_to_dict():
    g = AyudaGem()
    d = g.to_dict()
    assert d["id"] == "ayuda"
    assert d["type"] == "dedicated"


# ============================================================
# ScholarGem
# ============================================================

def test_scholar_instantiation():
    g = ScholarGem()
    assert g.search_history == []


def test_scholar_to_dict():
    g = ScholarGem()
    d = g.to_dict()
    assert d["id"] == "scholar"
    assert "http_fallback" in d["backends"]


def test_scholar_execute_dispatches_to_research():
    g = ScholarGem()
    result = asyncio.run(g.execute("test query"))
    assert result["query"] == "test query"
    assert "timestamp" in result


def test_scholar_parse_ddg_html():
    html = """
    <html><body>
    <a class="result__a" href="https://example.com">Example Title</a>
    <a class="result__a" href="https://test.com">Test Title</a>
    </body></html>
    """
    sources = ScholarGem._parse_ddg_html(html, max_sources=5)
    assert len(sources) == 2
    assert sources[0]["url"] == "https://example.com"
    assert sources[0]["title"] == "Example Title"


def test_scholar_extract_text():
    html = "<html><body><script>var x=1;</script><p>Hello <b>world</b></p></body></html>"
    text = ScholarGem._extract_text(html)
    assert "Hello" in text
    assert "world" in text
    assert "var x" not in text


# ============================================================
# SageGem
# ============================================================

def test_sage_instantiation(tmp_path: Path):
    db = tmp_path / "sage.db"
    g = SageGem(db_path=db)
    assert db.exists()


def test_sage_remember_and_recall(tmp_path: Path):
    g = SageGem(db_path=tmp_path / "sage.db")
    r1 = asyncio.run(g.remember("test observation 1", category="test"))
    assert r1["success"] is True
    r2 = asyncio.run(g.remember("another observation", category="general"))
    assert r2["success"] is True

    results = asyncio.run(g.recall("observation"))
    assert len(results) == 2


def test_sage_recall_with_category_filter(tmp_path: Path):
    g = SageGem(db_path=tmp_path / "sage.db")
    asyncio.run(g.remember("foo", category="A"))
    asyncio.run(g.remember("foo", category="B"))

    results = asyncio.run(g.recall("foo", category="A"))
    assert len(results) == 1
    assert results[0]["category"] == "A"


def test_sage_empty_content():
    g = SageGem(db_path=Path("/tmp/sage_test_empty.db"))
    r = asyncio.run(g.remember(""))
    assert r["success"] is False


def test_sage_execute_remember():
    g = SageGem(db_path=Path("/tmp/sage_test_exec.db"))
    if g.db_path.exists():
        g.db_path.unlink()
    g._init_db()
    result = asyncio.run(g.execute("just a thought"))
    assert result["action"] == "remember"
    assert result["success"] is True


def test_sage_execute_recall():
    g = SageGem(db_path=Path("/tmp/sage_test_exec2.db"))
    if g.db_path.exists():
        g.db_path.unlink()
    g._init_db()
    asyncio.run(g.remember("important thing"))
    result = asyncio.run(g.execute("recall: important"))
    assert result["action"] == "recall"
    assert result["count"] >= 1


# ============================================================
# BibliotecaGem
# ============================================================

def test_biblioteca_instantiation(tmp_path: Path):
    g = BibliotecaGem(db_path=tmp_path / "bib.db")
    assert g.db_path.exists()


def test_biblioteca_index_and_search(tmp_path: Path):
    g = BibliotecaGem(db_path=tmp_path / "bib.db")
    r = asyncio.run(g.index("https://example.com", title="Example",
                            category="docs", tags=["test", "url"]))
    assert r["success"] is True

    results = asyncio.run(g.search("example"))
    assert len(results) >= 1
    assert "test" in results[0]["tags"]


def test_biblioteca_list_categories(tmp_path: Path):
    g = BibliotecaGem(db_path=tmp_path / "bib.db")
    asyncio.run(g.index("source1", category="A"))
    asyncio.run(g.index("source2", category="A"))
    asyncio.run(g.index("source3", category="B"))

    cats = g.list_categories()
    assert {"category": "A", "count": 2} in cats
    assert {"category": "B", "count": 1} in cats


def test_biblioteca_execute_dispatch(tmp_path: Path):
    g = BibliotecaGem(db_path=tmp_path / "bib.db")
    # index
    r = asyncio.run(g.execute("index: file.txt"))
    assert r["action"] == "index"
    # search
    r = asyncio.run(g.execute("search: file"))
    assert r["action"] == "search"
    # categorias
    r = asyncio.run(g.execute("categorias"))
    assert r["action"] == "list_categories"


def test_biblioteca_execute_invalid():
    g = BibliotecaGem(db_path=Path("/tmp/bib_invalid.db"))
    if g.db_path.exists():
        g.db_path.unlink()
    g._init_db()
    r = asyncio.run(g.execute("nada"))
    assert r["success"] is False
    assert "use prefix" in r["error"]
