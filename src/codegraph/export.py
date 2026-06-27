import json
import logging
import re
from pathlib import Path
from typing import Optional

import networkx as nx


logger = logging.getLogger("codegraph.export")


def _dir_preserving_edge(G: nx.Graph, u: str, v: str, data: dict) -> tuple[str, str, dict]:
    src = data.get("_src", u)
    tgt = data.get("_tgt", v)
    if src not in G.nodes:
        src = u
    if tgt not in G.nodes:
        tgt = v
    return src, tgt, data


def _collect_edge_data(G: nx.Graph) -> list[dict]:
    edges_list = []
    for u, v, data in G.edges(data=True):
        src, tgt, data = _dir_preserving_edge(G, u, v, data)
        edge_entry = {
            "source": src,
            "target": tgt,
            "relation": data.get("relation", "references"),
            "weight": data.get("weight", 1.0),
            "confidence": data.get("confidence", "EXTRACTED"),
        }
        if "source_file" in data:
            edge_entry["source_file"] = data["source_file"]
        for key in ("_src", "_tgt"):
            edge_entry.pop(key, None)
        edges_list.append(edge_entry)
    return edges_list


def to_json(G: nx.Graph, path: str | Path, pretty: bool = True) -> None:
    path = Path(path)
    nodes_list = []
    for nid, data in G.nodes(data=True):
        node_entry = dict(data)
        node_entry["id"] = nid
        community = node_entry.pop("community", None)
        if community is not None:
            node_entry["community"] = community
        nodes_list.append(node_entry)

    graph_data = {
        "nodes": nodes_list,
        "edges": _collect_edge_data(G),
        "metadata": {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "is_directed": G.is_directed(),
        },
    }
    if G.graph.get("hyperedges"):
        graph_data["hyperedges"] = G.graph["hyperedges"]

    indent = 2 if pretty else None
    path.write_text(json.dumps(graph_data, indent=indent, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Graph exported to {path} ({len(nodes_list)} nodes, {len(graph_data['edges'])} edges)")


def to_html(
    G: nx.Graph,
    path: str | Path,
    title: str = "Code Graph",
    community_labels: Optional[dict[int, str]] = None,
) -> None:
    path = Path(path)
    nodes_list = []
    edges_list = []

    for nid, data in G.nodes(data=True):
        label = data.get("label", nid)
        community = data.get("community", -1)
        comm_label = ""
        if community >= 0 and community_labels:
            comm_label = community_labels.get(community, f"Community {community}")
        title_attr = nid
        if data.get("source_file"):
            title_attr += f"\n{data['source_file']}"
        nodes_list.append({
            "id": nid,
            "label": label,
            "title": title_attr,
            "group": community if community >= 0 else 0,
            "community_label": comm_label,
            "size": min(30, 5 + G.degree(nid)),
            "shape": "dot",
        })

    for u, v, data in G.edges(data=True):
        src, tgt, data = _dir_preserving_edge(G, u, v, data)
        edges_list.append({
            "from": src,
            "to": tgt,
            "label": data.get("relation", ""),
            "title": f"confidence: {data.get('confidence', 'EXTRACTED')}",
            "color": {"EXTRACTED": "#4caf50", "INFERRED": "#ff9800", "AMBIGUOUS": "#f44336"}
                       .get(data.get("confidence", "EXTRACTED"), "#999"),
            "width": data.get("weight", 1.0),
            "arrows": "to" if G.is_directed() else None,
        })

    community_colors = [
        "#2196f3", "#f44336", "#4caf50", "#ff9800", "#9c27b0",
        "#00bcd4", "#e91e63", "#3f51b5", "#8bc34a", "#ff5722",
        "#607d8b", "#795548", "#009688", "#ffc107", "#673ab7",
    ]

    groups_js = json.dumps({
        str(i): {"color": community_colors[i % len(community_colors)]}
        for i in set(d.get("group", 0) for d in nodes_list)
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/vis-network.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/dist/vis-network.min.css">
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: #1e1e2e; color: #cdd6f4; }}
  #controls {{ position: fixed; top: 10px; left: 10px; z-index: 100; background: rgba(30,30,46,0.9); padding: 12px; border-radius: 8px; }}
  #controls input {{ padding: 8px; border-radius: 4px; border: 1px solid #45475a; background: #313244; color: #cdd6f4; width: 200px; }}
  #controls select {{ padding: 8px; border-radius: 4px; border: 1px solid #45475a; background: #313244; color: #cdd6f4; }}
  #controls button {{ padding: 8px 16px; border-radius: 4px; border: none; background: #89b4fa; color: #1e1e2e; cursor: pointer; }}
  #network {{ width: 100vw; height: 100vh; }}
  #legend {{ position: fixed; bottom: 10px; right: 10px; z-index: 100; background: rgba(30,30,46,0.9); padding: 8px; border-radius: 8px; font-size: 12px; }}
  #stats {{ position: fixed; bottom: 10px; left: 10px; z-index: 100; font-size: 12px; color: #6c7086; }}
</style>
</head>
<body>
<div id="controls">
  <input id="search" type="text" placeholder="Search nodes..." />
  <select id="communityFilter"><option value="">All Communities</option></select>
  <button onclick="resetView()">Reset</button>
</div>
<div id="network"></div>
<div id="legend"><div style="color:#4caf50">■ EXTRACTED</div><div style="color:#ff9800">■ INFERRED</div><div style="color:#f44336">■ AMBIGUOUS</div></div>
<div id="stats">{G.number_of_nodes()} nodes · {G.number_of_edges()} edges</div>
<script>
const nodes = new vis.DataSet({json.dumps(nodes_list)});
const edges = new vis.DataSet({json.dumps(edges_list)});
const groups = {groups_js};

const container = document.getElementById('network');
const data = {{ nodes, edges }};
const options = {{
  physics: {{ solver: 'forceAtlas2Based', forceAtlas2Based: {{ gravitationalConstant: -40, centralGravity: 0.005, springLength: 120, springConstant: 0.02 }}, stabilization: {{ iterations: 200 }} }},
  edges: {{ smooth: {{ type: 'continuous' }}, font: {{ size: 10, color: '#6c7086' }} }},
  nodes: {{ font: {{ size: 12, color: '#cdd6f4' }}, borderWidth: 1, color: {{ border: '#45475a', background: '#313244' }} }},
  groups,
  interaction: {{ hover: true, tooltipDelay: 200, navigationButtons: true, keyboard: true }},
  layout: {{ improvedLayout: true }}
}};
const network = new vis.Network(container, data, options);
network.on('click', function(params) {{
  if (params.nodes.length) {{
    network.selectNodes([params.nodes[0]]);
    network.focus(params.nodes[0], {{ scale: 2 }});
  }}
}});

document.getElementById('search').addEventListener('input', function() {{
  const q = this.value.toLowerCase();
  nodes.forEach(function(n) {{
    if (!q || n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)) {{
      network.selectNodes([n.id]);
      network.focus(n.id, {{ scale: 1.5 }});
    }}
  }});
}});

const communities = new Set(nodes.get().map(n => n.community_label).filter(Boolean));
const sel = document.getElementById('communityFilter');
communities.forEach(c => {{ const o = document.createElement('option'); o.value = c; o.text = c; sel.appendChild(o); }});
sel.addEventListener('change', function() {{
  const val = this.value;
  nodes.forEach(function(n) {{
    const match = !val || n.community_label === val;
    if (network.body && network.body.nodes[n.id]) {{
      network.body.nodes[n.id].options.hidden = !match;
    }}
  }});
  network.redraw();
}});

function resetView() {{ network.fit({{ animation: true }}); }}
</script>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")
    logger.info(f"HTML graph exported to {path}")


def _sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", label)
    if sanitized and sanitized[0].isdigit():
        sanitized = "n_" + sanitized
    return sanitized or "node"


def to_cypher(
    G: nx.Graph,
    path: str | Path,
    community_labels: Optional[dict[int, str]] = None,
) -> None:
    path = Path(path)
    lines = [
        "// SuperNEXUS Code Graph — Neo4j Cypher Export",
        f"// {G.number_of_nodes()} nodes, {G.number_of_edges()} edges",
        "",
        "// Constraints",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:CodeNode) REQUIRE n.id IS UNIQUE;",
        "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.label);",
        "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.source_file);",
        "",
        "// Nodes",
    ]

    for nid, data in G.nodes(data=True):
        label = data.get("label", nid)
        source_file = data.get("source_file", "")
        file_type = data.get("file_type", "concept")
        comm = data.get("community", -1)
        props = {
            "id": nid,
            "label": label,
            "file_type": file_type,
            "source_file": source_file,
        }
        if comm >= 0:
            comm_label = "Unknown"
            if community_labels:
                comm_label = community_labels.get(comm, f"Community_{comm}")
            else:
                comm_label = f"Community_{comm}"
            props["community"] = comm
            props["community_label"] = comm_label

        props_str = ", ".join(f"{k}: {json.dumps(v)}" for k, v in props.items())
        lines.append(f"MERGE (n:CodeNode:FileType_{file_type} {{ {props_str} }});")

    lines.append("")
    lines.append("// Edges")
    for u, v, data in G.edges(data=True):
        src, tgt, data = _dir_preserving_edge(G, u, v, data)
        rel_type = _sanitize_label(data.get("relation", "references")).upper()
        conf = data.get("confidence", "EXTRACTED")
        weight = data.get("weight", 1.0)
        lines.append(
            f"MATCH (a:CodeNode {{ id: {json.dumps(src)} }}) "
            f"MATCH (b:CodeNode {{ id: {json.dumps(tgt)} }}) "
            f"MERGE (a)-[r:{rel_type} {{ confidence: {json.dumps(conf)}, weight: {weight} }}]->(b);"
        )

    lines.append("")
    lines.append("// Community toplogy")
    if community_labels:
        for comm_id, label in community_labels.items():
            safe_label = _sanitize_label(label)
            lines.append(
                f"MATCH (n:CodeNode) WHERE n.community = {comm_id} "
                f"SET n.community_name = {json.dumps(label)};"
            )

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Cypher export written to {path}")
