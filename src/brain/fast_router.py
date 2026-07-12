"""FastRouter — clasificador ultra-ligero para routing de tasks a gemas.

Reemplaza el LLM fallback (Phase 4) con un clasificador TF-IDF-like que:
- Corre en <1ms (vs 1-3s del LLM)
- No requiere dependencias externas (solo math + re)
- Se entrena desde las keyword patterns existentes
- Retorna confianza para decidir si delegar al LLM

Arquitectura:
1. Pre-computa pesos TF-IDF-like de keywords por gema
2. Scorea tasks con bag-of-words + n-gram matching
3. Retorna top-3 gemas con confidence
4. Fallback a LLM solo si confidence < threshold
"""

import asyncio
import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GemaProfile:
    """Perfil de una gema para el clasificador."""
    name: str
    keywords: Set[str] = field(default_factory=set)
    multi_word_patterns: Set[str] = field(default_factory=set)
    weight: float = 1.0


@dataclass
class FastRouteResult:
    """Resultado del clasificador rápido."""
    gem: str
    confidence: float
    all_scores: Dict[str, float]
    top_n: List[Tuple[str, float]]
    source: str  # "fast_router" | "llm_fallback" | "keyword_deterministic"


class FastRouter:
    """Clasificador TF-IDF-like para routing de tasks.

    Entrena desde diccionarios de keywords (multi-word y single)
    y puede refinar con ejemplos reales vía update().

    Uso:
        router = FastRouter()
        router.train_from_patterns(multi_word, single_keyword)
        result = router.classify("refactoriza el modulo de pagos")
        # -> FastRouteResult(gem="code", confidence=0.87, ...)
    """

    def __init__(self):
        self._gemas: Dict[str, GemaProfile] = {}
        self._total_keywords = 0
        self._keyword_doc_count: Dict[str, int] = Counter()
        self._gema_keyword_freq: Dict[str, Counter] = defaultdict(Counter)
        self._idf_cache: Dict[str, float] = {}
        self._n_gram_index: Dict[str, Set[str]] = defaultdict(set)
        self._confidence_threshold = 0.25

    # ── Training ───────────────────────────────────────────────────────

    def train_from_patterns(
        self,
        multi_word: Dict[str, str],
        single_keyword: Dict[str, str],
    ) -> "FastRouter":
        """Entrena desde los diccionarios de patrones existentes.

        Cada pattern/keyword es un 'documento' que pertenece a una gema.
        Construye pesos TF-IDF-like: keywords raras = mayor peso.
        """
        # Agrupar keywords por gema
        gema_keywords: Dict[str, Set[str]] = defaultdict(set)
        gema_multi: Dict[str, Set[str]] = defaultdict(set)

        for pattern, gem in multi_word.items():
            gema_keywords[gem].add(pattern)
            gema_multi[gem].add(pattern)

        for keyword, gem in single_keyword.items():
            gema_keywords[gem].add(keyword)

        # Construir perfiles
        for gem, keywords in gema_keywords.items():
            profile = GemaProfile(
                name=gem,
                keywords=keywords,
                multi_word_patterns=gema_multi.get(gem, set()),
            )
            self._gemas[gem] = profile

        # Contar doc frequency (cuantas gemas usan cada keyword)
        all_keywords = set()
        for gem, keywords in gema_keywords.items():
            all_keywords.update(keywords)
        self._total_keywords = len(all_keywords)

        for gem, keywords in gema_keywords.items():
            for kw in keywords:
                self._keyword_doc_count[kw] += 1
                self._gema_keyword_freq[gem][kw] += 1
                # N-gram index: bigramas de la keyword
                for i in range(len(kw) - 2):
                    bigram = kw[i:i+3]
                    self._n_gram_index[bigram].add(kw)

        # Pre-computar IDF
        n_gemas = len(self._gemas)
        for kw, df in self._keyword_doc_count.items():
            self._idf_cache[kw] = math.log((n_gemas + 1) / (df + 1)) + 1.0

        return self

    def update(self, gem: str, keywords: List[str]):
        """Actualiza incrementalmiente con nuevos ejemplos."""
        if gem not in self._gemas:
            self._gemas[gem] = GemaProfile(name=gem)

        for kw in keywords:
            self._gemas[gem].keywords.add(kw)
            self._keyword_doc_count[kw] += 1
            self._gema_keyword_freq[gem][kw] += 1

        # Recalcular IDF
        n_gemas = len(self._gemas)
        for kw in set(keywords):
            df = self._keyword_doc_count[kw]
            self._idf_cache[kw] = math.log((n_gemas + 1) / (df + 1)) + 1.0
        self._total_keywords = len(self._keyword_doc_count)

    # ── Classification ─────────────────────────────────────────────────

    def classify(self, task: str, top_k: int = 3) -> FastRouteResult:
        """Clasifica una task en una gema.

        Returns:
            FastRouteResult con la gema seleccionada, confianza, y scores.
        """
        task_lower = task.lower()
        words = set(self._tokenize(task_lower))
        n_words = len(words)

        if n_words == 0:
            return FastRouteResult(
                gem="director",
                confidence=0.0,
                all_scores={},
                top_n=[],
                source="fast_router",
            )

        scores: Dict[str, float] = defaultdict(float)
        matched_keywords: Dict[str, Set[str]] = defaultdict(set)

        # Score por keyword match (TF-IDF weighted)
        for gem, profile in self._gemas.items():
            gem_score = 0.0
            matched = set()

            for kw in profile.keywords:
                if kw in task_lower:
                    tf = self._gema_keyword_freq[gem].get(kw, 0)
                    idf = self._idf_cache.get(kw, 1.0)
                    gem_score += (1.0 + math.log(1 + tf)) * idf
                    matched.add(kw)

            scores[gem] = gem_score
            matched_keywords[gem] = matched

        # Score por n-gram match (captura variaciones)
        task_bigrams = set()
        for i in range(len(task_lower) - 2):
            bg = task_lower[i:i+3]
            if bg.isalpha():
                task_bigrams.add(bg)

        for gem, profile in self._gemas.items():
            if scores[gem] == 0:
                for kw in profile.keywords:
                    kw_bigrams = set()
                    for i in range(len(kw) - 2):
                        bg = kw[i:i+3]
                        if bg.isalpha():
                            kw_bigrams.add(bg)
                    overlap = task_bigrams & kw_bigrams
                    if len(overlap) >= min(3, len(kw) - 1):
                        scores[gem] += 0.1 * len(overlap)

        # Normalizar scores (solo gemas con score > 0)
        max_score = max(scores.values()) if scores else 0.0
        if max_score > 0:
            non_zero = {g: s for g, s in scores.items() if s > 0}
            if non_zero:
                exp_scores = {g: math.exp(s / max_score) for g, s in non_zero.items()}
                total_exp = sum(exp_scores.values()) or 1.0
                normalized = {g: s / total_exp for g, s in exp_scores.items()}
            else:
                normalized = dict.fromkeys(scores.keys(), 0.0)
        else:
            normalized = dict.fromkeys(scores.keys(), 0.0)

        # Top N
        sorted_scores = sorted(normalized.items(), key=lambda x: -x[1])
        top_n = sorted_scores[:top_k]

        best_gem = "director"
        best_conf = 0.0
        if max_score > 0 and top_n:
            best_gem = top_n[0][0]
            best_conf = top_n[0][1]

        return FastRouteResult(
            gem=best_gem,
            confidence=best_conf,
            all_scores=dict(normalized),
            top_n=top_n,
            source="fast_router",
        )

    def _n_gram_index_bigrams(self, word: str) -> Set[str]:
        """Extrae bigramas de una palabra."""
        result = set()
        for i in range(len(word) - 2):
            bg = word[i:i+3]
            if bg.isalpha():
                result.add(bg)
        return result

    async def classify_with_fallback(
        self,
        task: str,
        multi_word_patterns: Dict[str, str],
        single_keyword_patterns: Dict[str, str],
        llm_classify_fn=None,
    ) -> FastRouteResult:
        """Clasifica con 3 niveles de fallback.

        Nivel 1: Keyword deterministico (multi-word + single, exact match)
        Nivel 2: FastRouter TF-IDF (si confianza > threshold)
        Nivel 3: LLM fallback (si confianza < threshold y hay función)
        """
        task_lower = task.lower()

        # Nivel 1: Keyword deterministico (Phase 1 + 3 original)
        deterministic_gems: Set[str] = set()
        for pattern, gem in multi_word_patterns.items():
            if pattern in task_lower:
                deterministic_gems.add(gem)
        for keyword, gem in single_keyword_patterns.items():
            if keyword in task_lower:
                deterministic_gems.add(gem)

        if deterministic_gems:
            gems = list(deterministic_gems)
            return FastRouteResult(
                gem=gems[0],
                confidence=0.95,
                all_scores={g: 0.95 for g in gems},
                top_n=[(g, 0.95) for g in gems[:3]],
                source="keyword_deterministic",
            )

        # Nivel 2: FastRouter TF-IDF
        result = self.classify(task)
        if result.confidence >= self._confidence_threshold:
            return result

        # Nivel 3: LLM fallback (opcional)
        if llm_classify_fn and result.confidence < self._confidence_threshold:
            llm_result = await llm_classify_fn(task) if asyncio.iscoroutinefunction(llm_classify_fn) else llm_classify_fn(task)
            if llm_result:
                return FastRouteResult(
                    gem=llm_result,
                    confidence=0.6,
                    all_scores={**result.all_scores, llm_result: 0.6},
                    top_n=[(llm_result, 0.6), *result.top_n],
                    source="llm_fallback",
                )

        return result

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokeniza texto: lowercase, split por espacios/puntuacion."""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [t for t in text.split() if len(t) > 1]


# ── Singleton factory ──────────────────────────────────────────────────

_fast_router: Optional[FastRouter] = None


def get_fast_router(force_rebuild: bool = False) -> FastRouter:
    """Singleton del FastRouter, entrenado con los patrones por defecto."""
    global _fast_router
    if _fast_router is None or force_rebuild:
        from src.brain.routing import MULTI_WORD_PATTERNS, SINGLE_KEYWORD_PATTERNS
        _fast_router = FastRouter()
        _fast_router.train_from_patterns(MULTI_WORD_PATTERNS, SINGLE_KEYWORD_PATTERNS)
        logger.info(
            f"FastRouter trained: {len(_fast_router._gemas)} gemas, "
            f"{_fast_router._total_keywords} keywords"
        )
    return _fast_router
