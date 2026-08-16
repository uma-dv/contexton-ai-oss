"""
Visualization module for ContextOn.AI OSS.

Generates interactive HTML graphs with quality badges (🟢🟡🔴).
"""

import json
from typing import Dict, Any, List


def generate_graph_html(graph, output_path: str = "graph.html") -> str:
    """
    Generate an interactive HTML visualization of the graph.
    
    Features:
    - Nodes colored by confidence (green=high, yellow=medium, red=low)
    - Quality badges (🟢🟡🔴) on each node
    - Clickable nodes with details
    - Community highlighting
    - Interactive zoom and pan
    
    Args:
        graph: ContextGraph instance
        output_path: Path to save HTML file
    
    Returns:
        Path to generated file
    """
    # Prepare node data
    nodes_data = []
    for nid, node in graph.nodes.items():
        confidence = node.get("confidence", 0)
        badge = "🟢" if confidence >= 0.8 else ("🟡" if confidence >= 0.5 else "🔴")
        color = "#22c55e" if confidence >= 0.8 else ("#eab308" if confidence >= 0.5 else "#ef4444")
        
        nodes_data.append({
            "id": nid,
            "label": node.get("content", "")[:50],
            "type": node.get("type", "unknown"),
            "confidence": confidence,
            "badge": badge,
            "color": color,
            "mentions": node.get("mentions", 0),
            "failures": node.get("failure_count", 0),
        })
    
    # Prepare edge data
    edges_data = []
    for edge in graph.edges:
        confidence = edge.get("confidence", 0.5)
        color = "#22c55e" if confidence >= 0.8 else ("#eab308" if confidence >= 0.5 else "#ef4444")
        
        edges_data.append({
            "source": edge["source"],
            "target": edge["target"],
            "type": edge.get("type", ""),
            "rationale": edge.get("rationale", ""),
            "confidence": confidence,
            "color": color,
        })
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ContextOn.AI OSS Visualization</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
        #graph {{ width: 100%; height: 80vh; border: 1px solid #ccc; }}
        .legend {{ padding: 10px; background: #f5f5f5; }}
        .legend-item {{ display: inline-block; margin-right: 20px; }}
        .badge {{ font-size: 1.2em; }}
        .details {{ padding: 10px; background: #fff; border-top: 1px solid #ccc; }}
    </style>
</head>
<body>
    <div class="legend">
        <h3>ContextOn.AI OSS - Quality Badges</h3>
        <span class="legend-item"><span class="badge">🟢</span> High Confidence (≥0.8)</span>
        <span class="legend-item"><span class="badge">🟡</span> Medium Confidence (0.5-0.8)</span>
        <span class="legend-item"><span class="badge">🔴</span> Low Confidence (<0.5)</span>
    </div>
    <div id="graph"></div>
    <div class="details" id="details">Click a node to see details</div>
    
    <script>
        var nodes = new vis.DataSet({json.dumps(nodes_data)});
        var edges = new vis.DataSet({json.dumps(edges_data)});
        
        var container = document.getElementById('graph');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            physics: {{ enabled: true }},
            nodes: {{
                shape: 'dot',
                size: 20,
                font: {{ size: 12 }},
                borderWidth: 2,
            }},
            edges: {{
                arrows: 'to',
                smooth: {{ type: 'continuous' }},
            }},
        }};
        
        var network = new vis.Network(container, data, options);
        
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                document.getElementById('details').innerHTML = 
                    '<h3>' + node.badge + ' ' + node.label + '</h3>' +
                    '<p><strong>Type:</strong> ' + node.type + '</p>' +
                    '<p><strong>Confidence:</strong> ' + (node.confidence * 100).toFixed(1) + '%</p>' +
                    '<p><strong>Mentions:</strong> ' + node.mentions + '</p>' +
                    '<p><strong>Failures:</strong> ' + node.failures + '</p>';
            }}
        }});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return output_path
