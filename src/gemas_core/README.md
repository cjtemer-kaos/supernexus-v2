# gemas_core — Estándar canónico de gemas para proyectos SuperNEXUS

**Source canónica:** `supernexus-v2/src/gemas_core/`
**Sincronizado a:** `latamrust-nexus/src/gemas_core/`, `sfdx/nexus/src/gemas_core/`
**Versión:** 1.5.0

## ¿Qué es?

Módulo Python estándar que define el contrato y la implementación base de las
gemas de SuperNEXUS. Es la **fuente única de verdad** para:

- `GemaBase` (interfaz abstracta)
- `GemaManifest` (dataclass de metadata leída de JSON)
- `LLMRoleGema` (dispatcher Ollama genérico)
- `build_standard_gemas()` (carga 6 dedicated + 18 manifests = 24)
- `dispatch_gema()` (dispatcher con `inspect.signature`, plan_mode, disabled_gemas)
- `validate_manifest()` (validador JSON)
- `core.atomic_io` (crash-safe JSON/text writes)
- `core.prompt_security` (anti-injection wrapper)
- `core.rate_limiter` (sliding-window in-memory rate limiter)
- `core.rate_limit_helpers` (v1.4.0 — aiohttp integration: `client_key`, `check_http`, `check_ws`, `rate_limit_middleware`)
- `core.rate_limit_unified` (v1.9.0 — `SafetyLimiter` facade: multi-purpose, request-aware, admin reset, observability)
- `core.rate_limiter_redis` (v1.10.0 — `RedisRateLimiter` for shared buckets across processes; `SafetyLimiter(backend="redis", ...)`)
- `core.url_utils` (v1.5.0 — stdlib HTTP URL validation: `is_valid_url`, `normalize_url`, `parse_url`)
- `core.html_text` (v1.5.0 — stdlib HTML→text: `extract_text`, `extract_text_with_meta`)
- `core.text_ranker` (v1.5.0 — TF-IDF + embedder hook: `rank_content`, `KeywordScorer`, `Embedder` protocol)
- `core.web_crawler` (v1.5.0 — async BFS recursive crawler: `RecursiveCrawler`, `Fetcher` protocol, `extract_links`)
- `core.memory_types` (v1.7.0 — RUFLO taxonomy: `MemoryType`, `AccessLevel`, `DistanceMetric`)
- `core.hook_events` (v1.7.0 — RUFLO 19-event / 5-priority: `HookEvent`, `HookPriority`)
- `teammate.contract` (v1.7.0 — multi-agent dataclasses: `PeerStatus`, `MailboxMessage`, `PlanProposal`, `TeleportRequest`)
- `core.memory_consolidator` (v1.8.0 — sweep/dedup/compact API: `sweep_expired`, `dedup`, `compact_index`, `run_all`)
- `core.smart_retrieval` (v1.8.0 — 5-phase search pipeline: `smart_search`, `rrf_fuse`, `recency_boost`, `mmr_diversify`, `session_diversify`)
- `agents.plan_mode` (user-approved plan gating)
- 6 workers estándar: `AyudaGem`, `ScholarGem`, `SageGem`, `BibliotecaGem`, `PrompterGem`, `WebResearchGem` (v1.6.0)

## Estructura

```
gemas_core/
├── __init__.py             # Public API (v1.5.0)
├── base.py                 # GemaBase ABC + GemaManifest + ManifestSchema
├── llm_role_gema.py        # LLMRoleGema + load_all_role_gemas()
├── builders.py             # build_standard_gemas() + IDs list
├── dispatch.py             # dispatch_gema() + list_gema_methods() + plan_mode
├── manifest_schema.py      # DEFAULT_* + validate_manifest()
├── core/                   # v1.2.0 — utility submodules
│   ├── __init__.py
│   ├── atomic_io.py        # atomic_write_json + atomic_write_text
│   ├── prompt_security.py  # untrusted_context_message + is_untrusted_message
│   ├── rate_limiter.py     # v1.3.0 — RateLimiter (sliding window, thread-safe)
│   ├── rate_limit_helpers.py  # v1.4.0 — aiohttp integration
│   ├── rate_limit_unified.py  # v1.9.0 — SafetyLimiter facade
│   ├── rate_limiter_redis.py  # v1.10.0 — RedisRateLimiter (shared buckets)
│   ├── url_utils.py        # v1.5.0 — stdlib HTTP URL validation
│   ├── html_text.py        # v1.5.0 — stdlib HTML→text extraction
│   ├── text_ranker.py      # v1.5.0 — TF-IDF + embedder hook
│   └── web_crawler.py      # v1.5.0 — async BFS recursive crawler
├── agents/                 # v1.2.0 — agent-loop helpers
│   ├── __init__.py
│   └── plan_mode.py        # PLAN_MODE_DIRECTIVE + active plan + mutator gating
├── workers/
│   ├── __init__.py
│   ├── ayuda.py            # AyudaGem (guía reactiva + perfil adaptativo)
│   ├── scholar.py          # ScholarGem (research web multi-backend)
│   ├── sage.py             # SageGem (persistencia SQLite)
│   ├── biblioteca.py       # BibliotecaGem (knowledge base)
│   ├── prompter.py         # PrompterGem (prompt engineering)
│   └── prompter_knowledge.py  # KB estática: 13 templates + 37 patterns
├── tests/                  # 314 tests unitarios (pytest)
└── README.md
```

