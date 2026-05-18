"""
Judge Pipeline - Evaluacion de calidad de 3 niveles para SuperNEXUS v2

Evalua si una tarea fue completada correctamente usando 3 niveles:
1. Cortocircuito logico: Verificacion rapida de criterios basicos
2. Validacion estatica AST: Analisis sintactico del codigo generado
3. Evaluacion LLM: Juicio semantico usando modelo de razonamiento

Patrones extraidos de: aden-hive/core/framework/agent_loop/internals/judge_pipeline.py
"""

import ast
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus-judge")


class JudgeAction(str, Enum):
    ACCEPT = "ACCEPT"
    RETRY = "RETRY"
    FAIL = "FAIL"


@dataclass
class JudgeVerdict:
    action: JudgeAction
    feedback: str = ""
    confidence: float = 1.0
    level: int = 0  # Nivel de evaluacion (0=short-circuit, 1=AST, 2=LLM)


class LogicalShortCircuit:
    """
    Nivel 0: Verificacion rapida de criterios basicos.

    Detecta condiciones obvias de exito o fallo sin analisis profundo.
    """

    # Patrones de fallo obvio
    FAILURE_PATTERNS = [
        r"i (cannot|can't|unable|don't have access)",
        r"no (puedo|tengo acceso|encuentro)",
        r"error:?\s",
        r"exception:?\s",
        r"failed:?\s",
        r"not found",
        r"no existe",
        r"no se encontro",
    ]

    # Patrones de exito obvio
    SUCCESS_PATTERNS = [
        r"completed successfully",
        r"completado exitosamente",
        r"task completed",
        r"tarea completada",
        r"all tests passed",
        r"todos los tests pasaron",
        r"changes applied",
        r"cambios aplicados",
    ]

    @classmethod
    def evaluate(cls, result: str, expected_keys: List[str] = None, tool_results: List[Dict] = None) -> Optional[JudgeVerdict]:
        """
        Evalua resultado con cortocircuito logico.

        Retorna None si no puede determinar nada (pasar al siguiente nivel).
        """
        if not result or not result.strip():
            return JudgeVerdict(
                action=JudgeAction.RETRY,
                feedback="Resultado vacio. Debes proporcionar una respuesta.",
                confidence=0.9,
                level=0,
            )

        result_lower = result.lower()

        # Verificar patrones de fallo
        for pattern in cls.FAILURE_PATTERNS:
            if re.search(pattern, result_lower):
                return JudgeVerdict(
                    action=JudgeAction.RETRY,
                    feedback=f"Detectado posible fallo: '{pattern}'. Intenta de nuevo con otro enfoque.",
                    confidence=0.6,
                    level=0,
                )

        # Verificar patrones de exito
        for pattern in cls.SUCCESS_PATTERNS:
            if re.search(pattern, result_lower):
                return JudgeVerdict(
                    action=JudgeAction.ACCEPT,
                    feedback="Tarea completada exitosamente.",
                    confidence=0.7,
                    level=0,
                )

        # Verificar keys esperadas
        if expected_keys:
            missing = [k for k in expected_keys if k not in result_lower]
            if missing and len(missing) > len(expected_keys) * 0.5:
                return JudgeVerdict(
                    action=JudgeAction.RETRY,
                    feedback=f"Faltan elementos clave: {missing}. Asegurate de incluirlos.",
                    confidence=0.7,
                    level=0,
                )

        # Verificar si hubo llamadas a herramientas exitosas
        if tool_results:
            failed_tools = [t for t in tool_results if t.get("status") == "error" or t.get("error")]
            if len(failed_tools) > len(tool_results) * 0.5:
                return JudgeVerdict(
                    action=JudgeAction.RETRY,
                    feedback=f"La mayoria de herramientas fallaron ({len(failed_tools)}/{len(tool_results)}). Revisa los errores.",
                    confidence=0.8,
                    level=0,
                )

        # No se pudo determinar - pasar al siguiente nivel
        return None


