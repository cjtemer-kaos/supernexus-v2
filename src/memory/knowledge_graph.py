"""
KnowledgeGraph - Grafo de conocimiento con visualización para SuperNEXUS v2.0

Características:
- Nodos y conexiones entre conceptos
- Backlinks automáticos entre notas markdown
- Análisis de dependencias entre componentes
- Exportación para visualización en UI
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Nodo en el grafo de conocimiento"""
    id: str
    label: str
    node_type: str
    content: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = hashlib.md5(f"{self.label}{self.node_type}".encode()).hexdigest()[:12]


@dataclass
class GraphEdge:
    """Conexión entre nodos"""
    source: str
    target: str
    edge_type: str
    weight: float = 1.0
    description: str = ""


class KnowledgeGraph:
    """
    Grafo de conocimiento para SuperNEXUS v2.0
    
    Uso:
        graph = KnowledgeGraph()
        graph.add_node("concept_1", "Python", "concept", tags=["programming"])
        graph.add_node("concept_2", "FastAPI", "concept", tags=["web", "python"])
        graph.add_edge("concept_1", "concept_2", "related_to")
        
        visualization = graph.export_for_visualization()
    """
    
    def __init__(self, storage_path: str = None):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.storage_path = Path(storage_path) if storage_path else None
        
        if self.storage_path and self.storage_path.exists():
            self.load()
    
    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        content: str = "",
        tags: List[str] = None,
        metadata: Dict = None,
    ) -> GraphNode:
        """Agrega nodo al grafo"""
        node = GraphNode(
            id=node_id,
            label=label,
            node_type=node_type,
            content=content,
            tags=tags or [],
            metadata=metadata or {},
            updated_at=datetime.now().isoformat(),
        )
        
        self.nodes[node_id] = node
        logger.debug(f"Node added: {node_id} ({label})")
        
        return node
    
    def remove_node(self, node_id: str):
        """Elimina nodo y sus conexiones"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            
            self.edges = [
                e for e in self.edges
                if e.source != node_id and e.target != node_id
            ]
            
            if node_id in self.adjacency:
                del self.adjacency[node_id]
            
            for source in self.adjacency:
                self.adjacency[source].discard(node_id)
            
            logger.debug(f"Node removed: {node_id}")
    
    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        description: str = "",
    ) -> GraphEdge:
        """Agrega conexión entre nodos"""
        if source not in self.nodes or target not in self.nodes:
            logger.warning(f"Cannot add edge: node(s) not found ({source} -> {target})")
            return None
        
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            description=description,
        )
        
        self.edges.append(edge)
        self.adjacency[source].add(target)
        
        logger.debug(f"Edge added: {source} -> {target} ({edge_type})")
        
        return edge
    
    def add_backlink(self, source: str, target: str, description: str = ""):
        """Agrega backlink bidireccional"""
        self.add_edge(source, target, "backlink", description=description)
        self.add_edge(target, source, "backlink", description=description)
    
    def find_related(self, node_id: str, max_depth: int = 2) -> Dict[str, GraphNode]:
        """Encuentra nodos relacionados"""
        if node_id not in self.nodes:
            return {}
        
        visited = set()
        queue = [(node_id, 0)]
        related = {}
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            if current_id != node_id and current_id in self.nodes:
                related[current_id] = self.nodes[current_id]
            
            for neighbor in self.adjacency.get(current_id, set()):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        
        return related
    
    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        """Encuentra camino entre dos nodos (BFS)"""
        if source not in self.nodes or target not in self.nodes:
            return None
        
        visited = {source}
        queue = [(source, [source])]
        
        while queue:
            current, path = queue.pop(0)
            
            if current == target:
                return path
            
            for neighbor in self.adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def analyze_dependencies(self, node_id: str) -> Dict:
        """Analiza dependencias de un nodo"""
        if node_id not in self.nodes:
            return {"error": "Node not found"}
        
        incoming = [e for e in self.edges if e.target == node_id]
        outgoing = [e for e in self.edges if e.source == node_id]
        
        related = self.find_related(node_id)
        
        return {
            "node": self.nodes[node_id].label,
            "incoming_dependencies": len(incoming),
            "outgoing_dependencies": len(outgoing),
            "total_related": len(related),
            "related_nodes": list(related.keys()),
        }
    
    def get_central_nodes(self, top_n: int = 10) -> List[Dict]:
        """Obtiene nodos más centrales (más conexiones)"""
        connection_count = defaultdict(int)
        
        for edge in self.edges:
            connection_count[edge.source] += 1
            connection_count[edge.target] += 1
        
        sorted_nodes = sorted(
            connection_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return [
            {
                "id": node_id,
                "label": self.nodes[node_id].label if node_id in self.nodes else "unknown",
                "connections": count,
            }
            for node_id, count in sorted_nodes[:top_n]
            if node_id in self.nodes
        ]
    
    def export_for_visualization(self) -> Dict:
        """Exporta grafo para visualización en UI"""
        nodes_data = [
            {
                "id": node.id,
                "label": node.label,
                "type": node.node_type,
                "tags": node.tags,
                "metadata": node.metadata,
            }
            for node in self.nodes.values()
        ]
        
        edges_data = [
            {
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
                "weight": edge.weight,
                "description": edge.description,
            }
            for edge in self.edges
        ]
        
        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "stats": self.get_stats(),
        }
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del grafo"""
        node_types = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.node_type] += 1
        
        edge_types = defaultdict(int)
        for edge in self.edges:
            edge_types[edge.edge_type] += 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "avg_connections": (
                len(self.edges) * 2 / len(self.nodes)
                if len(self.nodes) > 0 else 0
            ),
        }
    
    def save(self):
        """Guarda grafo en disco"""
        if not self.storage_path:
            return
        
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "nodes": {
                node_id: {
                    "id": node.id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "content": node.content,
                    "tags": node.tags,
                    "created_at": node.created_at,
                    "updated_at": node.updated_at,
                    "metadata": node.metadata,
                }
                for node_id, node in self.nodes.items()
            },
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "edge_type": edge.edge_type,
                    "weight": edge.weight,
                    "description": edge.description,
                }
                for edge in self.edges
            ],
        }
        
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Knowledge graph saved: {self.storage_path}")
    
    def load(self):
        """Carga grafo desde disco"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        with open(self.storage_path, "r") as f:
            data = json.load(f)
        
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        
        for node_id, node_data in data.get("nodes", {}).items():
            node = GraphNode(
                id=node_data["id"],
                label=node_data["label"],
                node_type=node_data["node_type"],
                content=node_data.get("content", ""),
                tags=node_data.get("tags", []),
                created_at=node_data.get("created_at", ""),
                updated_at=node_data.get("updated_at", ""),
                metadata=node_data.get("metadata", {}),
            )
            self.nodes[node_id] = node
        
        for edge_data in data.get("edges", []):
            edge = GraphEdge(
                source=edge_data["source"],
                target=edge_data["target"],
                edge_type=edge_data["edge_type"],
                weight=edge_data.get("weight", 1.0),
                description=edge_data.get("description", ""),
            )
            self.edges.append(edge)
            self.adjacency[edge.source].add(edge.target)
        
        logger.info(f"Knowledge graph loaded: {len(self.nodes)} nodes, {len(self.edges)} edges")
