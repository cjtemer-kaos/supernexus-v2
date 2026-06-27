"""
Interfaz base de gema + dataclass de manifest.

GemaBase es el contrato que toda gema (dedicada o role-LLM) debe cumplir.
GemaManifest encapsula metadata leída de data/gemas/<name>.json.
ManifestSchema define los campos estándar del manifest JSON.
"""
from __future__ import annotations

import abc
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass


class ManifestSchema:
    """Constantes del schema JSON estándar para data/gemas/*.json.

    Los clientes pueden extender (p. ej. LatamRust añade 'rust_operative: true'),
    pero estos son los campos mínimos garantizados.
    """
    FIELD_NAME = "name"
    FIELD_MODEL = "model"
    FIELD_DESCRIPTION = "description"
    FIELD_SYSTEM_PROMPT = "systemPrompt"
    FIELD_KEYWORDS = "semanticKeywords"
    FIELD_CATEGORY = "category"
    FIELD_CHECKPOINT = "useCheckpointContract"

    REQUIRED = {FIELD_NAME}
    DEFAULT_MODEL = "gemma4:latest"


@dataclass
class GemaManifest:
    """Metadata de una gema leída de data/gemas/<name>.json.

    Attributes:
        name: Identificador único (e.g. "code", "scholar", "ayuda").
        model: Modelo Ollama preferido (e.g. "qwen2.5-coder:7b").
        description: Descripción corta de 1-2 líneas.
        system_prompt: System prompt especializado del rol LLM.
        keywords: Keywords semánticas para routing.
        category: Categoría (general, plugins, server_control, ...).
        raw: Manifest completo como dict (para campos client-specific).
        source_path: Path al manifest (opcional, para tooling).
    """
    name: str
    model: str = ManifestSchema.DEFAULT_MODEL
    description: str = ""
    system_prompt: str = ""
    keywords: List[str] = field(default_factory=list)
    category: str = "general"
    use_checkpoint_contract: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional["Path"] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GemaManifest":
        """Construye un GemaManifest desde un dict (JSON loaded)."""
        if ManifestSchema.FIELD_NAME not in data:
            raise ValueError(f"manifest missing required field 'name': {data}")
        return cls(
            name=data[ManifestSchema.FIELD_NAME],
            model=data.get(ManifestSchema.FIELD_MODEL, ManifestSchema.DEFAULT_MODEL),
            description=data.get(ManifestSchema.FIELD_DESCRIPTION, ""),
            system_prompt=data.get(ManifestSchema.FIELD_SYSTEM_PROMPT, ""),
            keywords=data.get(ManifestSchema.FIELD_KEYWORDS, []),
            category=data.get(ManifestSchema.FIELD_CATEGORY, "general"),
            use_checkpoint_contract=data.get(ManifestSchema.FIELD_CHECKPOINT, False),
            raw=data,
        )

    @classmethod
    def from_file(cls, path: Path) -> "GemaManifest":
        """Carga un GemaManifest desde un archivo JSON."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        instance = cls.from_dict(data)
        instance.source_path = path
        return instance

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para listar en UI/API."""
        return asdict(self)


class GemaBase(abc.ABC):
    """Interfaz abstracta que toda gema debe implementar.

    Una gema es una unidad de procesamiento especializada que recibe
    una tarea (string) + contexto opcional y devuelve un dict de resultado.

    Métodos:
        execute(task, context) -> dict
            Método principal de la gema. Es async.

        to_dict() -> dict
            Serializa metadata para listar en UI/API.

    Subclases deben implementar execute() y opcionalmente to_dict().
    El adapter de dispatch detecta la signature y llama al método correcto.
    """

    name: str = ""
    description: str = ""
    category: str = "general"

    @abc.abstractmethod
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Ejecuta la gema sobre una tarea y devuelve un dict de resultado.

        El dict debe incluir al menos 'success' (bool) y 'gema' (str).
        """
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Serializa metadata. Override en subclases para campos extra."""
        return {
            "id": self.name,
            "name": self.name.upper(),
            "description": self.description,
            "category": self.category,
        }