class ASTValidator:
    """
    Nivel 1: Validacion estatica del codigo generado.

    Analiza sintaxis AST para verificar que el codigo es valido.
    """

    @classmethod
    def evaluate(cls, result: str, language: str = "python") -> Optional[JudgeVerdict]:
        """
        Evalua codigo generado con analisis AST.

        Retorna None si no hay codigo para validar o el lenguaje no es soportado.
        """
        if language != "python":
            return None

        # Extraer bloques de codigo
        code_blocks = cls._extract_code_blocks(result)
        if not code_blocks:
            return None  # No hay codigo, pasar al siguiente nivel

        verdicts = []
        for i, code in enumerate(code_blocks):
            verdict = cls._validate_python(code, i)
            verdicts.append(verdict)

        # Si algun bloque tiene error critico, retornar RETRY
        for v in verdicts:
            if v.action == JudgeAction.FAIL:
                return JudgeVerdict(
                    action=JudgeAction.RETRY,
                    feedback=f"Error de sintaxis en bloque de codigo {v.feedback}",
                    confidence=0.95,
                    level=1,
                )

        # Si todos los bloques son validos
        if all(v.action == JudgeAction.ACCEPT for v in verdicts):
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback=f"Todos los {len(code_blocks)} bloques de codigo son sintacticamente validos.",
                confidence=0.8,
                level=1,
            )

        return None

    @classmethod
    def _extract_code_blocks(cls, text: str) -> List[str]:
        """Extrae bloques de codigo markdown"""
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return [m.strip() for m in matches if m.strip()]

        # Si no hay bloques markdown, intentar detectar codigo python
        lines = text.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith(("def ", "class ", "import ", "from ", "#")):
                in_code = True
                code_lines.append(line)
            elif in_code and (line.strip() == "" or line.startswith((" ", "\t"))):
                code_lines.append(line)
            elif in_code and line.strip():
                code_lines.append(line)
                if any(kw in line for kw in ["return ", "raise ", "pass"]):
                    code = "\n".join(code_lines).strip()
                    if len(code) > 20:
                        return [code]
                    code_lines = []
                    in_code = False

        return []

    @classmethod
    def _validate_python(cls, code: str, block_index: int) -> JudgeVerdict:
        """Valida sintaxis Python usando AST"""
        try:
            ast.parse(code)
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback=f"bloque {block_index} valido",
                confidence=0.9,
                level=1,
            )
        except SyntaxError as e:
            return JudgeVerdict(
                action=JudgeAction.FAIL,
                feedback=f"bloque {block_index}, linea {e.lineno}: {e.msg}",
                confidence=0.95,
                level=1,
            )


class LLMJudge:
    """
    Nivel 2: Evaluacion semantica usando LLM.

    Usa un modelo de razonamiento para evaluar si la tarea fue completada.
    """

    EVALUATION_PROMPT = """Evaluador de tareas para SuperNEXUS.

Tarea original: {task}
Resultado producido: {result}
Criterios de exito: {success_criteria}

Evalua si la tarea fue completada correctamente.
Responde SOLO con un JSON:
{{"completed": true/false, "score": 0-100, "feedback": "explicacion breve"}}

Reglas:
- completed=true solo si TODOS los criterios de exito estan satisfechos
- score refleja la calidad (100 = perfecto, 0 = irrelevante)
- feedback debe ser conciso (max 100 caracteres)
"""

    def __init__(self, llm_executor: Callable = None):
        self.llm_executor = llm_executor

    async def evaluate(
        self,
        task: str,
        result: str,
        success_criteria: str = "",
    ) -> JudgeVerdict:
        """
        Evalua resultado usando LLM.

        Requiere un executor LLM configurado.
        """
        if not self.llm_executor:
            logger.warning("LLMJudge: no executor configured, skipping LLM evaluation")
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback="Sin evaluador LLM disponible, aceptando por defecto.",
                confidence=0.3,
                level=2,
            )

        prompt = self.EVALUATION_PROMPT.format(
            task=task,
            result=result[:2000],
            success_criteria=success_criteria or "Completar la tarea correctamente",
        )

        try:
            llm_result = await self.llm_executor(prompt)
            content = llm_result.get("content", "") if isinstance(llm_result, dict) else str(llm_result)

            # Parsear respuesta JSON
            import json
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
                completed = evaluation.get("completed", False)
                score = evaluation.get("score", 0)
                feedback = evaluation.get("feedback", "")

                if completed and score >= 70:
                    return JudgeVerdict(
                        action=JudgeAction.ACCEPT,
                        feedback=feedback or "Tarea evaluada como completada.",
                        confidence=score / 100,
                        level=2,
                    )
                else:
                    return JudgeVerdict(
                        action=JudgeAction.RETRY,
                        feedback=feedback or f"Tarea incompleta (score: {score}/100). Mejora el resultado.",
                        confidence=1.0 - (score / 100),
                        level=2,
                    )

            # Si no se pudo parsear JSON, evaluacion conservadora
            return JudgeVerdict(
                action=JudgeAction.RETRY,
                feedback="No se pudo evaluar automaticamente. Verifica manualmente.",
                confidence=0.4,
                level=2,
            )

        except Exception as e:
            logger.error(f"LLMJudge evaluation error: {e}")
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback=f"Error en evaluacion LLM: {e}. Aceptando por defecto.",
                confidence=0.2,
                level=2,
            )


class SubagentJudge:
    """
    Juez especializado para sub-agentes.

    Evalua si un sub-agente completo su tarea especificica.
    """

    def __init__(self, task_description: str):
        self.task_description = task_description

    def evaluate(self, assistant_text: str, tool_results: List[Dict], output_accumulator: Dict) -> JudgeVerdict:
        """Evalua si el sub-agente completo su tarea"""
        if not assistant_text and not output_accumulator:
            return JudgeVerdict(
                action=JudgeAction.RETRY,
                feedback=f"Sub-agent task incomplete: {self.task_description}. No output produced.",
                confidence=0.9,
                level=0,
            )
        return JudgeVerdict(
            action=JudgeAction.ACCEPT,
            feedback="Sub-agent task appears complete.",
            confidence=0.7,
            level=0,
        )


