import pytest
import tempfile
import json
from pathlib import Path
from src.core.skill_marketplace import SkillManifest, SkillRegistry, SkillVersion


def test_manifest_creation():
    m = SkillManifest(name="test-skill", version="1.2.3", author="opencode",
                      tags=["code", "refactor"], description="A test skill")
    assert m.name == "test-skill"
    assert m.version == "1.2.3"
    assert m.author == "opencode"
    assert "code" in m.tags


def test_register_skill():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = SkillRegistry(storage_path=str(Path(tmpdir) / "registry.json"))
        m = SkillManifest(name="my-skill", tags=["data"], description="Data analysis skill")
        reg.register(m)
        assert reg.get("my-skill") is not None


def test_search_by_tag():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = SkillRegistry(storage_path=str(Path(tmpdir) / "registry.json"))
        reg.register(SkillManifest(name="skill-a", tags=["code", "python"]))
        reg.register(SkillManifest(name="skill-b", tags=["data", "python"]))
        reg.register(SkillManifest(name="skill-c", tags=["devops"]))
        code_skills = reg.search_by_tag("code")
        assert len(code_skills) == 1
        assert code_skills[0].name == "skill-a"
        python_skills = reg.search_by_tag("python")
        assert len(python_skills) == 2


def test_search_by_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = SkillRegistry(storage_path=str(Path(tmpdir) / "registry.json"))
        reg.register(SkillManifest(name="database-optimizer", tags=["db"], description="Optimize SQL queries"))
        reg.register(SkillManifest(name="docker-deployer", tags=["docker"], description="Deploy with Docker"))
        results = reg.search("database")
        assert len(results) >= 1
        assert results[0].name == "database-optimizer"


def test_install_skill():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = SkillRegistry(storage_path=str(Path(tmpdir) / "registry.json"))
        skill_dir = Path(tmpdir) / "src_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill")
        m = SkillManifest(name="installable-skill", install_path=str(skill_dir))
        reg.register(m)

        import src.core.skill_marketplace as sm
        original = sm.SKILLS_INSTALL_DIR
        sm.SKILLS_INSTALL_DIR = Path(tmpdir) / "installed_skills"
        try:
            result = reg.install("installable-skill")
            assert result is True
            assert (sm.SKILLS_INSTALL_DIR / "installable-skill" / "SKILL.md").exists()
        finally:
            sm.SKILLS_INSTALL_DIR = original


def test_version_comparison():
    v1 = SkillVersion.parse("1.0.0")
    v2 = SkillVersion.parse("2.0.0")
    v3 = SkillVersion.parse("1.5.0")
    v4 = SkillVersion.parse("1.0.0")

    assert v1 < v2
    assert v1 < v3
    assert v3 < v2
    assert v1 == v4
    assert v2 > v3
    assert str(v1) == "1.0.0"


def test_rating_update():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = SkillRegistry(storage_path=str(Path(tmpdir) / "registry.json"))
        m = SkillManifest(name="rateable-skill")
        reg.register(m)
        reg.update_rating("rateable-skill", 4.0)
        reg.update_rating("rateable-skill", 5.0)
        updated = reg.get("rateable-skill")
        assert updated.rating_count == 2
        assert updated.rating == pytest.approx(4.5)


def test_list_by_rating():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = SkillRegistry(storage_path=str(Path(tmpdir) / "registry.json"))
        reg.register(SkillManifest(name="low", rating=1.0, rating_count=1))
        reg.register(SkillManifest(name="high", rating=5.0, rating_count=1))
        reg.register(SkillManifest(name="mid", rating=3.0, rating_count=1))
        top = reg.list_by_rating(top_k=2)
        assert len(top) == 2
        assert top[0].name == "high"
        assert top[1].name == "mid"
