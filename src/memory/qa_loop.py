"""
QA Loop - Auto-mejora de agentes para SuperNEXUS v2.0

Adaptado de OpenSwarm qa_loop.py.
Los agentes evaluan su propio rendimiento y se mejoran iterativamente.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class QALoop:
    """
    Loop de calidad para auto-mejora de agentes.
    Evalua respuestas, identifica areas de mejora, aplica correcciones.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent.parent / "data" / "qa")

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.data_dir / "qa_history.json"
        self.improvements_file = self.data_dir / "improvements.json"
        self.history: List[Dict] = []
        self.improvements: Dict = {"rules": [], "patterns": [], "metrics": {}}
        self._load()

    def _load(self):
        """Carga historial y mejoras"""
        if self.history_file.exists():
            try:
                self.history = json.loads(
                    self.history_file.read_text(encoding="utf-8")
                )
            except:
                self.history = []

        if self.improvements_file.exists():
            try:
                self.improvements = json.loads(
                    self.improvements_file.read_text(encoding="utf-8")
                )
            except:
                self.improvements = {"rules": [], "patterns": [], "metrics": {}}

    def _save(self):
        """Guarda historial y mejoras"""
        self.history_file.write_text(
            json.dumps(self.history[-1000:], indent=2), encoding="utf-8"
        )
        self.improvements_file.write_text(
            json.dumps(self.improvements, indent=2), encoding="utf-8"
        )

    def evaluate_response(
        self,
        query: str,
        response: str,
        gem_used: str,
        success: bool,
        feedback: str = "",
        metrics: Optional[Dict] = None,
    ) -> Dict:
        """
        Evalua una respuesta de agente.
        Registra el resultado y busca patrones de mejora.
        """
        entry = {
            "id": f"qa_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "query": query[:500],
            "response_preview": response[:500],
            "gem_used": gem_used,
            "success": success,
            "feedback": feedback,
            "metrics": metrics or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.history.append(entry)

        # Si fallo, buscar patron de mejora
        if not success:
            self._identify_improvement(query, response, feedback, gem_used)

        # Actualizar metricas
        self._update_metrics(gem_used, success)

        self._save()
        return entry

    def _identify_improvement(self, query: str, response: str, feedback: str, gem: str):
        """Identifica areas de mejora basadas en fallos"""
        # Buscar patrones comunes en fallos
        failure_patterns = {
            "timeout": "response took too long",
            "empty": "response was empty or incomplete",
            "error": "response contained errors",
            "irrelevant": "response was not relevant to query",
        }

        for pattern, description in failure_patterns.items():
            if pattern in feedback.lower() or pattern in response.lower():
                # Verificar si ya existe regla para este patron
                existing = [
                    r for r in self.improvements["rules"]
                    if r.get("pattern") == pattern and r.get("gem") == gem
                ]
                if not existing:
                    self.improvements["rules"].append({
                        "pattern": pattern,
                        "gem": gem,
                        "description": description,
                        "suggestion": f"Improve {gem} handling of {pattern} cases",
                        "created": datetime.now().isoformat(),
                        "trigger_count": 1,
                    })
                else:
                    existing[0]["trigger_count"] = existing[0].get("trigger_count", 0) + 1

    def _update_metrics(self, gem: str, success: bool):
        """Actualiza metricas de rendimiento por gem"""
        metrics = self.improvements.setdefault("metrics", {})
        gem_metrics = metrics.setdefault(gem, {"total": 0, "success": 0, "fail": 0})

        gem_metrics["total"] += 1
        if success:
            gem_metrics["success"] += 1
        else:
            gem_metrics["fail"] += 1

        gem_metrics["success_rate"] = (
            gem_metrics["success"] / gem_metrics["total"]
            if gem_metrics["total"] > 0
            else 0
        )

    def get_improvements(self) -> List[Dict]:
        """Obtiene lista de mejoras identificadas"""
        # Ordenar por trigger_count (mas frecuentes primero)
        return sorted(
            self.improvements.get("rules", []),
            key=lambda x: x.get("trigger_count", 0),
            reverse=True,
        )

    def get_gem_performance(self) -> Dict[str, Dict]:
        """Obtiene rendimiento de cada gem"""
        return self.improvements.get("metrics", {})

    def get_recent_failures(self, limit: int = 10) -> List[Dict]:
        """Obtiene fallos recientes"""
        return [
            entry for entry in reversed(self.history)
            if not entry.get("success")
        ][:limit]

    def get_stats(self) -> Dict:
        """Estadisticas generales del QA loop"""
        total = len(self.history)
        successes = sum(1 for h in self.history if h.get("success"))
        failures = total - successes

        return {
            "total_evaluations": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0,
            "improvement_rules": len(self.improvements.get("rules", [])),
            "gems_tracked": len(self.improvements.get("metrics", {})),
        }
