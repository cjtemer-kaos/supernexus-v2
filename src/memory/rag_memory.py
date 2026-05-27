"""
RAG Semantic Memory - Capa 2 de memoria para SuperNEXUS v2.0

Busqueda hibrida: BM25 + Embeddings locales (sentence-transformers opcional).
Basado en patrones de RAG_Techniques de NirDiamant.
"""

import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SimpleTokenizer:
    """Tokenizador simple con stemming basico"""

    STOPWORDS = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
        "al", "en", "con", "sin", "por", "para", "que", "se", "es", "son",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "and",
        "but", "or", "nor", "not", "so", "yet", "both", "either", "neither",
        "each", "every", "all", "any", "few", "more", "most", "other", "some",
        "such", "no", "only", "own", "same", "than", "too", "very", "just",
        "because", "if", "when", "where", "how", "what", "which", "who", "whom",
        "this", "that", "these", "those", "i", "me", "my", "myself", "we", "our",
        "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
        "he", "him", "his", "himself", "she", "her", "hers", "herself", "it",
        "its", "itself", "they", "them", "their", "theirs", "themselves",
    }

    def tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()
        return [t for t in tokens if t not in self.STOPWORDS and len(t) > 2]


class BM25Index:
    """
    Indice BM25 (mejora de TF-IDF con normalizacion de longitud).
    Basado en el algoritmo Okapi BM25 usado en motores de busqueda profesionales.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        k1: Controla saturacion de frecuencia de terminos (1.2-2.0 tipico)
        b: Controla normalizacion por longitud (0.0-1.0, 0.75 tipico)
        """
        self.tokenizer = SimpleTokenizer()
        self.documents: Dict[str, str] = {}
        self.doc_tokens: Dict[str, List[str]] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.idf: Dict[str, float] = {}
        self.k1 = k1
        self.b = b
        self._built = False

    def add_document(self, doc_id: str, text: str):
        self.documents[doc_id] = text
        self.doc_tokens[doc_id] = self.tokenizer.tokenize(text)
        self.doc_lengths[doc_id] = len(self.doc_tokens[doc_id])
        self._built = False

    def remove_document(self, doc_id: str):
        self.documents.pop(doc_id, None)
        self.doc_tokens.pop(doc_id, None)
        self.doc_lengths.pop(doc_id, None)
        self._built = False

    def build(self):
        if self._built:
            return

        n_docs = len(self.documents)
        if n_docs == 0:
            return

        # Calcular longitud promedio
        self.avg_doc_length = sum(self.doc_lengths.values()) / n_docs if n_docs > 0 else 1

        # Calcular document frequency
        df = Counter()
        for tokens in self.doc_tokens.values():
            for token in set(tokens):
                df[token] += 1

        # Calcular IDF con smoothing BM25
        self.idf = {}
        for term, freq in df.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[term] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1)

        self._built = True

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self._built:
            self.build()

        if not self.documents:
            return []

        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        scores = {}
        for doc_id, doc_tokens in self.doc_tokens.items():
            score = 0.0
            doc_len = self.doc_lengths[doc_id]
            
            for token in query_tokens:
                if token in self.idf and token in doc_tokens:
                    tf = doc_tokens.count(token)
                    # BM25 scoring function
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))
                    score += self.idf[token] * (numerator / denominator)
            
            if score > 0:
                scores[doc_id] = score

        # Normalizar y ordenar
        if not scores:
            return []
        
        max_score = max(scores.values())
        results = [
            {
                "id": doc_id,
                "bm25_score": score / max_score,
                "preview": self.documents[doc_id][:200],
            }
            for doc_id, score in scores.items()
        ]
        results.sort(key=lambda x: x["bm25_score"], reverse=True)
        return results[:top_k]


