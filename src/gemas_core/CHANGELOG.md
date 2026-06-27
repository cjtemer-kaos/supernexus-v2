# CHANGELOG — gemas_core

## v1.10.0 (2026-06-06) — Redis-backed rate limiter

Completes Phase 4 of the rate-limit unification roadmap.
The in-process `RateLimiter` was sufficient for single-worker
deployments, but multi-worker and multi-machine deployments
need a shared bucket. The new `core.rate_limiter_redis`
module provides a drop-in `RedisRateLimiter` that uses Redis
sorted sets to implement the same sliding-window semantics
across processes.

### Added

#### `core/rate_limiter_redis.py` — `RedisRateLimiter`

- Atomic sliding-window check using a sorted set per key:
  `ZADD` + `ZREMRANGEBYSCORE` + `ZCARD` inside a single
  `MULTI/EXEC` pipeline.
- Unique member IDs (`<ms>:<uuid12>`) so two requests in the
  same millisecond don't collide in the sorted set.
- Lazy redis import — `redis-py` is a heavy dep; only
  imported when `RedisRateLimiter` is actually constructed.
- Drop-in surface: `check(key)`, `reset(key)`, `reset_all()`,
  `snapshot() -> Dict`, `max_requests`, `window` — same as
  the in-process `RateLimiter`.
- **Fail-open on Redis errors**: if the connection drops, the
  `check` returns `True` rather than denying real users.
  Rationale: an unreachable limiter is less harmful than an
  unreachable service. Callers that need fail-closed should
  wrap `check` in their own try/except.
- `reset_all()` uses `SCAN` + `DEL` to avoid blocking the
  Redis server on large keyspaces.
- `key_prefix` and `redis_url` (or pre-built `client`) are
  configurable so two limiters can co-exist on one Redis.

#### `core/rate_limit_unified.py` — extended

- `SafetyLimiter(backend="memory"|"redis", redis_kwargs=...)`
  now accepts a backend selector. When `backend="redis"`,
  every purpose is built from `RedisRateLimiter` with the
  shared `key_prefix` / `redis_url`.
- Pre-built limiters (a `RateLimiter` or `RedisRateLimiter`
  instance) can be passed directly instead of a config
  dict — useful when the caller has custom logic attached
  to a specific instance.
- `redis_kwargs` is forwarded to `RedisRateLimiter`:
  `redis_url`, `key_prefix`, `client`.

### Test totals

- supernexus-v2 gemas_core: **619/619 pass** (was 603, +16 new
  in `tests/test_rate_limiter_redis.py` (11) and
  `tests/test_rate_limit_unified.py` (5 more)).
- 2 new public symbols added (`RedisRateLimiter`,
  `RedisLimiterBackend`).
- Tests that need a real Redis are auto-skipped on machines
  where `127.0.0.1:6379` is unreachable (e.g. CI without
  docker).

### Cross-version constraints honoured

- ❌ Did NOT add `redis` to a hard `requirements.txt` — it's
  an optional dep, only imported when the Redis backend is
  actually used.
- ❌ Did NOT change the in-process `RateLimiter` API — it's
  still the default.
- ❌ Did NOT touch `nexus_memory.db` schema or any other
  persistent store.
- ✅ The Redis backend is fail-open (Redis outage ≠ service
  outage).

---

## v1.9.0 (2026-06-06) — Unified rate-limiting facade

Completes Phase 3 of the rate-limit unification roadmap.
The new `core.rate_limit_unified` module is the single
source of truth for the three projects' per-IP / per-route
limiters, replacing the per-project `RateLimiter` ports that
existed alongside gemas_core since v1.3.0.

### Added

#### `core/rate_limit_unified.py` — `SafetyLimiter` facade

- `SafetyLimiter(**configs)` — multi-purpose facade holding
  one `RateLimiter` per named purpose (`default`, `chat`,
  `rcon`, etc.). Unknown purposes fall back to `default`.
- `check(client_id, *, purpose="default") -> (bool, dict)` —
  legacy-compatible shape: on denial `info` includes
  `reason`, `retry_after`, `retry_after_seconds`,
  `max_requests`, `window_seconds`, `purpose`.
- `check_request(request, *, purpose, prefix) -> (bool, dict)` —
  extracts the client key from an aiohttp request (honors
  `X-Forwarded-For`, falls back to `remote`).
- `check_request_or_429(request, ...) -> Optional[Response]` —
  returns a 429 `web.json_response` if blocked, else `None`.
  Single-line gate for handlers.
- `gate_request(request, ...)` — alias for the above.
- `reset(target=None, *, purpose=None)` — granular admin
  reset (specific client × specific purpose).
- `add_purpose(name, max_requests, window_seconds)` — dynamic
  purpose registration (idempotent).
- `status() -> Dict` — observability dump (per-purpose config
  + live bucket sizes).
- `purposes` property — read-only tuple of configured purpose
  names.

### Wired

#### `optimization/api_safety.py` (supernexus-v2 + sfdx)