## Public API

```python
from gemas_core import (
    GemaBase,                # ABC — extender para crear nuevas gemas
    GemaManifest,            # Dataclass — metadata de manifest
    ManifestSchema,          # Constantes del schema JSON
    LLMRoleGema,             # Dispatcher Ollama genérico
    load_all_role_gemas,     # Carga todos los manifests de data/gemas/*.json
    build_standard_gemas,    # Carga 6 dedicated + 18 role
    list_standard_dedicated_ids,  # ('ayuda', 'scholar', 'sage', 'biblioteca', 'prompter', 'web_research')
    list_standard_role_ids,  # 18 role-LLM IDs
    list_all_standard_ids,   # 24 IDs en orden
    dispatch_gema,           # Dispatcher con signature inspection
    list_gema_methods,       # Introspección de métodos
    RateLimiter,             # v1.3.0 — sliding-window in-memory rate limiter
    client_key,              # v1.4.0 — aiohttp request key extractor
    check_http,              # v1.4.0 — 429 short-circuit for HTTP handlers
    check_ws,                # v1.4.0 — per-message gate for WS loops
    rate_limit_middleware,   # v1.4.0 — aiohttp middleware factory
)
```

## Gemas del estándar (23 total)

### Dedicated (5 — workers Python propios)

| ID | Nombre | Categoría | Descripción |
|----|--------|-----------|-------------|
| `ayuda` | AyudaGem | workflow | Guía reactiva, perfil adaptativo de usuario |
| `scholar` | ScholarGem | research | Investigación web multi-backend con síntesis |
| `sage` | SageGem | data-ai | Persistencia SQLite con búsqueda full-text |
| `biblioteca` | BibliotecaGem | data-ai | Knowledge base con index + search |
| `prompter` | PrompterGem | core | Prompt engineering con 13 templates + 37 patterns (MIT, nidhinjs/prompt-master v1.6.0) |

### Role-LLM (18 — system_prompt + Ollama)

`analyst`, `architect`, `code`, `codex`, `creative`, `debugger`, `design`,
`devops`, `director`, `engineer`, `music`, `opencode`, `optimizer`, `producer`,
`security`, `tester`, `trainer`, `vision`.

> **v1.1.0:** `prompter` fue promovida de role-LLM a dedicated (ver CHANGELOG).
> **v1.6.0:** `web_research` fue añadida como 6ª dedicated (port RUFUS primitives → gem).

### PrompterGem — quick start

```python
from gemas_core.workers import PrompterGem

g = PrompterGem()  # ollama_client opcional para refine vía LLM

# Análisis estático (sin Ollama)
result = await g.execute("Write me a prompt for Cursor to refactor auth module")
# → {target_tool: "cursor", template_id: "G", template: "File-Scope",
#    detected_patterns: [...], filled_prompt: "...", audit_trail: [...]}

# Refinamiento vía Ollama (cliente inyectable)
import ollama
g_opt = PrompterGem(ollama_client=ollama.AsyncClient())
result = await g_opt.optimize("Build a Claude Code prompt for REST API")
# → mismo analysis + refined_prompt (string del LLM)

# Acceso directo a la knowledge base
from gemas_core.workers.prompter_knowledge import (
    get_template, list_templates, list_patterns, detect_pattern,
    detect_target_tool, is_reasoning_model, pick_template_for,
)
```

Knowledge base: **13 templates A-M** (RTF, CO-STAR, RISEN, CRISPE, CoT, Few-Shot,
File-Scope, ReAct+Stop, Visual Descriptor, Reference Image Editing, ComfyUI,
Prompt Decompiler, Opus 4.7 Task Brief) + **37 credit-killing patterns** en 6
categorías (task, context, format, scope, reasoning, agentic). Source:
<https://github.com/nidhinjs/prompt-master> (MIT).

## Uso en cliente

### Patrón 1 — Standard only (SuperNEXUS base)

