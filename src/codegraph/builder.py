import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional

import networkx as nx

from .types import LANG_FAMILY

logger = logging.getLogger("codegraph")

_FILE_TYPE_SYNONYMS = {
    "markdown": "document", "text": "document",
    "tool": "code", "library": "code",
    "pattern": "concept", "principle": "concept",
    "constraint": "concept", "tech": "concept",
    "technology": "concept", "data-source": "concept",
    "data_source": "concept", "gotcha": "concept",
    "framework": "concept",
}


def normalize_id(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    cleaned = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_").casefold()


def _norm_source_file(p: Optional[str], root: Optional[str] = None) -> Optional[str]:
    if not p:
        return p
    p = p.replace("\\", "/")
    if root and os.path.isabs(p):
        try:
            p = Path(p).relative_to(root).as_posix()
        except ValueError:
            pass
    return p


def edge_data(G: nx.Graph, u: str, v: str) -> dict:
    raw = G[u][v]
    if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)):
        return next(iter(raw.values()), {})
    return raw


def edge_datas(G: nx.Graph, u: str, v: str) -> list[dict]:
    raw = G[u][v]
    if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)):
        return list(raw.values())
    return [raw]


def build_from_json(
    extraction: dict,
    *,
    directed: bool = False,
    root: Optional[str | Path] = None,
) -> nx.Graph:
    _root = str(Path(root).resolve()) if root else None

    if "edges" not in extraction and "links" in extraction:
        extraction = dict(extraction, edges=extraction["links"])

    for node in extraction.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("file_type") in (None, ""):
            node["file_type"] = "concept"
        ft = node.get("file_type", "")
        if ft and ft not in {"code", "document", "paper", "image", "rationale", "concept"}:
            node["file_type"] = _FILE_TYPE_SYNONYMS.get(ft, "concept")

    G: nx.Graph = nx.DiGraph() if directed else nx.Graph()
    for node in extraction.get("nodes", []):
        if "source_file" in node:
            node["source_file"] = _norm_source_file(node["source_file"], _root)
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})

    node_set = set(G.nodes())
    norm_to_id: dict[str, str] = {normalize_id(nid): nid for nid in node_set}

    for edge in sorted(
        extraction.get("edges", []),
        key=lambda e: (
            str(e.get("source", e.get("from", ""))),
            str(e.get("target", e.get("to", ""))),
            str(e.get("relation", "")),
        ),
    ):
        if "source" not in edge and "from" in edge:
            edge["source"] = edge["from"]
        if "target" not in edge and "to" in edge:
            edge["target"] = edge["to"]
        if "source" not in edge or "target" not in edge:
            continue
        src, tgt = edge["source"], edge["target"]
        if src not in node_set:
            src = norm_to_id.get(normalize_id(src), src)
        if tgt not in node_set:
            tgt = norm_to_id.get(normalize_id(tgt), tgt)
        if src not in node_set or tgt not in node_set:
            continue

        attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
        if "source_file" in attrs:
            attrs["source_file"] = _norm_source_file(attrs["source_file"], _root)

        if attrs.get("relation") == "calls" and attrs.get("confidence") == "INFERRED":
            src_ext = Path(G.nodes[src].get("source_file") or "").suffix.lower()
            tgt_ext = Path(G.nodes[tgt].get("source_file") or "").suffix.lower()
            if src_ext and tgt_ext and LANG_FAMILY.get(src_ext) != LANG_FAMILY.get(tgt_ext):
                continue

        attrs["_src"] = src
        attrs["_tgt"] = tgt

        if not G.is_directed() and G.has_edge(src, tgt):
            existing = edge_data(G, src, tgt)
            if existing.get("relation") == attrs.get("relation") and (
                existing.get("_src") == tgt and existing.get("_tgt") == src
            ):
                continue

        G.add_edge(src, tgt, **attrs)

    hyperedges = extraction.get("hyperedges", [])
    if hyperedges:
        G.graph["hyperedges"] = hyperedges
    return G


def build(
    extractions: list[dict],
    *,
    directed: bool = False,
    dedup: bool = True,
    root: Optional[str | Path] = None,
) -> nx.Graph:
    from .dedup import deduplicate_entities
    combined: dict = {"nodes": [], "edges": [], "hyperedges": [], "input_tokens": 0, "output_tokens": 0}
    for ext in extractions:
        combined["nodes"].extend(ext.get("nodes", []))
        combined["edges"].extend(ext.get("edges", []))
        combined["hyperedges"].extend(ext.get("hyperedges", []))
        combined["input_tokens"] += ext.get("input_tokens", 0)
        combined["output_tokens"] += ext.get("output_tokens", 0)
    if dedup and combined["nodes"]:
        combined["nodes"], combined["edges"] = deduplicate_entities(
            combined["nodes"], combined["edges"], communities={},
        )
    return build_from_json(combined, directed=directed, root=root)


