"""
dispatch — Dispatcher con inspect.signature para tolerar signatures distintas.

Gemas tienen diferentes signatures (e.g. AyudaGem.execute(task) vs
SageGem.analyze_and_persist(task) vs LLMRoleGema.execute(task, context)).
Esta utility inspecciona la signature del método y llama con los kwargs
disponibles.

When ``plan_mode=True`` is passed, gemas registered as mutators in
:mod:`gemas_core.agents.plan_mode` are blocked before execution and
return a structured error. Pass ``disabled_gemas`` to override the
default blocklist (e.g. for testing or for a custom orchestrator
that maintains its own blocklist).
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, FrozenSet, Optional

from .agents.plan_mode import is_mutating_gema
from .base import GemaBase

logger = logging.getLogger("gemas-core.dispatch")


def list_gema_methods(gema: GemaBase) -> Dict[str, inspect.Signature]:
    """Retorna dict {method_name: signature} de métodos públicos de la gema.

    Útil para introspection y para routing explícito.
    """
    out: Dict[str, inspect.Signature] = {}
    for name in dir(gema):
        if name.startswith("_"):
            continue
        attr = getattr(gema, name, None)
        if not callable(attr):
            continue
        try:
            sig = inspect.signature(attr)
        except (ValueError, TypeError):
            continue
        out[name] = sig
    return out


async def dispatch_gema(
    gema: GemaBase,
    task: str,
    context: str = "",
    method: str = "execute",
    plan_mode: bool = False,
    disabled_gemas: Optional[FrozenSet[str]] = None,
) -> Dict[str, Any]:
    """Dispatch una tarea a una gema, adaptándose a la signature del método.

    Args:
        gema: Instancia de GemaBase (o duck-typed con método execute / run / handle).
        task: Tarea / mensaje del usuario.
        context: Contexto adicional (opcional, default "").
        method: Nombre del método principal (default "execute").
        plan_mode: Si True, bloquea gemas mutadoras antes de ejecutarlas.
                   Por defecto usa :func:`plan_mode_disabled_gemas`; pasar
                   ``disabled_gemas`` para usar un set personalizado.
        disabled_gemas: Set explícito de nombres de gemas a bloquear.
                         Tiene precedencia sobre ``plan_mode``.

    Returns:
        Dict con el resultado de la gema, o un error estructurado si
        ``plan_mode=True`` y la gema es mutadora.

    Notes:
        - Si el método no existe, intenta con "run" y luego "handle".
        - Si acepta (task, context), pasa ambos.
        - Si acepta solo (task), pasa solo task.
        - Si acepta solo (context), pasa solo context.
        - Si acepta variadic *args, pasa task como primer arg.
    """
    if not isinstance(gema, GemaBase) and not hasattr(gema, method):
        return {
            "success": False,
            "error": f"object is not a GemaBase and has no '{method}' method",
        }

    gema_name = getattr(gema, "name", "") or ""

    if disabled_gemas is not None and gema_name in disabled_gemas:
        return {
            "success": False,
            "gema": gema_name or "unknown",
            "error": f"gema '{gema_name}' is disabled by orchestrator blocklist",
            "plan_mode_blocked": True,
        }
    if plan_mode and is_mutating_gema(gema_name):
        return {
            "success": False,
            "gema": gema_name or "unknown",
            "error": (
                f"gema '{gema_name}' is a mutator and cannot run in plan mode. "
                "Use it only after the user approves the plan."
            ),
            "plan_mode_blocked": True,
        }

    for candidate in (method, "execute", "run", "handle"):
        fn = getattr(gema, candidate, None)
        if fn is None or not callable(fn):
            continue
        try:
            sig = inspect.signature(fn)
        except (ValueError, TypeError):
            continue

        kwargs = _build_kwargs(sig, task=task, context=context)
        positional_args = _build_args(sig, task=task, context=context)
        try:
            if positional_args:
                result = fn(*positional_args)
            else:
                result = fn(**kwargs)
            if inspect.iscoroutine(result):
                result = await result
            return result if isinstance(result, dict) else {
                "success": True,
                "gema": gema_name or "unknown",
                "output": result,
            }
        except TypeError as e:
            # Signature mismatch — try next candidate
            logger.debug(f"signature mismatch on {candidate}: {e}")
            continue
        except Exception as e:
            return {
                "success": False,
                "gema": gema_name or "unknown",
                "error": f"{type(e).__name__}: {e}",
            }

    return {
        "success": False,
        "gema": gema_name or "unknown",
        "error": f"no callable method matched for '{gema.__class__.__name__}'",
    }


def _build_kwargs(sig: inspect.Signature, task: str, context: str) -> Dict[str, Any]:
    """Construye kwargs basado en la signature del método."""
    params = list(sig.parameters.values())

    # Si tiene *args, NO usar kwargs — el caller usará positional args
    has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
    if has_var_positional:
        return {}

    kwargs: Dict[str, Any] = {}
    param_names = {p.name for p in params}

    if "task" in param_names:
        kwargs["task"] = task
    elif "query" in param_names:
        kwargs["query"] = task
    elif "message" in param_names:
        kwargs["message"] = task
    elif "input" in param_names:
        kwargs["input"] = task

    if "context" in param_names:
        kwargs["context"] = context

    return kwargs


def _build_args(sig: inspect.Signature, task: str, context: str) -> tuple:
    """Construye positional args basado en la signature del método.

    Para *args: pasa (task, context) si context, sino (task,)
    Para signatures posicionales específicas: respeta el orden.
    """
    params = list(sig.parameters.values())
    has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
    if has_var_positional:
        return (task, context) if context else (task,)

    # Sin *args, no hay positional args que construir (usar kwargs).
    return ()
