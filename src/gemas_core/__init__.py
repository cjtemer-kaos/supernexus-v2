"""
gemas_core — Estándar canónico de gemas para proyectos SuperNEXUS.

Este módulo es la fuente única de verdad para:
  - GemaBase (interfaz abstracta)
  - GemaManifest (dataclass de metadata)
  - LLMRoleGema (dispatcher Ollama genérico)
  - build_standard_gemas() (carga 6 dedicated + 18 manifests)
  - dispatch_gema() (dispatcher con inspect.signature + plan_mode)
  - 6 workers estándar: AyudaGem, ScholarGem, SageGem, BibliotecaGem, PrompterGem, WebResearchGem
  - core.atomic_io: write-tmp-fsync-replace para JSON/text
  - core.prompt_security: untrusted context wrapper anti-injection
  - core.rate_limiter: sliding-window in-memory rate limiter, key-based, thread-safe
  - core.rate_limit_helpers: aiohttp integration (client_key, check_http, check_ws, rate_limit_middleware)
  - core.url_utils: HTTP URL validation + normalization (stdlib only)
  - core.html_text: HTML→text extraction via stdlib html.parser
  - core.text_ranker: TF-IDF scorer + embedder-honouring ranking
  - core.web_crawler: BFS recursive async crawler with Fetcher protocol
  - core.memory_types: MemoryType + AccessLevel + DistanceMetric (RUFLO taxonomy)
  - core.hook_events: 19-event HookEvent + 5-level HookPriority (RUFLO)
  - teammate.contract: PeerStatus + MailboxMessage + PlanProposal + TeleportRequest
  - core.memory_consolidator: sweep_expired / dedup / compact_index / run_all
  - core.smart_retrieval: 5-phase pipeline (RRF + recency + MMR + session)
  - agents.plan_mode: directive + active plan note + gem mutator gating

Cada proyecto cliente tiene:
  - src/gemas_core/  (synced desde supernexus-v2, vendor copy)
  - src/gemas_client_overrides/  (preservado por sync, gemas client-specific)

Vendor copy + sync script (NO git submodule, NO pip package) para mantener
control total sobre la versión exacta y evitar dependencias externas.
"""
from .base import GemaBase, GemaManifest, ManifestSchema
from .llm_role_gema import LLMRoleGema, load_all_role_gemas
from .builders import (
    build_standard_gemas,
    list_standard_dedicated_ids,
    list_standard_role_ids,
    list_all_standard_ids,
)
from .dispatch import dispatch_gema, list_gema_methods
from .core.atomic_io import atomic_write_json, atomic_write_text
from .core.prompt_security import (
    UNTRUSTED_CONTEXT_HEADER,
    UNTRUSTED_CONTEXT_POLICY,
    is_untrusted_message,
    untrusted_context_message,
    untrusted_context_messages,
)
from .agents.plan_mode import (
    PLAN_MODE_DIRECTIVE,
    PLAN_MODE_KNOWN_MUTATORS,
    PLAN_MODE_READONLY_GEMAS,
    PlanNote,
    build_active_plan_note,
    is_mutating_gema,
    parse_plan_checklist,
    plan_mode_disabled_gemas,
    update_plan,
)
from .core.rate_limiter import RateLimiter
from .core.rate_limit_helpers import (
    check_http,
    check_ws,
    client_key,
    rate_limit_middleware,
)
from .core.rate_limit_unified import SafetyLimiter
from .core.rate_limiter_redis import RedisLimiterBackend, RedisRateLimiter
from .core.url_utils import (
    is_http_url,
    is_valid_url,
    normalize_url,
    parse_url,
)
from .core.html_text import (
    DEFAULT_SKIP_TAGS,
    TextExtractionStats,
    extract_text,
    extract_text_with_meta,
)
from .core.text_ranker import (
    Embedder,
    KeywordScorer,
    ScoredItem,
    cosine_similarity_vectors,
    euclidean_similarity_vectors,
    rank_content,
    tokenize,
)
from .core.web_crawler import (
    CrawledDoc,
    CrawlStats,
    Fetcher,
    RecursiveCrawler,
    extract_links,
)
from .workers.web_research import (
    WebResearchGem,
    WebResearchResult,
    web_research,
)
from .core.memory_types import (
    AccessLevel,
    DistanceMetric,
    MemoryType,
)
from .core.hook_events import (
    HookEvent,
    HookPriority,
)
from .teammate import (
    MailboxMessage,
    PeerStatus,
    PlanProposal,
    TeleportRequest,
)
from .core.memory_consolidator import (
    ConsolidationResult,
    DedupStrategy,
    MemoryBackend,
    MemoryEntry,
    compact_index,
    dedup,
    run_all,
    sweep_expired,
)
from .core.smart_retrieval import (
    RetrievalHit,
    SearchFn,
    SmartSearchOptions,
    SmartSearchResult,
    expand_query,
    make_search_fn,
    mmr_diversify,
    multi_query_search,
    recency_boost,
    rrf_fuse,
    session_diversify,
    smart_search,
)