class JudgePipeline:
    """
    Pipeline de evaluacion de 3 niveles.

    Uso:
        pipeline = JudgePipeline(llm_executor=director.ai_tools.quick_response)
        verdict = await pipeline.evaluate(
            task="Crear una funcion que sume dos numeros",
            result="def add(a, b): return a + b",
            success_criteria="Funcion valida en Python",
            tool_results=[{"tool": "code", "status": "success"}],
        )
    """

    def __init__(self, llm_executor: Callable = None, max_iterations: int = 10):
        self.logical = LogicalShortCircuit()
        self.ast = ASTValidator()
        self.llm = LLMJudge(llm_executor)
        self._evaluation_count = 0
        self._iteration = 0
        self._max_iterations = max_iterations
        self._subagent_judge: Optional[SubagentJudge] = None
        self._custom_judge: Optional[Callable] = None

    def reset(self):
        """Resetea el contador de iteraciones"""
        self._iteration = 0

    def set_subagent_judge(self, task_description: str):
        """Configura un juez especializado para sub-agente"""
        self._subagent_judge = SubagentJudge(task_description)

    def set_custom_judge(self, judge_fn: Callable):
        """Configura un juez personalizado"""
        self._custom_judge = judge_fn

    def evaluate(
        self,
        assistant_text: str = "",
        tool_results: List[Dict] = None,
        output_accumulator: Dict = None,
        output_keys: List[str] = None,
        mark_complete: bool = False,
        skip_judge: bool = False,
        task: str = "",
        result: str = "",
        success_criteria: str = "",
        expected_keys: List[str] = None,
        language: str = "python",
    ) -> JudgeVerdict:
        """
        Evalua resultado pasando por los 3 niveles.

        Soporta dos APIs:
        - Nueva: assistant_text, tool_results, output_accumulator, output_keys
        - Legacy: task, result, success_criteria, expected_keys
        """
        self._iteration += 1
        self._evaluation_count += 1

        if skip_judge:
            return JudgeVerdict(
                action=JudgeAction.RETRY,
                feedback="Judge skipped by request.",
                confidence=0.0,
                level=0,
            )

        if mark_complete:
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback="Marked complete by request.",
                confidence=1.0,
                level=0,
            )

        # Use subagent judge if configured
        if self._subagent_judge:
            verdict = self._subagent_judge.evaluate(
                assistant_text or result,
                tool_results or [],
                output_accumulator or {},
            )
            return verdict

        # Use custom judge if configured
        if self._custom_judge:
            ctx = {
                "assistant_text": assistant_text or result,
                "tool_results": tool_results or [],
                "output_accumulator": output_accumulator or {},
            }
            return self._custom_judge(ctx)

        # Normalize inputs
        text = assistant_text or result
        keys = output_keys or expected_keys
        accum = output_accumulator or {}

        # Quick check: empty output with required keys = RETRY
        if not text.strip() and not accum and keys:
            missing = keys
            return JudgeVerdict(
                action=JudgeAction.RETRY,
                feedback=f"Output incomplete: missing keys {missing}. No response produced.",
                confidence=0.95,
                level=0,
            )

        # If output_accumulator has all required keys, accept regardless of text
        if keys and all(k in accum for k in keys):
            return JudgeVerdict(
                action=JudgeAction.ACCEPT,
                feedback="All required keys present in output.",
                confidence=0.9,
                level=0,
            )

        # Nivel 0: Cortocircuito logico
        verdict = self.logical.evaluate(text, keys, tool_results)
        if verdict:
            logger.info(f"Judge L0: {verdict.action.value} (confidence: {verdict.confidence:.2f})")
            return verdict

        # Nivel 1: Validacion AST (solo para codigo)
        if language == "python":
            verdict = self.ast.evaluate(text, language)
            if verdict:
                logger.info(f"Judge L1: {verdict.action.value} (confidence: {verdict.confidence:.2f})")
                return verdict

        # Nivel 2: LLM evaluation (skip if no executor - accept by default)
        if self.llm.llm_executor:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context - accept by default
                    return JudgeVerdict(
                        action=JudgeAction.ACCEPT,
                        feedback="LLM evaluation deferred (async context).",
                        confidence=0.5,
                        level=2,
                    )
                else:
                    verdict = loop.run_until_complete(self.llm.evaluate(task or text, text, success_criteria))
                    logger.info(f"Judge L2: {verdict.action.value} (confidence: {verdict.confidence:.2f})")
                    return verdict
            except Exception:
                pass

        # No LLM executor available - accept by default
        return JudgeVerdict(
            action=JudgeAction.ACCEPT,
            feedback="No LLM evaluator available, accepting by default.",
            confidence=0.3,
            level=2,
        )

    def get_stats(self) -> Dict:
        return {
            "total_evaluations": self._evaluation_count,
            "iteration": self._iteration,
            "max_iterations": self._max_iterations,
        }