```python
from gemas_core import build_standard_gemas
from pathlib import Path

gemas = build_standard_gemas(
    gemas_dir=Path("data/gemas"),
    ollama_url="http://127.0.0.1:11434",
)
# 24 gemas: 6 dedicated + 18 role-LLM (v1.6.0)
```

### Patrón 2 — Standard + client overrides (LatamRust, SFDX)

```python
from gemas_core import build_standard_gemas
from src.gemas_client_overrides import (
    RconCommanderGem,
    CombatlogAnalystGem,
    PluginConfiguratorGem,
    # ... 8 gemas operativas Rust
)

# 1) Cargar standard
gemas = build_standard_gemas(gemas_dir=Path("data/gemas"))

# 2) Mergear con client-specific (sobrescriben o añaden)
client_gemas = {
    "rcon_commander": RconCommanderGem(),
    "combatlog_analyst": CombatlogAnalystGem(),
    # ...
}
gemas.update(client_gemas)
# Total: 23 standard + 8 client = 31
```

### Patrón 3 — Solo dispatch (sin builder)

```python
from gemas_core import dispatch_gema
from gemas_core.workers.ayuda import AyudaGem

gem = AyudaGem()
result = await dispatch_gema(gem, task="que puedes hacer")
# dispatch_gema detecta signature y llama con los kwargs correctos
```

## Vendor copy + sync script

Cada cliente tiene su propia copia de `gemas_core/` sincronizada desde
SuperNEXUS. **NO** usamos git submodule (fragil en Windows) ni pip package
(sobrecosto). El script es:

```bash
python scripts/sync_gemas_core.py --list          # listar clientes
python scripts/sync_gemas_core.py --client NAME   # sync uno
python scripts/sync_gemas_core.py --all           # sync todos
python scripts/sync_gemas_core.py --all --dry-run # ver qué cambiaría
```

El script:
- Compara source vs dest por bytes
- Copia nuevos / actualiza diferentes (con `.sync-backup.` prefix)
- Elimina archivos en dest que no están en source
- **Preserva** `gemas_client_overrides/` en cada cliente
- Limpia `__pycache__` y `.pyc`
- Verifica imports después del sync
- Corre tests del cliente

## Schema de manifest

```json
{
  "name": "code",
  "model": "qwen2.5-coder:7b",
  "description": "Code review, refactoring, programación",
  "systemPrompt": "Eres CODE, gema especializada...",
  "semanticKeywords": ["code", "review", "refactor"],
  "category": "code"
}
```

**Campos requeridos:** `name`
**Campos opcionales:** `model`, `description`, `systemPrompt`, `semanticKeywords`, `category`, `version`, `author`, `dependencies`

Validar con:
```python
from gemas_core.manifest_schema import validate_manifest
errors = validate_manifest(manifest_dict)  # [] si OK, [str] si hay errores
```

## Tests

```bash
cd supernexus-v2
python -m pytest src/gemas_core/tests/ -v    # 314/314 pass (v1.4.0)

cd latamrust-nexus
python -m pytest tests/ src/gemas_core/tests/ -v   # 314/314 gemas_core + suite global
```

## Añadir una nueva gema standard

1. Añadir manifest en `supernexus-v2/data/gemas/<nombre>.json`
2. Si tiene worker Python: añadir en `supernexus-v2/src/gemas_core/workers/`
3. Si solo es role-LLM: ya está, solo añadir el manifest
4. Si es dedicated nueva (no es uno de los 4 actuales): añadir a
   `STANDARD_DEDICATED_IDS` en `builders.py`
5. Añadir tests en `tests/test_workers.py` o `tests/test_llm_role_gema.py`
6. Sincronizar:
   ```bash
   python scripts/sync_gemas_core.py --all
   ```

## Añadir una gema client-specific

1. Crear `cliente/src/gemas_client_overrides/<nombre>_gem.py`
2. Implementar extendiendo `GemaBase`:
   ```python
   from gemas_core import GemaBase
   class MyClientGem(GemaBase):
       name = "my_client_gem"
       description = "..."
       async def execute(self, task, context=""):
           return {"success": True, "gema": "my_client_gem", "output": ...}
   ```
3. Registrar en el `client_director.py` del cliente (merge con `build_standard_gemas()`)
4. **No requiere tocar SuperNEXUS** — el script preserva `gemas_client_overrides/`

## Versioning

`__version__ = "1.0.0"` en `__init__.py`. Para bump:
- **Patch** (1.0.x): bug fixes, sin cambios de API
- **Minor** (1.x.0): nuevas gemas standard, nuevas funciones, backwards-compat
- **Major** (x.0.0): cambios breaking en API o schema

Tras bump, sync automático a todos los clientes.