__version__ = "1.10.0"
__all__ = [
    # Core
    "GemaBase",
    "GemaManifest",
    "ManifestSchema",
    "LLMRoleGema",
    "load_all_role_gemas",
    "build_standard_gemas",
    "list_standard_dedicated_ids",
    "list_standard_role_ids",
    "list_all_standard_ids",
    "dispatch_gema",
    "list_gema_methods",
    # atomic_io
    "atomic_write_json",
    "atomic_write_text",
    # prompt_security
    "UNTRUSTED_CONTEXT_POLICY",
    "UNTRUSTED_CONTEXT_HEADER",
    "untrusted_context_message",
    "untrusted_context_messages",
    "is_untrusted_message",
    # plan_mode
    "PLAN_MODE_DIRECTIVE",
    "PLAN_MODE_READONLY_GEMAS",
    "PLAN_MODE_KNOWN_MUTATORS",
    "plan_mode_disabled_gemas",
    "is_mutating_gema",
    "build_active_plan_note",
    "PlanNote",
    "parse_plan_checklist",
    "update_plan",
    # rate_limiter
    "RateLimiter",
    # rate_limit_helpers (v1.4.0 — aiohttp integration)
    "client_key",
    "check_http",
    "check_ws",
    "rate_limit_middleware",
    # rate_limit_unified (v1.9.0 — multi-purpose SafetyLimiter facade)
    "SafetyLimiter",
    # rate_limiter_redis (v1.10.0 — shared sliding-window via Redis)
    "RedisRateLimiter",
    "RedisLimiterBackend",
    # url_utils (v1.5.0 — stdlib HTTP URL validation)
    "is_valid_url",
    "is_http_url",
    "normalize_url",
    "parse_url",
    # html_text (v1.5.0 — stdlib HTML→text)
    "DEFAULT_SKIP_TAGS",
    "extract_text",
    "extract_text_with_meta",
    "TextExtractionStats",
    # text_ranker (v1.5.0 — stdlib TF-IDF + embedder hook)
    "Embedder",
    "KeywordScorer",
    "ScoredItem",
    "cosine_similarity_vectors",
    "euclidean_similarity_vectors",
    "rank_content",
    "tokenize",
    # web_crawler (v1.5.0 — async BFS recursive crawler)
    "Fetcher",
    "RecursiveCrawler",
    "CrawledDoc",
    "CrawlStats",
    "extract_links",
    # web_research_gem (v1.6.0 — RUFUS primitives → gem)
    "WebResearchGem",
    "WebResearchResult",
    "web_research",
    # memory_types (v1.7.0 — RUFLO taxonomy)
    "MemoryType",
    "AccessLevel",
    "DistanceMetric",
    # hook_events (v1.7.0 — RUFLO 19-event / 5-priority enums)
    "HookEvent",
    "HookPriority",
    # teammate/contract (v1.7.0 — multi-agent coordination dataclasses)
    "PeerStatus",
    "MailboxMessage",
    "PlanProposal",
    "TeleportRequest",
    # memory_consolidator (v1.8.0 — sweep/dedup/compact API)
    "ConsolidationResult",
    "DedupStrategy",
    "MemoryBackend",
    "MemoryEntry",
    "sweep_expired",
    "dedup",
    "compact_index",
    "run_all",
    # smart_retrieval (v1.8.0 — 5-phase search pipeline)
    "RetrievalHit",
    "SearchFn",
    "SmartSearchOptions",
    "SmartSearchResult",
    "expand_query",
    "rrf_fuse",
    "multi_query_search",
    "recency_boost",
    "mmr_diversify",
    "session_diversify",
    "smart_search",
    "make_search_fn",
]
