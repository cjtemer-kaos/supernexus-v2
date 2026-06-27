"""
codegraph — Knowledge Graph Engine for SuperNEXUS.

Builds, queries, analyzes, and exports code knowledge graphs from
AST extractions, semantic analysis, and file-level discovery.

Pipeline:
    extract() → build() → community() → analyze() → export()

Usage:
    from codegraph.builder import build_from_json, build_merge
    from codegraph.query import GraphQuery
    from codegraph.analyze import god_nodes, surprising_connections
    from codegraph.community import cluster, cohesion_score
    from codegraph.export import to_json, to_html
"""

from . import builder, query, analyze, community, export, dedup

__all__ = ["builder", "query", "analyze", "community", "export", "dedup"]