- The local `RateLimiter` class (odysseus port with burst
  detection) is now a thin wrapper around
  `gemas_core.core.rate_limit_unified.SafetyLimiter`. The
  legacy `RateLimitConfig` dataclass is kept as a back-compat
  shim with `burst_limit`/`burst_window` fields (no longer
  consumed by the limiter, but kept so external imports
  don't break).
- `SafetyManager.check_rate_limit(client_id)` continues to
  return `(bool, dict)` — the call sites in `handle_chat`
  and WS handlers are unchanged.
- Burst detection is dropped. No callers in the SuperNEXUS
  v2.0 surface relied on it. If a project needs it, add a
  separate `RateLimiter` instance with a tight window
  alongside the main one.

#### `src/api/server.py` (sfdx only)

- The global `rate_limit_middleware(200, 60_000)` (legacy
  `src.core.rate_limiter.rate_limit_middleware`) is replaced
  with `gemas_core.core.rate_limit_helpers.rate_limit_middleware`
  fed by a single global `RateLimiter(max_requests=200,
  window_seconds=60)`.
- `src/core/rate_limiter.py` (86 lines, the simple
  odysseus port) is **deleted** — confirmed by grep that
  no other module imports it.

### Test totals

- supernexus-v2 gemas_core: **603/603 pass** (was 582, +21 new
  in `tests/test_rate_limit_unified.py`).
- 1 new public symbol added (`SafetyLimiter`).

### Cross-version constraints honoured

- ❌ Did NOT change the legacy `check_rate_limit(client_id)`
  return shape — every existing call site still works.
- ❌ Did NOT modify `latamrust-nexus` (already on the
  unified `RateLimiter` since v1.4.0).
- ❌ Did NOT touch `nexus_memory.db` schema or
  `self_learning_loop.py` (additive).
- ✅ `latamrust-nexus` continues to work unchanged because
  the per-route `chat_limiter` / `rcon_limiter` in
  `src/api/rate_limiters.py` is exactly the same class.

---

## v1.8.0 (2026-06-06) — Memory consolidator + smart retrieval

Ports the algorithm subset of RUFLO v3's
`@claude-flow/memory/src/consolidator.ts` and
`@claude-flow/memory/src/smart-retrieval.ts` (ADR-090, ADR-125
Phase 4) to gemas_core. **All additive** — no replacement of
`self_learning_loop.py`, no schema changes to
`nexus_memory.db`, no LLM dependency added.

### Added

#### `core/memory_consolidator.py` — maintenance API

- `MemoryBackend` (Protocol): minimal `list_all()`, `delete(id)`,
  `update(entry)` contract. Caller passes any backend (e.g. a
  thin wrapper over `nexus-sovereign.add_observation`).
- `MemoryEntry` (dataclass): `id`, `content`, `content_hash`,
  `created_at`, `ttl_s`, `tags`, `metadata`. `is_expired()`
  helper.
- `DedupStrategy` (enum): KEEP_NEWEST, KEEP_OLDEST, MERGE_TAGS.
- `ConsolidationResult` (dataclass): swept + deduped + compacted
  counters, deleted_ids, kept_ids, `total_processed` property,
  `to_dict()`.
- `sweep_expired(backend, now=None)`: deletes entries whose TTL
  has elapsed.
- `dedup(backend, strategy)`: collapses entries with the same
  `content_hash`. Three strategies; MERGE_TAGS unions all tags
  into the kept entry.
- `compact_index(backend)`: NOP for SQLite-based backends;
  records 0 compacted for the audit log.
- `run_all(backend, dedup_strategy, now)`: runs all 3 in order
  (sweep → dedup → compact). Order matters: dedup BEFORE sweep
  would re-allocate IDs to expired entries.

#### `core/smart_retrieval.py` — 5-phase search pipeline

- `RetrievalHit` (dataclass): `id`, `text`, `score`,
  `created_at`, `session_id`, `metadata`.
- `SearchFn` (Protocol): any callable
  `(query, *, top_k) -> List[RetrievalHit]`.
- `SmartSearchOptions` (dataclass): `multi_query`,
  `recency_boost`, `diversity_mmr`, `session_diversity` toggles
  + `n_query_variants`, `recency_half_life_days`, `mmr_lambda`,
  `rrf_k` knobs.
- `SmartSearchResult` (dataclass): `hits`, `phases_run`,
  `n_input_queries`, `to_dict()`.

Phases:
  1. `expand_query(query, n_variants)`: original + stopword-stripped
     + substring variants. stdlib-only; no LLM.
  2. `multi_query_search(queries, search_fn)`: fans out to the
     `SearchFn` for each variant. SearchFn failures are caught
     and logged.
  3. `rrf_fuse(result_lists, k=60)`: Reciprocal Rank Fusion;
     each hit's score = sum(1 / (k + rank)).
  4. `recency_boost(hits, half_life_days)`: half-life decay
     re-scoring; hits without `created_at` get 0.5 (neutral).
  5. `mmr_diversify(hits, top_k, lam, similarity_fn)`: greedy MMR
     with default Jaccard-on-words similarity.
  6. `session_diversity(hits, top_k, per_session_cap=3)`:
     round-robin across distinct sessions; runs before MMR if
     there are >=2 sessions and the toggle is on.

- `smart_search(query, search_fn, options, top_k)`: orchestrates
  the 5 phases based on options; tags each phase that ran.
- `make_search_fn(records)`: convenience builder for an
  in-memory search function over a static record list (useful
  for tests + small corpora).

### Test totals

- supernexus-v2 gemas_core: **582/582 pass** (was 536, +46 new).
- 25 new public symbols added (4 from consolidator: 1 protocol +
  2 dataclasses + 4 functions + 1 enum; 12 from smart_retrieval:
  1 protocol + 3 dataclasses + 9 functions).

### Cross-version constraints honoured

- ❌ Did NOT replace `self_learning_loop.py` (additive).
- ❌ Did NOT replace `retrieval_search` or `brain_recall` MCP
  tools (additive; caller chooses to use the new pipeline).
- ❌ Did NOT modify `nexus_memory.db` schema.
- ❌ Did NOT add LLM dependency (stdlib-only query expansion).
- ✅ Both modules operate on caller-supplied data; no I/O
  performed by the core itself.

---

## v1.7.0 (2026-06-06) — RUFLO enums + teammate contracts

Ports the protocol-contract subset of RUFLO v3
(`@claude-flow/memory`, `@claude-flow/hooks`,
`plugins/teammate-plugin`) to gemas_core. **All additive** —
no replacement of existing modules, no schema-breaking changes
to `message_board.db`, no new runtime plumbing.

### Added

#### `core/memory_types.py` — taxonomy enums

- `MemoryType` (10 values): FACT, EPISODE, SKILL, PATTERN,
  INTENT, OBSERVATION, PLAN, CHECKPOINT, PREFERENCE, TASK_RESULT.
  - `MemoryType.persistent()` → 6 types meant to survive across
    sessions (FACT, SKILL, PATTERN, PREFERENCE, PLAN, TASK_RESULT).
  - `MemoryType.transient()` → 4 types meant to live only for
    the current session (EPISODE, INTENT, OBSERVATION, CHECKPOINT).
  - The two classes partition the full set.
- `AccessLevel` (4 values): PRIVATE, TEAM, SHARED, PUBLIC.
  - `AccessLevel.ordered()` returns them from most-restrictive
    to least-restrictive.
- `DistanceMetric` (4 values): COSINE, EUCLIDEAN, DOT, MANHATTAN.

#### `core/hook_events.py` — 19-event / 5-priority enums

- `HookEvent` (19 values across 6 categories): lifecycle,
  agent/task, tool/MCP, memory, coordination, safety.
- `HookPriority` (5 levels, lower = higher priority): CRITICAL,
  HIGH, NORMAL, LOW, DEFERRED.
  - `HookPriority.blocking()` returns the priorities that should
    block execution (CRITICAL + HIGH).
- **No runtime port.** The TypeScript EventEmitter-based hook
  executor is not ported — gemas_core keeps using
  `agents/plan_mode.py` for actual gating.

#### `teammate/contract.py` — multi-agent coordination dataclasses

- `PeerStatus` (3 values): HEALTHY, DEGRADED, OFFLINE.
  - `PeerStatus.reachable()` → HEALTHY + DEGRADED.
- `MailboxMessage` (dataclass): `peer_id`, `payload`, `ttl_s`,
  `enqueued_at`, `msg_id`; `is_expired()` and `to_dict()`.
- `PlanProposal` (dataclass): `id`, `steps`, `requires`,
  `approvals`, `proposed_at`, `proposed_by`.
  - `is_approved()` — N/2 + 1 quorum rule.
  - `is_rejected()` — at least one required peer explicitly said
    False. Required peers that haven't responded are NOT
    counted as rejections.
  - `pending_approvers()` — required peers that haven't responded
    yet.
  - `record_approval(peer_id, approved)` — record a vote.
- `TeleportRequest` (dataclass): `from_peer`, `to_peer`,
  `session_state`, `requested_at`, `request_id`, `accepted`;
  `accept()` and `to_dict()`.

#### `teammate/__init__.py`

- Re-exports the 4 public names from `teammate/contract.py`.
  Future v1.8+ work may add `teammate/coordinator.py` (helper
  that drives the existing `send_message` MCP tool) and
  `teammate/transport.py` (sqlite-backed mailbox — additive to
  `message_board.db`).

### Python 3.10 compatibility

- `StrEnum` was added in Python 3.11; this project targets 3.10.
  A small `str + Enum` polyfill is included in each module that
  needs it. The polyfill is a no-op on 3.11+.

### Test totals

- supernexus-v2 gemas_core: **536/536 pass** (was 483, +53 new).
- 12 new public symbols added (`MemoryType`, `AccessLevel`,
  `DistanceMetric`, `HookEvent`, `HookPriority`, `PeerStatus`,
  `MailboxMessage`, `PlanProposal`, `TeleportRequest` + 3
  methods: `pending_approvers`, `accept`, `is_expired`).

### Cross-version constraints honoured

- ❌ Did NOT replace any of the 6 dedicated workers.
- ❌ Did NOT replace `dispatch_gema`.
- ❌ Did NOT modify `message_board.db` schema.
- ❌ Did NOT port TypeScript EventEmitter hook runtime.
- ✅ All proposals are additive new modules + new symbols.

---

## v1.6.0 (2026-06-05) — WebResearchGem

Wraps the v1.5.0 RUFUS primitives (`RecursiveCrawler` +
`rank_content`) behind the standard `GemaBase` interface, exposing
a "research this query against these URLs" workflow as a 6th
dedicated worker.

### Added

#### `workers/web_research.py` — WebResearchGem

- `WebResearchGem` extends `GemaBase` with `name="web_research"`,
  `category="research"`.
- `bind_fetcher(fetcher)` / `bind_embedder(embedder)` for
  dependency injection — keeps gemas_core aiohttp-free at the
  module level (the default `_AiohttpFetcher` is created lazily on
  first use).
- `research(query, start_urls, *, max_depth=2, max_pages=25,
  top_k=None) -> WebResearchResult` is the main API: validates
  start URLs, crawls with BFS, ranks with `KeywordScorer` (or the
  injected `Embedder`), returns a structured result.
- `execute(task, context)` parses `context` as JSON (with
  `start_urls`, `max_depth`, `max_pages`, `top_k` keys) for
  compatibility with `dispatch_gema`.
- `WebResearchResult` (NamedTuple) wraps `docs`, `ranked`,
  `fetch_attempts`, `fetch_failures`, `skipped_urls`,
  `invalid_start_urls`; `to_dict()` for serialization.
- Convenience function `web_research(query, start_urls, *,
  fetcher=None, embedder=None, max_depth=2, max_pages=25, top_k=None)`
  for one-shot use.
- `search_history` (list of dicts) for cross-call audit, matching
  the `ScholarGem` pattern.
- 27 new tests including manifest contract, GemaBase interface,
  execute() JSON parsing, default vs injected fetcher/embedder,
  invalid start URL handling, empty results, top_k, kwargs
  passthrough.

### Changed

- `builders.STANDARD_DEDICATED_IDS`: 5 → 6 (added `"web_research"`).
- `builders._class_name()`: now handles snake_case compound IDs
  (e.g. `"web_research" → "WebResearchGem"`). Previously it only
  supported single-word IDs via `str.capitalize()`.
- `workers/ayuda.py`:
  - `full_catalog()`: `llm_dedicated` 5 → 6 entries; total
    23 → 24.
  - `role_names`: added `"web_research"` (sorted by length
    descending for word-boundary matching).
- `tests/test_builders.py`: `len(dedicated) == 5` → 6;
  `len(all) == 23` → 24.
- `tests/test_workers.py`: catalog assertions updated
  (24 + N client gemas).
- `tests/test_prompter.py`: 23 → 24 total gemas.

### Test totals

- supernexus-v2 gemas_core: **483/483 pass** (was 456, +27 new).
- 6 public symbols added (`WebResearchGem`, `WebResearchResult`,
  `web_research`; same 3 + existing v1.5.0 batch already counted).

### Refinements over v1.5.0 crawler

- Lazy aiohttp import: gemas_core no longer requires aiohttp for
  import-time; the default fetcher is created on first use. This
  mirrors the pattern from `core/rate_limit_helpers.py`.
- Better separation: the `Fetcher` protocol stays in
  `core.web_crawler`; the gem is a thin wrapper, not a duplicate
  of the crawl logic.
- Default `max_pages=25` (was unlimited) to prevent runaway
  crawls on a single `research()` call.

---

## v1.5.0 (2026-06-05) — RUFUS web-research primitives

## v1.5.0 (2026-06-05) — RUFUS web-research primitives

Ports the stdlib-portable patterns from `tensorsofthewall/RUFUS`
(web scraper for RAG) into gemas_core, with **zero new
dependencies**. Each module is usable on its own and composes
into a complete "scrape a website, score its content against a
prompt" pipeline when a caller injects a `Fetcher` + an
`Embedder`.

### Added

#### `core/url_utils.py` — stdlib HTTP URL validation

- `is_valid_url(url, *, schemes=("http","https")) -> bool`
  — defensive against non-string / empty / whitespace / XSS
  inputs (rejects `javascript:`, `data:`, etc.).
- `is_http_url(url) -> bool` — convenience alias.
- `parse_url(url) -> Optional[_UrlParts]` — returns a
  NamedTuple of (scheme, netloc, path, params, query, fragment)
  or None for invalid/relative URLs.
- `normalize_url(url, base="") -> Optional[str]` — resolves a
  relative URL against a base and validates the result.
- 33 tests including IDN, fragment-only, scheme-only, base
  validation, anchor inheritance of the base query, etc.

#### `core/html_text.py` — stdlib HTML→text extraction

- `extract_text(html, *, skip_tags=None) -> str` — uses
  `html.parser.HTMLParser` to drop noise tags (default:
  `style`, `script`, `nav`, `aside`, `footer`, `header`,
  `noscript`, `svg`, `form`) and collapse whitespace.
- `extract_text_with_meta(html, *, skip_tags=None) -> TextExtractionStats`
  — same plus diagnostic counters (input/output chars,
  dropped chunks, compression ratio).
- 33 tests including entity decoding, comments, malformed
  HTML, case-insensitive tag matching, and the full skip
  set locked down in `DEFAULT_SKIP_TAGS`.

#### `core/text_ranker.py` — stdlib TF-IDF + embedder hook

- `KeywordScorer` — TF-IDF with smoothed IDF
  (`ln((N+1)/(df+1)) + 1`), stdlib only, no numpy.
- `rank_content(ref, candidates, *, embedder=None, metric="cosine", top_k=None)`
  — public entry point. Without an embedder → keyword
  scoring. With an `Embedder` (any object with
  `embed(List[str]) -> List[List[float]]`) → cosine or
  euclidean on the embeddings.
- `Embedder` — `typing.Protocol` (structural). A real impl
  can wrap Ollama's `nomic-embed-text` or any other backend.
- `cosine_similarity_vectors` / `euclidean_similarity_vectors`
  — exposed helpers (euclidean returns `1/(1+d)` to match
  RUFUS's convention).
- `tokenize(text)` — lower-case, drop short tokens (<3
  chars), keep hyphenated/underscored words together.
- `ScoredItem` — NamedTuple `(text, score)` for `rank_content`
  results.
- 40 tests including tie-breaking determinism, embedder
  dispatch, metric kwarg, top_k truncation, unicode tokens.

#### `core/web_crawler.py` — async BFS recursive crawler

- `Fetcher` protocol — `runtime_checkable`; any object with
  `async fetch(url) -> Optional[str]` works. Returning None
  signals a fetch failure.
- `RecursiveCrawler(fetcher, *, max_depth=2, max_pages=100,
  max_concurrent=10, request_delay=0.0)` — BFS by depth
  level, with `asyncio.Semaphore` to cap concurrent fetches
  and a delay lock for polite throttling.
- `crawl(start_urls) -> List[CrawledDoc]` /
  `crawl_with_stats(start_urls) -> CrawlStats` — the second
  variant returns diagnostic counters
  (`fetch_attempts`, `fetch_failures`, `urls_visited`).
- `extract_links(html, base="")` — stdlib regex-based
  `<a href="...">` extraction with `mailto:` / `javascript:`
  / fragment-only / data: filtering, in source order, deduped
  within the page.
- `reset()` — clears the dedup set so the next crawl
  re-fetches. Useful for periodic refreshes.
- Constructor validates `max_depth >= 0`, `max_pages > 0`,
  `max_concurrent > 0`, `request_delay >= 0`.
- 36 tests including BFS dedup, cycle detection,
  `max_concurrent` semaphore verification, throttling delay,
  invalid-URL filtering, malformed HTML, fetch failure
  handling, fetch exceptions (treated as failure, not crash).

### Why port RUFUS into gemas_core

RUFUS is a thin web scraper for RAG (~175 lines). The
patterns we care about (`is_valid_url`, `extract_text`,
recursive crawl with depth + dedup, `rank_content`) are
useful for any "scrape a site, score its pages against a
prompt" workflow. RUFUS's heavy deps (BeautifulSoup, torch,
google-generativeai) are out — the stdlib versions cover
90% of the use case and the embedder hook lets a caller
inject Ollama for the other 10% without forcing gemas_core
to depend on it.

### Composition example (caller's code, not in gemas_core)

```python
import aiohttp
from gemas_core import (
    RecursiveCrawler, extract_text, KeywordScorer,
    rank_content, is_valid_url,
)

class AiohttpFetcher:
    async def fetch(self, url):
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                return await r.text() if r.status == 200 else None

crawler = RecursiveCrawler(AiohttpFetcher(), max_depth=2)
docs = await crawler.crawl(["https://example.com/"])
ranked = rank_content(ref=prompt, candidates=[d.text for d in docs])
```

### Backward compatibility

- No existing symbol changed. v1.4.0 tests still pass on
  v1.5.0 without modification.
- 314 → **456** tests in gemas_core (+142 new).
- 52 public symbols (was 36 in v1.4.0).

### v1.5+ candidates (not in this release)

- Unify supernexus-v2 / sfdx rate limiting behind
  `check_http` (single source of truth).
- Redis-backed `RateLimiter` for multi-worker deployments.
- A `gemas_client_overrides/web_research_gem.py` worker
  that uses the v1.5.0 primitives + aiohttp + Ollama to
  implement the full "scrape → score → return top-N"
  workflow as a first-class gem.

---

## v1.4.0 (2026-06-05)

### Added

#### `core/rate_limit_helpers` — aiohttp integration for `RateLimiter`

- Four small helpers that glue the v1.3.0 `RateLimiter` into an
  aiohttp app:
  - `client_key(request, *, prefix="")` — extracts a stable key from
    `X-Forwarded-For` (leftmost hop = original client) or
    `request.remote`. The `prefix` lets callers namespace their
    keys (e.g. `chat:ip-1` vs `rcon:ip-1:server1`).
  - `check_http(limiter, key)` — returns a 429 `web.json_response`
    with `Retry-After` header if the key is blocked, else `None`.
    Handlers short-circuit on a non-`None` return. This is the
    **per-handler** pattern: use it when different routes need
    different limits.
  - `check_ws(limiter, ws, key)` — for WebSocket message loops.
    Sends `{"type": "error", "text": "rate limit exceeded"}` and
    closes the socket with code 1008 (policy violation) if blocked,
    returns `True` if allowed. WebSockets can't return a 429 once
    the upgrade has happened, so this is the only signal we have.
  - `rate_limit_middleware(limiter, *, key_fn=None)` — aiohttp
    middleware factory for blanket protection. The middleware
    variant covers HTTP routes only; per-message WS handling
    still needs `check_ws` inside the loop.
- **Lazy aiohttp import**: the module imports `aiohttp.web` only
  when a helper is *called*, not at import time. Keeps gemas_core
  importable in environments where aiohttp isn't installed
  (e.g. projects that only need `RateLimiter` itself, or test
  runners that mock the import).

#### Wired into `latamrust-nexus` end-to-end

- `src/api/rate_limiters.py` — module that owns the two shared
  `RateLimiter` instances. Lives in a separate module to break
  the import cycle between `latamrust_server.py` and
  `latamrust_routes.py`.
- `src/api/latamrust_server.py`:
  - `POST /api/chat` and `POST /api/chat/ask` — 60 req/min per
    IP, prefixed `chat:`.
  - `GET /api/rust/rcon/ws` — per-message check inside the
    `async for msg in ws:` loop, key `rcon:<ip>:<server>`,
    30 req/min. Per-WS-connection, per-server, so a single
    client can have several WS open to different servers with
    independent budgets.
- `src/api/latamrust_routes.py`:
  - `POST /api/rust/rcon` — 30 req/min per `(IP, server)`.
    Body is parsed *before* the limit check so the bucket
    reflects the actual server, not just the IP.
- `src/api/server.py` (the fork):
  - `GET /api/rcon/servers` and `POST /api/rcon/command` —
    same `rcon_limiter` (30 req/min) with prefix `rcon-fork:`
    so the two RCON namespaces don't share buckets.

#### Integration tests in `latamrust-nexus`

- `tests/test_v140_rate_limit.py` — 13 tests covering: shared
  limiter defaults (60/30 per minute), `check_http` allow/deny,
  429 body shape, `Retry-After` header, `check_ws` allow/deny
  + error frame + close code 1008, `client_key` from remote /
  X-Forwarded-For / prefix, middleware factory returns a
  callable.

#### Why not `supernexus-v2` and `sfdx`?

Both already have a `backend.safety.check_rate_limit(client_ip)`
call at the top of `handle_chat`. The new `RateLimiter` would be
duplicative unless we replace the safety module. That's a bigger
refactor than v1.4.0 — left for a future v1.5+ that unifies the
two rate-limit backends behind a single interface.

### Test count

297 → **314** in the standard test suite (+17 in
`tests/test_rate_limit_helpers.py`). latamrust-nexus additionally
gets +13 in `tests/test_v140_rate_limit.py` (327 total).

## v1.3.0 (2026-06-05)

### Added

#### `core/rate_limiter` — sliding-window rate limiter, in-memory

- Ported from `pewdiepie-archdaemon/odysseus`
  (`src/rate_limiter.py`, 49 lines source). The odysseus version
  was a 49-line snippet; the v1.3.0 port is ~110 lines because it
  adds the observability/admin surface (`reset`, `reset_all`,
  `snapshot`) plus thread safety via `threading.Lock` and edge-case
  validation (zero / negative windows, empty keys, denied timestamps
  must not extend the block window).

- `RateLimiter(max_requests, window_seconds)` — single class,
  generic, key-based. Use it for any per-key rate limit (per-IP
  for unauthenticated endpoints, per-user for authenticated ones,
  per-tool for shell hooks, etc.).

- `check(key) -> bool` returns `True` if the request fits inside
  the sliding window, `False` if it should be blocked. Allowed
  requests are timestamped; **denied requests are not** (otherwise
  an attacker could extend the block window by sending a flood of
  requests past the limit).

- `reset(key)` clears one key's timestamps; `reset_all()` clears
  the whole limiter. Useful for tests, admin overrides, and
  post-authentication refresh.

- `snapshot() -> Dict[str, int]` returns the current per-key
  timestamp counts for observability dashboards and admin tools.

- `_maybe_cleanup()` purges keys whose last timestamp has slid
  out of the window. Runs inline on every `check` call (no
  background thread, no thread to start/stop/leak), gated by
  a `_cleanup_interval` of `max(window * 2, 120)` so long
  windows don't accumulate stale keys.

- **Thread safety**: a single `threading.Lock` guards the
  internal `Dict[str, List[float]]`. 24 tests cover basic
  allow/deny, sliding window, per-key isolation, concurrent
  threads obeying the limit, partial window expiry, denied
  requests not extending the block, reset semantics, snapshot
  shape, and edge cases (max=0, max=1, max=-1, window=0,
  window=-1, empty key).

- **In-process only**: storage is in-memory, not shared across
  processes. Fine for a single FastAPI worker; multi-worker
  deployments need a Redis-backed limiter. The class is small
  enough (~110 lines) that swapping the backend later is a
  one-evening task.

### Test count

273 → **297** in the standard test suite (+24 in
`tests/test_rate_limiter.py`).

## v1.2.0 (2026-06-05)

### Added

Three new submodules ported from `pewdiepie-archdaemon/odysseus` (branch
`dev`, MIT, 2026-05-31). Mirror local:
`D:\ias\proyectos\autopsia\odysseus\`.

#### `core/atomic_io` — crash-safe JSON/text writes

- `atomic_write_json(path, data, *, indent=None)` and
  `atomic_write_text(path, text)` write to `<path>.tmp.<pid>.<tid>`,
  fsync, then `os.replace` into place. Atomic on POSIX + modern
  Windows for same-FS renames.
- Tmp suffix uses `pid + thread id` so concurrent async FastAPI
  handlers in the same process don't collide.
- On any error after the tmp file is created (write, fsync, replace,
  even `KeyboardInterrupt`), the tmp file is cleaned up before the
  exception propagates — no orphaned `*.tmp.*` left behind.
- Original file (if any) is preserved because `os.replace` only runs
  after a successful write+fsync.
- Use this everywhere a JSON or text config is persisted: `auth.json`,
  `sessions.json`, `settings.json`, library DB, brain state, etc.

#### `core/prompt_security` — anti-injection wrapper

- `untrusted_context_message(label, content) -> dict` and
  `untrusted_context_messages(label, contents) -> list` wrap retrieved
  content in a sentinel-bounded `role: "user"` message with
  `metadata.trusted = False` and `metadata.source = label`.
- Sentinels: `<<<UNTRUSTED_SOURCE_DATA>>>` ... `<<<END_UNTRUSTED_SOURCE_DATA>>>`.
- `is_untrusted_message(msg) -> bool` for downstream audit/filtering.
- Exported constants: `UNTRUSTED_CONTEXT_POLICY` (for system-prompt
  splicing) and `UNTRUSTED_CONTEXT_HEADER` (auto-prepended to every
  wrapped message).
- **ScholarGem and BibliotecaGem** now expose safe `*_as_chat_messages()`
  methods that wrap each result before it ever reaches the LLM. The
  raw `research()` / `search()` API is unchanged for backwards compat.

#### `agents/plan_mode` — user-approved plan gating

- `PLAN_MODE_DIRECTIVE` (constant) — system-prompt block that
  overrides everything else, instructing the agent to PROPOSE not
  EXECUTE.
- `PLAN_MODE_READONLY_GEMAS` (allowlist: scholar, biblioteca, sage,
  prompter) and `PLAN_MODE_KNOWN_MUTATORS` (backstop: code, engineer,
  devops, creative, music, vision, design, trainer, producer,
  debugger, ayuda). The two sets are disjoint.
- `plan_mode_disabled_gemas()` — returns the mutator set (the
  dispatch layer is denylist-based).
- `is_mutating_gema(name) -> bool` — fails CLOSED: unknown / empty /
  non-string defaults to mutator.
- `build_active_plan_note(approved_plan) -> str` — re-injects the
  approved plan into the system prompt every turn so a long plan on
  a weak model survives history truncation.
- `parse_plan_checklist(text) -> list` and
  `update_plan(items, completed) -> str` for live progress rendering.
- `PlanNote` dataclass carries the plan + step cursor + progress
  fraction.

#### `dispatch_gema` — plan_mode + disabled_gemas support

- New optional kwargs: `plan_mode: bool = False` and
  `disabled_gemas: Optional[FrozenSet[str]] = None`. Both default to
  off — existing callers see zero behavior change.
- When `plan_mode=True` and the gema is a known mutator (or unknown
  — fail closed), execution is blocked before any method runs and
  the returned dict includes `plan_mode_blocked: True` plus a
  human-readable error.
- `disabled_gemas` is the explicit override channel: an orchestrator
  that maintains its own blocklist can pass it directly and skip the
  default `plan_mode` logic.

### Tests

- **+108 tests nuevos**:
  - 23 in `test_atomic_io.py` (basic, overwrite, JSON, failure
    cleanup, nested dirs, unicode, thread-id suffix, etc.)
  - 28 in `test_prompt_security.py` (sentinel wrap, label passthrough,
    JSON serializable, adversarial injection, etc.)
  - 10 in `test_prompt_security_integration.py` (Scholar and
    Biblioteca wrapping end-to-end)
  - 37 in `test_plan_mode.py` (directive, mutator detection, allowlist
    / backstop disjoint, parse checklist, update plan, PlanNote
    progress)
  - 10 in `test_dispatch_plan_mode.py` (plan_mode off → regression,
    plan_mode blocks mutators, allowlist runs, unknown fails closed,
    explicit blocklist override)
- **Total: 273/273 pass** (antes 165) en 3.42s.

### Public API

- `__version__ = "1.2.0"`
- `gemas_core.__all__` ahora incluye `atomic_write_json`,
  `atomic_write_text`, `UNTRUSTED_CONTEXT_POLICY`,
  `UNTRUSTED_CONTEXT_HEADER`, `untrusted_context_message`,
  `untrusted_context_messages`, `is_untrusted_message`,
  `PLAN_MODE_DIRECTIVE`, `PLAN_MODE_READONLY_GEMAS`,
  `PLAN_MODE_KNOWN_MUTATORS`, `plan_mode_disabled_gemas`,
  `is_mutating_gema`, `build_active_plan_note`, `PlanNote`,
  `parse_plan_checklist`, `update_plan`.

### Distribución

- Source canónica sigue en `supernexus-v2/src/gemas_core/`.
- Sync a `latamrust-nexus` y `sfdx` via `scripts/sync_gemas_core.py --all`.

---

## v1.1.0 (2026-06-05)

### Added

- **PrompterGem** — 5ª gema dedicated, promovida desde role-LLM.
  - `gemas_core/workers/prompter_knowledge.py` — knowledge base estática con
    13 templates (A-M) + 37 credit-killing patterns en 6 categorías
    (task/context/format/scope/reasoning/agentic).
  - `gemas_core/workers/prompter.py` — `PrompterGem` con `execute()` (análisis
    estático), `optimize()` (refinamiento vía Ollama inyectable), `detect_tool()`
    y `audit()` (pipeline paso a paso).
  - Helpers: `get_template`, `list_templates`, `list_patterns`, `get_pattern_by_id`,
    `detect_pattern`, `detect_target_tool`, `is_reasoning_model`,
    `format_with_template`, `pick_template_for`, `get_knowledge_summary`,
    `get_kb_metadata`.
  - Pipeline de 7 pasos: detect target tool → extract 9 dimensions → pick
    template → detect patterns → token audit → deliver → warnings.
  - Hard rules aplicadas: NO CoT para reasoning-native models (pattern 27),
    warnings cuando se detecta conflict.
  - Knowledge base portada de **nidhinjs/prompt-master v1.6.0** (MIT, 8.9k stars).
    Mirror local: `D:\ias\proyectos\autopsia\prompt-master\`.

### Changed

- **Builders**: `STANDARD_DEDICATED_IDS` ahora 5 entries (era 4).
  `STANDARD_ROLE_IDS` ahora 18 (era 19, `prompter` movido a dedicated).
  Total sigue siendo 23.
- **AyudaGem**: `full_catalog()` ahora retorna 5 `llm_dedicated` + 18
  `llm_role_count` (antes 4+19). `role_names` lista las 23 gemas
  (incluye `ayuda` y `prompter` para keyword detection).
- **`data/gemas/prompter.json`**: actualizado a v2.1.0, `main` apunta a
  `gemas_core.workers.prompter.PrompterGem`. Manifest preservado para
  metadata pero el builder prefiere el dedicated worker.

### Tests

- **+98 tests nuevos** (64 en `test_prompter_knowledge.py` + 34 en
  `test_prompter.py`). Total: **165/165 pass** (antes 67).
- 3 tests existentes actualizados al nuevo conteo (5+18=23).

### Distribución

- Source canónica sigue en `supernexus-v2/src/gemas_core/`.
- Sync a `latamrust-nexus` y `sfdx` via `scripts/sync_gemas_core.py --all`.

---

## v1.0.0 (2026-06-05)

### Initial release

Estándar canónico de gemas para proyectos SuperNEXUS. Define el contrato y la
implementación base de las 23 gemas estándar (4 dedicated + 19 role-LLM).

### Estructura

- `gemas_core/base.py` — `GemaBase` ABC + `GemaManifest` dataclass
- `gemas_core/llm_role_gema.py` — `LLMRoleGema` (dispatcher Ollama)
- `gemas_core/builders.py` — `build_standard_gemas()` (4+19 = 23)
- `gemas_core/dispatch.py` — `dispatch_gema()` con `inspect.signature`
- `gemas_core/manifest_schema.py` — JSON schema + `validate_manifest()`
- `gemas_core/workers/` — 4 workers: `AyudaGem`, `ScholarGem`, `SageGem`, `BibliotecaGem`
- `gemas_core/tests/` — 67 tests unitarios (pytest)
- `gemas_core/README.md` — documentación completa

### Distribución

- **Source canónica:** `supernexus-v2/src/gemas_core/`
- **Vendor copy:** `latamrust-nexus/src/gemas_core/`, `sfdx/nexus/src/gemas_core/`
- **Sync script:** `supernexus-v2/scripts/sync_gemas_core.py`

### Patrón client-specific

Cada cliente tiene `src/gemas_client_overrides/` preservado por sync:
- **LatamRust:** 8 gemas operativas Rust (rcon, combatlog, plugins, mapa, tebex, monitor, discord) + `rust_operatives_catalog.py`
- **SFDX:** sin client_overrides aún (sus `src/agents/*_gem.py` son código legacy de 22 gemas, no entran en el refactor de v1.0.0)

### Self-contained

- **LatamRust:** `src/gemas/__init__.py` importa las 4 dedicated desde `src.gemas_core.workers` (NO desde paths externos)
- **SFDX:** sus `src/agents/*_gem.py` permanecen como implementación SFDX-specific (no se borraron en v1.0.0 porque su código diverge del standard)
- Verificado con AST scan: 0 imports cross-project

### Refactor B (2026-06-05)

En LatamRust se eliminaron los duplicados:
- ~~`src/gemas/ayuda_gem.py`~~ → ahora `src.gemas_core.workers.AyudaGem`
- ~~`src/gemas/scholar_gem.py`~~ → ahora `src.gemas_core.workers.ScholarGem`
- ~~`src/gemas/sage_gem.py`~~ → ahora `src.gemas_core.workers.SageGem`
- ~~`src/gemas/biblioteca_gem.py`~~ → ahora `src.gemas_core.workers.BibliotecaGem`
- ~~`src/gemas/llm_role_gema.py`~~ → ahora `src.gemas_core.llm_role_gema.LLMRoleGema`

Backups en `data/backup_gemas_dupes/*.bak` por seguridad.

`src/gemas/__init__.py` ahora es 100% thin wrapper:
- Re-exporta las clases de `gemas_core`
- Importa las 8 gemas operativas Rust desde `gemas_client_overrides/`
- `build_all_gemas()` delega a `build_standard_gemas()` del standard

`src/gemas_client_overrides/rust_operatives_catalog.py` extrae el dict
`rust_gemas` que vivía en `ayuda_gem.py`, ahora se pasa via
`ayuda.full_catalog(client_gemas=list_rust_operatives())`.

### Tests

- SuperNEXUS: 67/67
- LatamRust: 122/122 (55 originales + 67 gemas_core)
- SFDX: pendiente migración a gemas_core (no en v1.0.0)
