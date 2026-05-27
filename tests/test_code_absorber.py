import pytest
import tempfile
from pathlib import Path
from src.core.code_absorber import CodeAbsorber, AbsorbedPattern, PatternExtractor


SAMPLE_PYTHON = """
class DataProcessor:
    def __init__(self, config):
        self.config = config

    async def process(self, data):
        result = await self._transform(data)
        return result

    def _transform(self, data):
        return [x * 2 for x in data]


def helper_function(param1, param2):
    return param1 + param2


def _private_util():
    pass
"""

SAMPLE_JS = """
class UserService {
    constructor(api) {
        this.api = api;
    }
    async getUser(id) {
        return await this.api.fetch(id);
    }
}

function formatDate(date) {
    return date.toISOString();
}
"""


def test_scan_repo_finds_python():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "src"
        src.mkdir()
        (src / "processor.py").write_text(SAMPLE_PYTHON)
        absorber = CodeAbsorber()
        patterns = absorber.scan_repo(str(src), repo_name="test-repo")
        assert len(patterns) > 0
        names = [p.name for p in patterns]
        assert "DataProcessor" in names
        assert "helper_function" in names


def test_extract_pattern_from_class():
    extractor = PatternExtractor()
    patterns = extractor.extract_from_python(SAMPLE_PYTHON)
    classes = [p for p in patterns if p["category"] == "class"]
    assert len(classes) >= 1
    assert classes[0]["name"] == "DataProcessor"


def test_extract_pattern_from_function():
    extractor = PatternExtractor()
    patterns = extractor.extract_from_python(SAMPLE_PYTHON)
    functions = [p for p in patterns if p["category"] == "function"]
    names = [p["name"] for p in functions]
    assert "process" in names  # public async method
    assert "helper_function" in names  # public function
    assert "_private_util" not in names  # private, skipped


def test_absorb_stores_in_memory():
    stored = []

    def brain_store(content):
        stored.append(content)

    absorber = CodeAbsorber(brain_store=brain_store)
    patterns = [
        AbsorbedPattern(name="TestPattern", category="class",
                       source_repo="test", code_snippet="class TestPattern: pass"),
    ]
    count = absorber.absorb(patterns)
    assert count == 1
    assert len(stored) == 1
    assert "TestPattern" in stored[0]


def test_quality_scoring():
    absorber = CodeAbsorber()
    # High quality: long, returns value, async
    high = absorber._score_quality("async def process(data):\n    result = await transform(data)\n    return result")
    assert high > 0.6
    # Low quality: very short
    low = absorber._score_quality("x = 1")
    assert low < 0.5


def test_absorber_status():
    absorber = CodeAbsorber()
    patterns = [
        AbsorbedPattern(name="A", category="class", source_repo="r", code_snippet="c"),
        AbsorbedPattern(name="B", category="function", source_repo="r", code_snippet="c"),
        AbsorbedPattern(name="C", category="class", source_repo="r", code_snippet="c"),
    ]
    absorber._patterns = patterns
    status = absorber.status()
    assert status["total_patterns"] == 3
    assert status["categories"]["class"] == 2
    assert status["categories"]["function"] == 1
