"""
DataCollector - Recolecta, filtra y cura datos de conversaciones para entrenamiento

Inspirado en el patron de NanoChat de usar conversaciones reales como datos de SFT.
Recolecta interacciones de alta calidad del sistema SuperNEXUS y las prepara
para el pipeline de entrenamiento.

Calidad > Cantidad: solo conversaciones exitosas con feedback positivo.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "training_data"
ARCHIVE_DIR = DATA_DIR / "archive"


@dataclass
class TrainingSample:
    """Una muestra de entrenamiento individual"""
    messages: List[Dict]  # [{role, content}, ...]
    gem_used: str
    project: str
    timestamp: str
    quality_score: float = 1.0  # 0.0 - 1.0
    tags: List[str] = field(default_factory=list)
    user_feedback: Optional[str] = None  # "good", "bad", "neutral"


@dataclass
class DataCollectorConfig:
    """Configuracion del recolector de datos"""
    min_quality_score: float = 0.7
    max_context_length: int = 8192
    archive_old_data: bool = True
    archive_days: int = 30
    auto_curate: bool = True
    # Data categories
    categories: List[str] = field(default_factory=lambda: [
        "code", "debug", "research", "creative", "analysis",
        "security", "devops", "design", "music", "general"
    ])


class DataCollector:
    """Recolector de datos de conversaciones para entrenamiento"""

    def __init__(self, config: Optional[DataCollectorConfig] = None):
        self.config = config or DataCollectorConfig()
        self._setup_dirs()
        self._stats = {
            "total_collected": 0,
            "total_curated": 0,
            "total_rejected": 0,
            "by_category": {},
        }

    def _setup_dirs(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        for cat in self.config.categories:
            (DATA_DIR / cat).mkdir(parents=True, exist_ok=True)

    def collect(self, conversation: Dict, metadata: Dict = None) -> Optional[TrainingSample]:
        """Recolecta una conversacion para entrenamiento"""
        sample = self._parse_conversation(conversation, metadata)
        if not sample:
            return None

        # Filtrar por calidad
        if sample.quality_score < self.config.min_quality_score:
            self._stats["total_rejected"] += 1
            logger.debug(f"Rechazada (baja calidad): score={sample.quality_score}")
            return None

        # Guardar
        self._save_sample(sample)
        self._stats["total_collected"] += 1
        logger.info(f"Recolectada: {sample.gem_used} | tags={sample.tags}")
        return sample

    def _parse_conversation(self, conversation: Dict, metadata: Dict = None) -> Optional[TrainingSample]:
        """Parsea una conversacion del chat en TrainingSample"""
        messages = conversation.get("messages", [])
        if len(messages) < 2:
            return None  # Muy corta para ser util

        gem = metadata.get("gem_used", "auto") if metadata else "auto"
        project = metadata.get("project", "default") if metadata else "default"

        # Calcular calidad
        quality = self._calculate_quality(conversation, metadata)

        # Detectar categoria
        tags = self._detect_tags(conversation)

        return TrainingSample(
            messages=messages,
            gem_used=gem,
            project=project,
            timestamp=metadata.get("timestamp", datetime.now().isoformat()) if metadata else datetime.now().isoformat(),
            quality_score=quality,
            tags=tags,
            user_feedback=metadata.get("user_feedback") if metadata else None,
        )

    def _calculate_quality(self, conversation: Dict, metadata: Dict = None) -> float:
        """Calcula score de calidad de la conversacion"""
        score = 1.0
        messages = conversation.get("messages", [])

        # Penalizar conversaciones muy cortas
        if len(messages) < 3:
            score *= 0.8

        # Penalizar si hay errores
        for msg in messages:
            content = msg.get("content", "").lower()
            if "error:" in content or "no puedo" in content or "no disponible" in content:
                score *= 0.5

        # Bonus por feedback positivo
        if metadata:
            feedback = metadata.get("user_feedback", "")
            if feedback == "good":
                score *= 1.2
            elif feedback == "bad":
                score *= 0.3

        # Bonus por longitud adecuada (ni muy corta ni muy larga)
        total_tokens = sum(len(msg.get("content", "")) for msg in messages)
        if 200 < total_tokens < 4000:
            score *= 1.1

        return min(1.0, max(0.0, score))

    def _detect_tags(self, conversation: Dict) -> List[str]:
        """Detecta tags/categoria de la conversacion"""
        tags = []
        text = " ".join(m.get("content", "").lower() for m in conversation.get("messages", []))

        tag_keywords = {
            "code": ["codigo", "function", "def ", "class ", "import ", "programa", "python", "javascript"],
            "debug": ["error", "bug", "fix", "traceback", "exception", "debug"],
            "research": ["investigar", "buscar", "analizar", "estudio", "paper"],
            "creative": ["escribir", "crear", "generar", "imagen", "musica", "video"],
            "security": ["seguridad", "vulnerabilidad", "auditoria", "exploit"],
            "devops": ["docker", "deploy", "pipeline", "ci/cd", "kubernetes"],
            "design": ["ui", "css", "frontend", "componente", "interfaz"],
            "analysis": ["datos", "analisis", "grafico", "estadistica", "kpi"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        return tags if tags else ["general"]

    def _save_sample(self, sample: TrainingSample):
        """Guarda una muestra en el archivo correspondiente"""
        # Determinar categoria principal
        category = sample.tags[0] if sample.tags else "general"
        cat_dir = DATA_DIR / category

        # Archivo por dia
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = cat_dir / f"{date_str}.jsonl"

        record = {
            "messages": sample.messages,
            "gem_used": sample.gem_used,
            "project": sample.project,
            "timestamp": sample.timestamp,
            "quality_score": sample.quality_score,
            "tags": sample.tags,
            "user_feedback": sample.user_feedback,
        }

        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        self._stats["total_curated"] += 1
        self._stats["by_category"][category] = self._stats["by_category"].get(category, 0) + 1

    def curate_dataset(self, output_path: Optional[str] = None) -> str:
        """Cura y consolida el dataset para entrenamiento"""
        if output_path is None:
            output_path = str(DATA_DIR / "curated_dataset.jsonl")

        samples = []
        for cat_dir in DATA_DIR.iterdir():
            if not cat_dir.is_dir() or cat_dir.name == "archive":
                continue
            for fp in cat_dir.glob("*.jsonl"):
                with open(fp, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            if record.get("quality_score", 0) >= self.config.min_quality_score:
                                samples.append(record)

        # Ordenar por calidad (mejores primero)
        samples.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        # Guardar dataset curado
        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')

        logger.info(f"Dataset curado: {len(samples)} muestras en {output_path}")
        return output_path

    def archive_old_data(self, days: int = None):
        """Archiva datos antiguos"""
        days = days or self.config.archive_days
        cutoff = time.time() - (days * 86400)

        for cat_dir in DATA_DIR.iterdir():
            if not cat_dir.is_dir() or cat_dir.name == "archive":
                continue
            for fp in cat_dir.glob("*.jsonl"):
                if fp.stat().st_mtime < cutoff:
                    dest = ARCHIVE_DIR / fp.name
                    fp.rename(dest)
                    logger.info(f"Archivado: {fp.name}")

    def get_stats(self) -> Dict:
        """Retorna estadisticas del recolector"""
        total_files = sum(1 for d in DATA_DIR.iterdir() if d.is_dir() for _ in d.glob("*.jsonl"))
        return {
            **self._stats,
            "data_files": total_files,
            "data_dir": str(DATA_DIR),
        }


# Singleton global
data_collector = DataCollector()