class LocalEmbedder:
    """
    Embedder local opcional usando sentence-transformers.
    Si no esta disponible, usa TF-IDF como fallback.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._available = False
        self._try_load()

    def _try_load(self):
        try:
            import os
            os.environ.setdefault("HF_HUB_OFFLINE", "1")  # Use cached model, don't hit network
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self._available = True
            logger.info(f"LocalEmbedder loaded: {self.model_name}")
        except ImportError:
            logger.info("sentence-transformers no disponible. Usando TF-IDF fallback.")
            self._available = False
        except Exception as e:
            logger.warning(f"LocalEmbedder failed to load (using TF-IDF fallback): {e}")
            self._available = False

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not self._available or not self.model:
            return self._tfidf_fallback(texts)
        
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def _tfidf_fallback(self, texts: List[str]) -> List[List[float]]:
        """Fallback simple usando frecuencia de terminos"""
        tokenizer = SimpleTokenizer()
        all_tokens = set()
        tokenized = [tokenizer.tokenize(t) for t in texts]
        for tokens in tokenized:
            all_tokens.update(tokens)
        
        token_list = sorted(list(all_tokens))
        token_to_idx = {t: i for i, t in enumerate(token_list)}
        
        embeddings = []
        for tokens in tokenized:
            vec = [0.0] * len(token_list)
            for t in tokens:
                if t in token_to_idx:
                    vec[token_to_idx[t]] += 1
            # Normalizar
            norm = math.sqrt(sum(v*v for v in vec)) or 1
            vec = [v/norm for v in vec]
            embeddings.append(vec)
        
        return embeddings

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot = sum(a*b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a*a for a in vec1)) or 1
        norm2 = math.sqrt(sum(b*b for b in vec2)) or 1
        return dot / (norm1 * norm2)

    @property
    def available(self) -> bool:
        return self._available


class HybridSearchIndex:
    """
    Busqueda hibrida: Combina BM25 (precision lexical) + Embeddings (semantica).
    Basado en patrones de RAG_Techniques de NirDiamant.
    
    Estrategia de fusion: Reciprocal Rank Fusion (RRF)
    - Combina rankings de ambos metodos
    - No requiere normalizacion de scores
    - Robusto y usado en sistemas de produccion
    """

    def __init__(self, bm25_weight: float = 0.6, embed_weight: float = 0.4, k: int = 60):
        """
        bm25_weight: Peso para BM25 (0.0-1.0)
        embed_weight: Peso para embeddings (0.0-1.0)
        k: Parametro RRF (tipico 60)
        """
        self.bm25 = BM25Index()
        self.embedder = LocalEmbedder()
        self.bm25_weight = bm25_weight
        self.embed_weight = embed_weight
        self.k = k
        self.documents: Dict[str, str] = {}
        self.embeddings: Dict[str, List[float]] = {}
        self._built = False

    def add_document(self, doc_id: str, text: str):
        self.documents[doc_id] = text
        self.bm25.add_document(doc_id, text)
        self._built = False

    def remove_document(self, doc_id: str):
        self.documents.pop(doc_id, None)
        self.embeddings.pop(doc_id, None)
        self.bm25.remove_document(doc_id)
        self._built = False

    def build(self):
        self.bm25.build()
        
        # Construir embeddings si estan disponibles
        if self.embedder.available and self.documents:
            texts = [self.documents[did] for did in self.documents]
            doc_ids = list(self.documents.keys())
            embeddings = self.embedder.encode(texts)
            for did, emb in zip(doc_ids, embeddings):
                self.embeddings[did] = emb
        
        self._built = True

    def _reciprocal_rank_fusion(self, bm25_results: List[Dict], embed_results: List[Dict], top_k: int) -> List[Dict]:
        """
        Combina rankings usando Reciprocal Rank Fusion (RRF).
        RRF(d) = sum(1 / (k + rank(d))) para cada metodo
        """
        rrf_scores = {}
        
        # Scores de BM25
        for rank, result in enumerate(bm25_results):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + (self.bm25_weight / (self.k + rank + 1))
        
        # Scores de Embeddings
        for rank, result in enumerate(embed_results):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + (self.embed_weight / (self.k + rank + 1))
        
        # Ordenar por RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs[:top_k]:
            results.append({
                "id": doc_id,
                "hybrid_score": score,
                "preview": self.documents[doc_id][:200],
            })
        
        return results

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self._built:
            self.build()

        if not self.documents:
            return []

        # Buscar con BM25
        bm25_results = self.bm25.search(query, top_k * 2)
        
        # Buscar con Embeddings si estan disponibles
        embed_results = []
        if self.embedder.available and self.embeddings:
            query_emb = self.embedder.encode([query])[0]
            scores = []
            for doc_id, doc_emb in self.embeddings.items():
                sim = self.embedder.cosine_similarity(query_emb, doc_emb)
                scores.append({"id": doc_id, "similarity": sim})
            scores.sort(key=lambda x: x["similarity"], reverse=True)
            embed_results = scores[:top_k * 2]
        
        # Si no hay embeddings, usar solo BM25
        if not embed_results:
            return bm25_results[:top_k]
        
        # Combinar con RRF
        return self._reciprocal_rank_fusion(bm25_results, embed_results, top_k)


class RAGMemory:
    """
    Capa 2 de memoria: RAG hibrido (BM25 + Embeddings locales).
    
    Mejoras implementadas (basadas en RAG_Techniques de NirDiamant):
    - Busqueda hibrida: BM25 para precision lexical + Embeddings para semantica
    - Reciprocal Rank Fusion para combinar resultados
    - sentence-transformers opcional (fallback a TF-IDF si no disponible)
    - Normalizacion de longitud en BM25 (Okapi BM25)
    """

    def __init__(self, data_dir: Optional[str] = None, use_embeddings: bool = True):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent.parent / "data" / "memory")

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.use_embeddings = use_embeddings
        self.index = HybridSearchIndex() if use_embeddings else BM25Index()
        self.metadata_file = self.data_dir / "rag_metadata.json"
        self.metadata: Dict = {}
        self._load_metadata()
        self._build_index_from_data()

    def _load_metadata(self):
        if self.metadata_file.exists():
            try:
                self.metadata = json.loads(
                    self.metadata_file.read_text(encoding="utf-8")
                )
            except:
                self.metadata = {"entries": {}}
        else:
            self.metadata = {"entries": {}}

    def _save_metadata(self):
        self.metadata_file.write_text(
            json.dumps(self.metadata, indent=2), encoding="utf-8"
        )

    def _build_index_from_data(self):
        for entry_id, entry in self.metadata.get("entries", {}).items():
            self.index.add_document(entry_id, entry.get("text", ""))
        self.index.build()

    def add(self, entry_id: str, text: str, source: str = "", tags: List[str] = None) -> Dict:
        self.index.add_document(entry_id, text)
        self.index.build()

        self.metadata["entries"][entry_id] = {
            "text": text[:5000],
            "source": source,
            "tags": tags or [],
            "added_at": datetime.now().isoformat(),
            "access_count": 0,
        }
        self._save_metadata()

        return {"success": True, "id": entry_id}

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self.index.search(query, top_k)

        for r in results:
            entry = self.metadata["entries"].get(r["id"])
            if entry:
                entry["access_count"] = entry.get("access_count", 0) + 1
        self._save_metadata()

        return results

    def delete(self, entry_id: str) -> Dict:
        self.index.remove_document(entry_id)
        self.metadata["entries"].pop(entry_id, None)
        self._save_metadata()
        return {"success": True}

    def get_stats(self) -> Dict:
        entries = self.metadata.get("entries", {})
        total_access = sum(e.get("access_count", 0) for e in entries.values())
        has_embeddings = hasattr(self.index, 'embedder') and self.index.embedder.available

        return {
            "total_entries": len(entries),
            "total_accesses": total_access,
            "index_built": self.index._built,
            "hybrid_search": self.use_embeddings,
            "embeddings_available": has_embeddings,
        }
