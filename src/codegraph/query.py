import logging
import math
from collections import Counter

import networkx as nx

logger = logging.getLogger("codegraph.query")

_EDGE_TYPE_RANK = {
    "calls": 0, "imports": 1, "imports_from": 2, "inherits": 3,
    "implements": 4, "references": 5, "defines": 6, "contains": 7,
    "similar": 8, "semantic_related": 9,
}

_HUB_THRESHOLD_MULTIPLIER = 2.0


def _compute_idf(G: nx.Graph) -> dict[str, float]:
    N = G.number_of_nodes()
    if N == 0:
        return {}
    term_doc_count: Counter[str] = Counter()
    for _, data in G.nodes(data=True):
        label = (data.get("label") or "").lower()
        for token in label.split():
            term_doc_count[token] += 1
    return {term: math.log((N + 1) / (count + 1)) + 1 for term, count in term_doc_count.items()}


def _score_nodes(
    G: nx.Graph, terms: list[str], idf: dict[str, float],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for node_id, data in G.nodes(data=True):
        label = (data.get("label") or "").lower()
        label_text = data.get("label") or node_id
        score = 0.0
        for term in terms:
            if term in label:
                idf_val = idf.get(term, 1.0)
                if label.startswith(term):
                    score += idf_val * 3.0
                elif f" {term}" in label or label.startswith(f"{term}_"):
                    score += idf_val * 2.0
                elif term in label.split():
                    score += idf_val * 1.5
                elif term in label_text.lower():
                    score += idf_val * 0.5
        if score > 0:
            scores[node_id] = score
    return scores


def _pick_seeds(scored: dict[str, float], top_k: int = 10) -> list[str]:
    if not scored:
        return []
    sorted_items = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    if not sorted_items:
        return []
    max_score = sorted_items[0][1]
    cutoff = max_score * 0.3
    candidates = [n for n, s in sorted_items if s >= cutoff]
    return candidates[:top_k]


def _infer_context_filters(query: str) -> dict:
    filters = {}
    q = query.lower()
    if any(w in q for w in ("call", "invoke", "function", "method")):
        filters["relation"] = "calls"
    if any(w in q for w in ("import", "dependency", "depend")):
        filters["relation"] = "imports"
    if "field" in q or "property" in q:
        filters["relation"] = "references"
    if "class" in q or "type" in q:
        filters["node_types"] = {"class"}
    return filters


def _hub_threshold(G: nx.Graph) -> int:
    degrees = sorted(d for _, d in G.degree())
    if not degrees:
        return 999
    p99_idx = max(0, int(len(degrees) * 0.99) - 1)
    return degrees[p99_idx] if p99_idx < len(degrees) else degrees[-1]


def _edge_confidence_sort_key(data: dict) -> tuple:
    order = {"EXTRACTED": 0, "INFERRED": 1, "AMBIGUOUS": 2}
    return (order.get(data.get("confidence", "EXTRACTED"), 0), -data.get("weight", 1.0))


class GraphQuery:
    def __init__(self, G: nx.Graph, idf: dict[str, float] | None = None):
        self.G = G
        self.idf = idf if idf is not None else _compute_idf(G)

    def query(self, query_text: str, top_k: int = 10) -> list[dict]:
        terms = [t.lower() for t in query_text.split() if len(t) > 1]
        if not terms:
            return []
        scores = _score_nodes(self.G, terms, self.idf)
        seed_ids = _pick_seeds(scores, top_k=top_k)
        results = []
        for nid in seed_ids:
            data = self.G.nodes[nid]
            results.append({
                "id": nid,
                "label": data.get("label", nid),
                "source_file": data.get("source_file", ""),
                "node_type": data.get("file_type", "concept"),
                "score": round(scores.get(nid, 0), 4),
            })
        return results

    def neighbors(
        self, node_id: str, relation: str | None = None,
        max_depth: int = 1, max_nodes: int = 50,
    ) -> list[dict]:
        if node_id not in self.G:
            return []
        hub_limit = _hub_threshold(self.G)
        visited: set[str] = set()
        results: list[dict] = []

        def _walk(current: str, depth: int):
            if depth > max_depth or len(visited) >= max_nodes:
                return
            for nb in self.G.neighbors(current):
                if nb in visited:
                    continue
                edge_data = self.G.get_edge_data(current, nb)
                if isinstance(edge_data, dict):
                    edge = next(iter(edge_data.values())) if edge_data else {}
                else:
                    edge = edge_data or {}
                if relation and edge.get("relation") != relation:
                    continue
                if self.G.degree(nb) > hub_limit and depth > 0:
                    continue
                visited.add(nb)
                nd = self.G.nodes[nb]
                results.append({
                    "id": nb,
                    "label": nd.get("label", nb),
                    "source_file": nd.get("source_file", ""),
                    "relation": edge.get("relation", ""),
                    "confidence": edge.get("confidence", "EXTRACTED"),
                    "depth": depth,
                })
                _walk(nb, depth + 1)

        _walk(node_id, 1)
        return results[:max_nodes]

    def shortest_path(
        self, source: str, target: str, weight: str | None = "confidence_score",
    ) -> list[dict]:
        if source not in self.G or target not in self.G:
            return []
        try:
            path = nx.shortest_path(self.G, source=source, target=target, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        result = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = self.G.get_edge_data(u, v)
            if isinstance(edge, dict):
                attrs = next(iter(edge.values())) if edge else {}
            else:
                attrs = edge or {}
            result.append({
                "source": u,
                "source_label": self.G.nodes[u].get("label", u),
                "target": v,
                "target_label": self.G.nodes[v].get("label", v),
                "relation": attrs.get("relation", ""),
                "confidence": attrs.get("confidence", "EXTRACTED"),
            })
        return result

    def community_query(
        self, community_id: int, community_labels: dict[int, str] | None = None,
    ) -> list[dict]:
        comm_label = (community_labels or {}).get(community_id, f"Community {community_id}")
        members = [
            n for n, d in self.G.nodes(data=True)
            if d.get("community") == community_id
        ]
        return [{
            "community_id": community_id,
            "label": comm_label,
            "node_count": len(members),
            "nodes": sorted(
                [{"id": n, "label": self.G.nodes[n].get("label", n)}
                 for n in members],
                key=lambda x: x["label"],
            ),
        }]

    def bfs(self, node_id: str, max_depth: int = 2, max_nodes: int = 100) -> list[dict]:
        if node_id not in self.G:
            return []
        hub_limit = _hub_threshold(self.G)
        visited: set[str] = {node_id}
        queue: list[tuple[str, int]] = [(node_id, 0)]
        results: list[dict] = []
        while queue and len(results) < max_nodes:
            current, depth = queue.pop(0)
            if depth > 0:
                nd = self.G.nodes[current]
                results.append({
                    "id": current,
                    "label": nd.get("label", current),
                    "depth": depth,
                })
            if depth >= max_depth:
                continue
            for nb in self.G.neighbors(current):
                if nb in visited:
                    continue
                if self.G.degree(nb) > hub_limit and depth > 0:
                    continue
                visited.add(nb)
                queue.append((nb, depth + 1))
        return results

    def god_nodes(self, top_n: int = 10) -> list[dict]:
        from .analyze import god_nodes as _god_nodes
        return _god_nodes(self.G, top_n=top_n)

    def surprising_connections(
        self, communities: dict[int, list[str]] | None = None, top_n: int = 5,
    ) -> list[dict]:
        from .analyze import surprising_connections as _surprising
        return _surprising(self.G, communities, top_n)

    def suggest_questions(
        self, communities: dict[int, list[str]],
        community_labels: dict[int, str], top_n: int = 7,
    ) -> list[dict]:
        from .analyze import suggest_questions as _suggest
        return _suggest(self.G, communities, community_labels, top_n)