def _norm_label(label: str) -> str:
    label = unicodedata.normalize("NFKC", label)
    return re.sub(r"[\W_ ]+", " ", label.casefold(), flags=re.UNICODE).strip()


_CHUNK_SUFFIX = re.compile(r"_c\d+$")


def deduplicate_by_label(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], list[dict]]:
    canonical: dict[str, dict] = {}
    remap: dict[str, str] = {}

    for node in nodes:
        key = _norm_label(node.get("label", node.get("id", "")))
        if not key:
            continue
        existing = canonical.get(key)
        if existing is None:
            canonical[key] = node
        else:
            has_suffix = bool(_CHUNK_SUFFIX.search(node["id"]))
            existing_has_suffix = bool(_CHUNK_SUFFIX.search(existing["id"]))
            if has_suffix and not existing_has_suffix:
                remap[node["id"]] = existing["id"]
            elif existing_has_suffix and not has_suffix:
                remap[existing["id"]] = node["id"]
                canonical[key] = node
            elif len(node["id"]) < len(existing["id"]):
                remap[existing["id"]] = node["id"]
                canonical[key] = node
            else:
                remap[node["id"]] = existing["id"]

    if not remap:
        return nodes, edges

    logger.info(f"Deduplicated {len(remap)} duplicate node(s) by label.")
    deduped_nodes = list(canonical.values())
    deduped_edges = []
    for edge in edges:
        e = dict(edge)
        e["source"] = remap.get(e["source"], e["source"])
        e["target"] = remap.get(e["target"], e["target"])
        if e["source"] != e["target"]:
            deduped_edges.append(e)
    return deduped_nodes, deduped_edges


def build_merge(
    new_chunks: list[dict],
    graph_path: str | Path = ".codegraph/graph.json",
    prune_sources: Optional[list[str]] = None,
    *,
    directed: bool = False,
    dedup: bool = True,
    root: Optional[str | Path] = None,
) -> nx.Graph:
    graph_path = Path(graph_path)
    if graph_path.exists():
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        links_key = "links" if "links" in data else "edges"
        existing_nodes = list(data.get("nodes", []))
        existing_edges = list(data.get(links_key, []))
        base = [{"nodes": existing_nodes, "edges": existing_edges}]
    else:
        existing_nodes = []
        base = []

    all_chunks = base + list(new_chunks)
    G = build(all_chunks, directed=directed, dedup=dedup, root=root)

    if prune_sources:
        _root_str = str(Path(root).resolve()) if root is not None else None
        prune_set: set[str] = set()
        for p in prune_sources:
            if not p:
                continue
            prune_set.add(p)
            norm = _norm_source_file(p, _root_str)
            if norm:
                prune_set.add(norm)
        to_remove = [
            n for n, d in G.nodes(data=True)
            if d.get("source_file") in prune_set
        ]
        G.remove_nodes_from(to_remove)
        edges_to_remove = [
            (u, v) for u, v, d in G.edges(data=True)
            if d.get("source_file") in prune_set
        ]
        if edges_to_remove:
            G.remove_edges_from(edges_to_remove)
        if to_remove or edges_to_remove:
            logger.info(f"Pruned {len(to_remove)} node(s), {len(edges_to_remove)} edge(s) from deleted sources.")

    if graph_path.exists() and not dedup and not prune_sources:
        existing_n = len(existing_nodes)
        new_n = G.number_of_nodes()
        if new_n < existing_n:
            raise ValueError(
                f"build_merge would shrink graph from {existing_n} → {new_n} nodes. "
                f"Pass prune_sources explicitly if you intend to remove nodes."
            )

    return G


def prefix_graph_for_global(G: nx.Graph, repo_tag: str) -> nx.Graph:
    relabel = {n: f"{repo_tag}::{n}" for n in G.nodes}
    H = nx.relabel_nodes(G, relabel, copy=True)
    for node, data in H.nodes(data=True):
        data["repo"] = repo_tag
        data.setdefault("local_id", node.split("::", 1)[1])
    return H


def prune_repo_from_graph(G: nx.Graph, repo_tag: str) -> int:
    to_remove = [n for n, d in G.nodes(data=True) if d.get("repo") == repo_tag]
    G.remove_nodes_from(to_remove)
    return len(to_remove)
