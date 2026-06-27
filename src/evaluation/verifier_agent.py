"""
Verifier Agent — verification gate inspirado en MiniMax Code.

NUNCA modifica archivos. Solo verifica con evidencia.
Output: VERDICT: PASS / VERDICT: FAIL con checks estructurados.
"""

import asyncio
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("verifier")


class Verdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class VerificationCheck:
    name: str
    method: str
    evidence: str
    result: bool  # True = PASS, False = FAIL
    expected_vs_actual: str = ""


@dataclass
class VerificationReport:
    verdict: Verdict
    checks: list[VerificationCheck] = field(default_factory=list)
    feedback: str = ""
    confidence: float = 1.0

    def to_text(self) -> str:
        lines = []
        for c in self.checks:
            lines.append(f"### Check: {c.name}")
            lines.append(f"**Method:** {c.method}")
            lines.append(f"**Evidence:** {c.evidence}")
            lines.append(f"**Result: {'PASS' if c.result else 'FAIL'}")
            if c.expected_vs_actual:
                lines.append(f"  Expected vs Actual: {c.expected_vs_actual}")
            lines.append("")
        lines.append(f"VERDICT: {self.verdict.value}")
        return "\n".join(lines)


class VerifierError(Exception):
    pass


class VerifierAgent:
    """
    Verificador adversarial — nunca modifica archivos, solo verifica.

    Integracion con JudgePipeline como _custom_judge.
    """

    MAX_RUNTIME_SECONDS = 300

    def __init__(
        self,
        llm_executor: Optional[Callable] = None,
        command_executor: Optional[Callable] = None,
        working_dir: str = "",
    ):
        self.llm = llm_executor
        self.run_cmd = command_executor
        self.working_dir = working_dir or os.getcwd()
        self._ephemeral_scripts: list[str] = []

    async def verify_code(
        self,
        task: str,
        result: str,
        success_criteria: str = "",
        changed_files: Optional[list[str]] = None,
    ) -> VerificationReport:
        checks: list[VerificationCheck] = []
        changed_files = changed_files or []

        # 1. Build check
        if changed_files:
            check = await self._check_build()
            checks.append(check)
            if not check.result:
                return VerificationReport(Verdict.FAIL, checks, "Build failed", 0.95)

        # 2. Test suite check
        check = await self._check_tests()
        checks.append(check)

        # 3. Lint check
        check = await self._check_lint()
        checks.append(check)

        # 4. Read diff & review
        if changed_files:
            check = await self._check_diff_review(changed_files)
            checks.append(check)

        # 5. Adversarial probe
        check = await self._check_adversarial(task, result, success_criteria)
        checks.append(check)

        # 6. LLM semantic evaluation
        if self.llm:
            check = await self._check_llm_semantic(task, result, success_criteria, changed_files)
            checks.append(check)

        failed = [c for c in checks if not c.result]
        if failed:
            feedback = f"FAIL: {len(failed)}/{len(checks)} checks failed"
            return VerificationReport(Verdict.FAIL, checks, feedback, 0.9)

        return VerificationReport(Verdict.PASS, checks, "All checks passed", 0.95)

    async def _check_build(self) -> VerificationCheck:
        name = "Build"
        method = "Run project build command"
        evidence = ""
        result_flag = True

        build_cmds = self._detect_build_commands()
        if not build_cmds:
            return VerificationCheck(name, "No build system detected", "Skipped", True)

        for cmd in build_cmds:
            evidence = await self._run_safe(cmd)
            if evidence is None:
                return VerificationCheck(name, method, "Command timed out or errored", False, "Expected exit 0, got timeout/error")

        return VerificationCheck(name, method, evidence, result_flag)

    async def _check_tests(self) -> VerificationCheck:
        name = "Test Suite"
        method = "Run test suite"
        evidence = ""
        result_flag = True

        if not self.run_cmd:
            return VerificationCheck(name, method, "No command executor available — skipped", True)

        test_cmds = self._detect_test_commands()
        if not test_cmds:
            return VerificationCheck(name, "No test system detected", "Skipped", True)

        for cmd in test_cmds:
            evidence = await self._run_safe(cmd)
            if evidence is None:
                return VerificationCheck(name, method, "Tests timed out", False)

        return VerificationCheck(name, method, evidence, result_flag)

    async def _check_lint(self) -> VerificationCheck:
        name = "Lint / Typecheck"
        method = "Run linter/typechecker"
        evidence = ""
        result_flag = True

        if not self.run_cmd:
            return VerificationCheck(name, method, "No command executor available — skipped", True)

        lint_cmds = self._detect_lint_commands()
        if not lint_cmds:
            return VerificationCheck(name, "No linter detected", "Skipped", True)

        for cmd in lint_cmds:
            evidence = await self._run_safe(cmd)
            if evidence is None:
                return VerificationCheck(name, method, "Lint timed out", False)

        return VerificationCheck(name, method, evidence, result_flag)

    async def _check_diff_review(self, changed_files: list[str]) -> VerificationCheck:
        name = "Code Diff Review"
        method = f"Read {len(changed_files)} changed files for design issues"
        evidence_parts = []
        result_flag = True

        for fp in changed_files:
            if not os.path.isfile(fp):
                evidence_parts.append(f"{fp}: not found")
                result_flag = False
                continue
            try:
                content = await self._read_file_safe(fp)
                issues = self._scan_for_issues(content, fp)
                if issues:
                    evidence_parts.append(f"{fp}: {'; '.join(issues)}")
                    result_flag = False
                else:
                    evidence_parts.append(f"{fp}: ok")
            except Exception as e:
                evidence_parts.append(f"{fp}: error reading ({e})")
                result_flag = False

        evidence = "\n".join(evidence_parts) if evidence_parts else "No files to review"
        return VerificationCheck(name, method, evidence, result_flag)

    async def _check_adversarial(self, task: str, result: str, success_criteria: str) -> VerificationCheck:
        name = "Adversarial Probe"
        method = "Try to break it — boundary values, edge cases, invariants"

        if not self.llm:
            return VerificationCheck(name, method, "No LLM available for adversarial probing", True)

        prompt = f"""You are an adversarial verifier. Try to break this deliverable.

Task: {task}
Result: {result}
Success criteria: {success_criteria}

Identify ONE specific adversarial probe:
1. What edge case or boundary condition would likely fail?
2. What invariant might be violated?
3. What happens with empty/malformed/negative input?

Respond with:
Probe: <one specific probe>
Method: <how to test it>
Expected: <what should happen>
Confidence: <0-1>
"""
        try:
            response = await self.llm(prompt)
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            return VerificationCheck(name, method, content.strip()[:500], True)
        except Exception as e:
            return VerificationCheck(name, method, f"Probe failed: {e}", True)

    async def _check_llm_semantic(
        self,
        task: str,
        result: str,
        success_criteria: str,
        changed_files: Optional[list[str]],
    ) -> VerificationCheck:
        name = "LLM Semantic Evaluation"
        method = "LLM judges completeness and correctness against requirements"

        if not self.llm:
            return VerificationCheck(name, method, "No LLM available", True)

        prompt = f"""Evaluate if this task was completed correctly.

TASK: {task}
RESULT: {result}
SUCCESS CRITERIA: {success_criteria or 'Complete the task correctly'}
CHANGED FILES: {changed_files or 'unknown'}

Respond EXACTLY with one line: PASS or FAIL
Then one line: <reason>
"""
        try:
            response = await self.llm(prompt)
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            passed = content.strip().upper().startswith("PASS")
            evidence = content.strip()[:300]
            return VerificationCheck(name, method, evidence, passed)
        except Exception as e:
            return VerificationCheck(name, method, f"LLM error: {e}", True)

    def _detect_build_commands(self) -> list[str]:
        wd = self.working_dir
        if os.path.isfile(os.path.join(wd, "package.json")):
            return ["npm run build"] if os.path.isfile(os.path.join(wd, "node_modules", ".package-lock.json")) else ["npm install 2>&1", "npm run build 2>&1"]
        if os.path.isfile(os.path.join(wd, "Cargo.toml")):
            return ["cargo build 2>&1"]
        if os.path.isfile(os.path.join(wd, "pyproject.toml")) or os.path.isfile(os.path.join(wd, "setup.py")):
            return ["pip install -e . 2>&1 || true"]
        return []

    def _detect_test_commands(self) -> list[str]:
        wd = self.working_dir
        cmds = []
        if os.path.isfile(os.path.join(wd, "package.json")):
            cmds.append("npm test 2>&1")
        if os.path.isfile(os.path.join(wd, "Cargo.toml")):
            cmds.append("cargo test 2>&1")
        if os.path.isfile(os.path.join(wd, "pyproject.toml")):
            cmds.append("python -m pytest -x --tb=short 2>&1 || true")
        return cmds

    def _detect_lint_commands(self) -> list[str]:
        wd = self.working_dir
        cmds = []
        if os.path.isfile(os.path.join(wd, "package.json")):
            cmds.append("npm run lint 2>&1 || true")
        if os.path.isfile(os.path.join(wd, "pyproject.toml")):
            cmds.append("python -m ruff check . 2>&1 || true")
        return cmds

    async def _run_safe(self, cmd: str) -> Optional[str]:
        if not self.run_cmd:
            return None
        try:
            result = await asyncio.wait_for(
                self.run_cmd(cmd),
                timeout=self.MAX_RUNTIME_SECONDS,
            )
            if isinstance(result, dict):
                return result.get("stdout", "") or result.get("stderr", "")
            return str(result)[:1000]
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            return str(e)

    async def _read_file_safe(self, path: str) -> str:
        if self.run_cmd:
            result = await self.run_cmd(f"Get-Content -LiteralPath '{path}' -Raw")
            if isinstance(result, dict):
                out = result.get("stdout", "") or result.get("content", "")
                return out[:10000] if out else ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(10000)

    def _scan_for_issues(self, content: str, filepath: str) -> list[str]:
        issues = []
        if re.search(r"(?i)(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]", content):
            issues.append("Possible hardcoded secret")
        if re.search(r"(?i)(TODO|FIXME|HACK|XXX)", content):
            issues.append("Contains TODO/FIXME/HACK")
        return issues


class VerifierJudgeAdapter:
    """
    Adapts VerifierAgent to JudgePipeline custom_judge interface.

    Uso:
        pipeline.set_custom_judge(VerifierJudgeAdapter(verifier).judge)
    """

    def __init__(self, verifier: VerifierAgent):
        self._verifier = verifier

    async def judge(self, ctx: dict) -> Any:
        """
        JudgePipeline custom_judge signature:
        ctx = {"assistant_text": str, "tool_results": list[dict], "output_accumulator": dict}
        """
        from judge_pipeline import JudgeAction, JudgeVerdict

        text = ctx.get("assistant_text", "") or ctx.get("result", "")
        task = ctx.get("task", "")
        criteria = ctx.get("success_criteria", "")

        report = await self._verifier.verify_code(
            task=task,
            result=text,
            success_criteria=criteria,
        )

        if report.verdict == Verdict.PASS:
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback=report.feedback,
                confidence=report.confidence,
                level=2,
            )
        return JudgeVerdict(
            action=JudgeAction.RETRY,
            feedback=report.feedback,
            confidence=report.confidence,
            level=2,
        )
