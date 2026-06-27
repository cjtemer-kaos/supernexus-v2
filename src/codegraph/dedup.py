import logging
import math
import re
import unicodedata
from collections import defaultdict

from datasketch import MinHash, MinHashLSH
from rapidfuzz.distance import JaroWinkler

logger = logging.getLogger("codegraph.dedup")

_ENTROPY_THRESHOLD = 2.5
_LSH_THRESHOLD = 0.7
_MERGE_THRESHOLD = 92.0
_COMMUNITY_BOOST = 5.0
_NUM_PERM = 128
_CHUNK_SUFFIX = re.compile(r"_c\d+$")


def _norm(label: str) -> str:
    label = unicodedata.normalize("NFKC", label)
    return re.sub(r"[\W_]+", " ", label.casefold(), flags=re.UNICODE).strip()


def _entropy(label: str) -> float:
    s = _norm(label)
    if not s:
        return 0.0
    freq: dict[str, int] = defaultdict(int)
    for ch in s:
        freq[ch] += 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def _shingles(text: str, k: int = 3) -> set[str]:
    if len(text) < k:
        return {text}
    return {text[i: i + k] for i in range(len(text) - k + 1)}


def _make_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for shingle in _shingles(text.replace(" ", "")):
        m.update(shingle.encode("utf-8"))
    return m


_VARIANT_SUFFIX = re.compile(r"^(.*[a-z])([0-9]+[a-z]*|[a-z]{2,})$")


def _is_variant_pair(a: str, b: str) -> bool:
    if a == b:
        return False
    if max(len(a), len(b)) >= 12:
        return False
    ma, mb = _VARIANT_SUFFIX.match(a), _VARIANT_SUFFIX.match(b)
    if not (ma and mb):
        return False
    return ma.group(1) == mb.group(1) and ma.group(2) != mb.group(2)


def _short_label_blocked(a: str, b: str, jw_score: float) -> bool:
    if max(len(a), len(b)) >= 12:
        return False
    from rapidfuzz.distance import DamerauLevenshtein
    if jw_score >= 97.0 and len(a) == len(b) and DamerauLevenshtein.distance(a, b) <= 1:
        return False
    return True


class _UF:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        self._parent.setdefault(x, x)
        self._parent.setdefault(y, y)
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[ry] = rx

    def components(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for x in self._parent:
            groups[self.find(x)].append(x)
        return dict(groups)


def deduplicate_entities(
    nodes: list[dict],
    edges: list[dict],
    *,
    communities: dict[str, int],
) -> tuple[list[dict], list[dict]]:
    repos_seen = {n.get("repo") for n in nodes if n.get("repo")}
    if len(repos_seen) > 1:
        raise ValueError(
            f"deduplicate_entities: nodes span multiple repos {sorted(repos_seen)!r}. "
            f"Cross-project dedup is disabled — run dedup per-repo before merging."
        )

    if len(nodes) <= 1:
        return nodes, edges

    seen_ids: dict[str, dict] = {}
    for node in nodes:
        nid = node.get("id", "")
        if nid and nid not in seen_ids:
            seen_ids[nid] = node
    unique_nodes = list(seen_ids.values())

    if len(unique_nodes) <= 1:
        return unique_nodes, edges

    norm_to_nodes: dict[str, list[dict]] = defaultdict(list)
    for node in unique_nodes:
        key = _norm(node.get("label", node.get("id", "")))
        if key:
            norm_to_nodes[key].append(node)

    uf = _UF()
    exact_merges = 0
    for key, group in norm_to_nodes.items():
        if len(group) <= 1:
            continue
        by_file: dict[str, list[dict]] = defaultdict(list)
        for node in group:
            sf = node.get("source_file") or ""
            by_file[sf].append(node)
        for file_group in by_file.values():
            if len(file_group) > 1:
                winner = _pick_winner(file_group)
                for node in file_group:
                    uf.union(winner["id"], node["id"])
                exact_merges += len(file_group) - 1

    candidates: list[dict] = []
    seen_norms: set[str] = set()
    for node in unique_nodes:
        key = _norm(node.get("label", node.get("id", "")))
        if key and key not in seen_norms:
            seen_norms.add(key)
            if _entropy(node.get("label", "")) >= _ENTROPY_THRESHOLD:
                candidates.append(node)

    fuzzy_merges = 0
    if len(candidates) >= 2:
        lsh = MinHashLSH(threshold=_LSH_THRESHOLD, num_perm=_NUM_PERM)
        minhashes: dict[str, MinHash] = {}

        for node in candidates:
            norm_label = _norm(node.get("label", node.get("id", "")))
            m = _make_minhash(norm_label)
            minhashes[node["id"]] = m
            try:
                lsh.insert(node["id"], m)
            except ValueError:
                pass

        for node in candidates:
            node_id = node["id"]
            norm_label = _norm(node.get("label", node.get("id", "")))
            neighbors = lsh.query(minhashes[node_id])

            for neighbor_id in neighbors:
                if neighbor_id == node_id:
                    continue
                if uf.find(node_id) == uf.find(neighbor_id):
                    continue

                neighbor = next((n for n in candidates if n["id"] == neighbor_id), None)
                if neighbor is None:
                    continue

                neighbor_norm = _norm(neighbor.get("label", neighbor.get("id", "")))
                score = JaroWinkler.normalized_similarity(norm_label, neighbor_norm) * 100

                if _is_variant_pair(norm_label, neighbor_norm):
                    continue
                if _short_label_blocked(norm_label, neighbor_norm, score):
                    continue

                c1 = communities.get(node_id)
                c2 = communities.get(neighbor_id)
                if (c1 is not None and c2 is not None and c1 == c2
                        and min(len(norm_label), len(neighbor_norm)) >= 12):
                    score += _COMMUNITY_BOOST

                if score >= _MERGE_THRESHOLD:
                    if norm_label == neighbor_norm:
                        sf_a = node.get("source_file") or ""
                        sf_b = neighbor.get("source_file") or ""
                        if sf_a != sf_b:
                            continue
                    all_group = norm_to_nodes.get(norm_label, [node]) + \
                        norm_to_nodes.get(neighbor_norm, [neighbor])
                    winner = _pick_winner(all_group)
                    uf.union(winner["id"], node_id)
                    uf.union(winner["id"], neighbor_id)
                    fuzzy_merges += 1

    components = uf.components()
    remap: dict[str, str] = {}

    for root, members in components.items():
        if len(members) == 1:
            continue
        group_nodes = [n for n in unique_nodes if n["id"] in members]
        winner = _pick_winner(group_nodes) if group_nodes else {"id": root}
        winner_id = winner["id"]
        for member in members:
            if member != winner_id:
                remap[member] = winner_id

    if not remap:
        return unique_nodes, edges

    total = len(remap)
    msg = f"Deduplicated {total} node(s)"
    if exact_merges:
        msg += f" ({exact_merges} exact"
        if fuzzy_merges:
            msg += f", {fuzzy_merges} fuzzy"
        msg += ")"
    logger.info(msg)

    deduped_nodes = [n for n in unique_nodes if n["id"] not in remap]
    deduped_edges = []
    for edge in edges:
        e = dict(edge)
        src = e["source"] if "source" in e else e.get("from")
        tgt = e["target"] if "target" in e else e.get("to")
        if src is None or tgt is None:
            continue
        e["source"] = remap.get(src, src)
        e["target"] = remap.get(tgt, tgt)
        e.pop("from", None)
        e.pop("to", None)
        if e["source"] != e["target"]:
            deduped_edges.append(e)

    return deduped_nodes, deduped_edges


def _pick_winner(nodes: list[dict]) -> dict:
    if not nodes:
        raise ValueError("Cannot pick winner from empty list")

    def _score(n: dict) -> tuple[int, int]:
        has_suffix = bool(_CHUNK_SUFFIX.search(n["id"]))
        return (1 if has_suffix else 0, len(n["id"]))

    return min(nodes, key=_score)
