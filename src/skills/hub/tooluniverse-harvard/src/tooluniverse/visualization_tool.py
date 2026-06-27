"""
Visualization Tool Base Class for ToolUniverse
==============================================

This module provides the base VisualizationTool class that all visualization
tools inherit from. It provides common functionality for HTML generation,
image conversion, error handling, and output formatting.
"""

import base64
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("VisualizationTool")
class VisualizationTool(BaseTool):
    """
    Base class for all visualization tools in ToolUniverse.

    Provides common functionality for:
    - HTML generation and embedding
    - Static image conversion
    - Error handling
    - Output formatting
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.name = tool_config.get("name")
        self.description = tool_config.get("description")

        # Default visualization settings
        self.default_width = tool_config.get("default_width", 800)
        self.default_height = tool_config.get("default_height", 600)
        self.default_style = tool_config.get("default_style", {})

    def create_visualization_response(
        self,
        html_content: str,
        viz_type: str,
        data: Optional[Dict] = None,
        static_image: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create a standardized visualization response."""
        response = {
            "success": True,
            "visualization": {
                "html": html_content,
                "type": viz_type,
                "data": data or {},
                "metadata": metadata or {},
            },
        }

        if static_image:
            response["visualization"]["static_image"] = static_image

        return response

    def create_error_response(
        self, error_message: str, error_type: str = "VisualizationError"
    ) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "success": False,
            "error": error_message,
            "error_type": error_type,
            "visualization": {
                "html": f"<div class='error'>Error: {error_message}</div>",
                "type": "error",
                "data": {},
                "metadata": {},
            },
        }

    def convert_to_base64_image(self, image_data: bytes, format: str = "PNG") -> str:
        """Convert image data to base64 string."""
        return base64.b64encode(image_data).decode("utf-8")

    def create_plotly_html(
        self,
        fig,
        width: Optional[int] = None,
        height: Optional[int] = None,
        include_plotlyjs: str = "cdn",
    ) -> str:
        """Create HTML from Plotly figure."""
        if width is None:
            width = self.default_width
        if height is None:
            height = self.default_height

        return fig.to_html(
            include_plotlyjs=include_plotlyjs,
            div_id=f"{self.name}_plot",
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["pan2d", "lasso2d", "select2d"],
            },
        )

    def create_py3dmol_html(
        self,
        viewer_html: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        title: str = None,
        info_cards: str = "",
        control_panel: str = "",
        toolbar: str = "",
    ) -> str:
        """Create modern HTML wrapper for py3Dmol viewer."""
        if width is None:
            width = self.default_width
        if height is None:
            height = self.default_height
        if title is None:
            title = f"{self.name} Visualization"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #f0f4f8 0%, #ffffff 100%);
                    min-height: 100vh;
                    color: #2c3e50;
                    line-height: 1.6;
                }}

                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                }}

                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}

                .title {{
                    font-size: 2.5rem;
                    font-weight: 300;
                    color: #4A90E2;
                    margin-bottom: 10px;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .subtitle {{
                    font-size: 1.1rem;
                    color: #7f8c8d;
                    font-weight: 300;
                }}

                .main-content {{
                    display: grid;
                    grid-template-columns: 1fr 300px;
                    gap: 30px;
                    margin-bottom: 30px;
                }}

                .viewer-section {{
                    position: relative;
                }}

                .viewer-container {{
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    overflow: hidden;
                    position: relative;
                }}

                .viewer-wrapper {{
                    position: relative;
                    width: 100%;
                    height: {height}px;
                }}

                .control-panel {{
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: rgba(255,255,255,0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.15);
                    z-index: 1000;
                    min-width: 200px;
                }}

                .control-group {{
                    margin-bottom: 15px;
                }}

                .control-group:last-child {{
                    margin-bottom: 0;
                }}

                .control-label {{
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: #34495e;
                    margin-bottom: 8px;
                    display: block;
                }}

                .control-select {{
                    width: 100%;
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background: white;
                    font-size: 0.9rem;
                    color: #2c3e50;
                    cursor: pointer;
                    transition: all 0.2s;
                }}

                .control-select:hover {{
                    border-color: #4A90E2;
                }}

                .control-select:focus {{
                    outline: none;
                    border-color: #4A90E2;
                    box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
                }}

                .toolbar {{
                    position: absolute;
                    bottom: 20px;
                    left: 20px;
                    display: flex;
                    gap: 10px;
                    z-index: 1000;
                }}

                .btn {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    padding: 10px 16px;
                    cursor: pointer;
                    font-size: 0.9rem;
                    font-weight: 500;
                    transition: all 0.2s;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }}

                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }}

                .btn:active {{
                    transform: translateY(0);
                }}

                .btn-secondary {{
                    background: linear-gradient(135deg, #50C878 0%, #4A90E2 100%);
                }}

                .btn-outline {{
                    background: transparent;
                    border: 2px solid #4A90E2;
                    color: #4A90E2;
                }}

                .btn-outline:hover {{
                    background: #4A90E2;
                    color: white;
                }}

                .info-section {{
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }}

                .card {{
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    padding: 20px;
                    transition: transform 0.2s;
                }}

                .card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 16px rgba(0,0,0,0.15);
                }}

                .card-title {{
                    font-size: 1.2rem;
                    font-weight: 600;
                    color: #2c3e50;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}

                .card-icon {{
                    width: 20px;
                    height: 20px;
                    fill: #4A90E2;
                }}

                .info-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                }}

                .info-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #ecf0f1;
                }}

                .info-item:last-child {{
                    border-bottom: none;
                }}

                .info-label {{
                    font-weight: 500;
                    color: #7f8c8d;
                }}

                .info-value {{
                    font-weight: 600;
                    color: #2c3e50;
                }}

                .interaction-hints {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    border-radius: 8px;
                    padding: 15px;
                    font-size: 0.9rem;
                    color: #6c757d;
                    text-align: center;
                    border-left: 4px solid #4A90E2;
                }}

                .hint-icon {{
                    display: inline-block;
                    margin-right: 5px;
                }}

                @media (max-width: 768px) {{
                    .main-content {{
                        grid-template-columns: 1fr;
                    }}

                    .control-panel {{
                        position: relative;
                        top: auto;
                        right: auto;
                        margin-bottom: 20px;
                    }}

                    .toolbar {{
                        position: relative;
                        bottom: auto;
                        left: auto;
                        margin-top: 20px;
                        justify-content: center;
                    }}

                    .title {{
                        font-size: 2rem;
                    }}

                    .info-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 class="title">{title}</h1>
                    <p class="subtitle">Interactive 3D Molecular Visualization</p>
                </div>

                <div class="main-content">
                    <div class="viewer-section">
                        <div class="viewer-container">
                            {control_panel}
                            <div class="viewer-wrapper">
                                {viewer_html}
                            </div>
                            {toolbar}
                        </div>
                    </div>

                    <div class="info-section">
                        {info_cards}
                        <div class="card">
                            <h3 class="card-title">
                                <svg class="card-icon" viewBox="0 0 24 24">
                                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                                </svg>
                                Interaction Guide
                            </h3>
                            <div class="interaction-hints">
                                <span class="hint-icon">🖱️</span> Drag to rotate |
                                <span class="hint-icon">🔍</span> Scroll to zoom |
                                <span class="hint-icon">✋</span> Right-click to pan
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def add_3d_controls_script(self) -> str:
        """Add JavaScript for 3D viewer controls."""
        return """
        <script>
            let viewer = null;

            // Wait for 3Dmol to load
            function waitFor3Dmol() {
                if (typeof $3Dmol !== 'undefined') {
                    // Find the viewer element
                    const viewerElements = document.querySelectorAll('[id^="3dmolviewer_"]');
                    if (viewerElements.length > 0) {
                        const viewerId = viewerElements[0].id;
                        viewer = window[viewerId.replace('3dmolviewer_', 'viewer_')];
                        if (viewer) {
                            console.log('3Dmol viewer found:', viewer);
                        }
                    }
                } else {
                    setTimeout(waitFor3Dmol, 100);
                }
            }

            // Style change function
            function changeStyle() {
                if (!viewer) return;
                const style = document.getElementById('styleSelect').value;
                const color = document.getElementById('colorSelect').value;

                viewer.setStyle({}, {}); // Clear current style

                if (style === 'cartoon') {
                    viewer.setStyle({cartoon: {color: color}});
                } else if (style === 'stick') {
                    viewer.setStyle({stick: {color: color}});
                } else if (style === 'sphere') {
                    viewer.setStyle({sphere: {color: color}});
                } else if (style === 'line') {
                    viewer.setStyle({line: {color: color}});
                } else if (style === 'surface') {
                    viewer.addSurface($3Dmol.VDW, {opacity: 0.7, color: 'white'});
                }

                viewer.render();
            }

            // Color change function
            function changeColor() {
                if (!viewer) return;
                const style = document.getElementById('styleSelect').value;
                const color = document.getElementById('colorSelect').value;

                viewer.setStyle({}, {}); // Clear current style

                if (style === 'cartoon') {
                    viewer.setStyle({cartoon: {color: color}});
                } else if (style === 'stick') {
                    viewer.setStyle({stick: {color: color}});
                } else if (style === 'sphere') {
                    viewer.setStyle({sphere: {color: color}});
                } else if (style === 'line') {
                    viewer.setStyle({line: {color: color}});
                }

                viewer.render();
            }

            // Background change function
            function changeBackground() {
                if (!viewer) return;
                const bg = document.getElementById('bgSelect').value;
                viewer.setBackgroundColor(bg);
            }

            // Reset view function
            function resetView() {
                if (!viewer) return;
                viewer.zoomTo();
                viewer.render();
            }

            // Screenshot function
            function downloadScreenshot() {
                if (!viewer) return;
                const img = viewer.pngURI();
                const link = document.createElement('a');
                link.download = 'protein_structure.png';
                link.href = img;
                link.click();
            }

            // Fullscreen function
            function toggleFullscreen() {
                const container = document.querySelector('.viewer-container');
                if (!document.fullscreenElement) {
                    container.requestFullscreen().catch(err => {
                        console.log('Error attempting to enable fullscreen:', err);
                    });
                } else {
                    document.exitFullscreen();
                }
            }

            // Initialize when page loads
            document.addEventListener('DOMContentLoaded', function() {
                waitFor3Dmol();
            });
        </script>
        """

    def create_molecule_2d_html(
        self,
        molecule_image: str,
        molecule_info: Dict[str, Any],
        width: Optional[int] = None,
        height: Optional[int] = None,
        title: str = None,
    ) -> str:
        """Create modern HTML for 2D molecule visualization."""
        if width is None:
            width = self.default_width
        if height is None:
            height = self.default_height
        if title is None:
            title = f"{self.name} Visualization"

        # Extract molecule properties
        smiles = molecule_info.get("smiles", "N/A")
        mol_weight = molecule_info.get("molecular_weight", 0)
        logp = molecule_info.get("logp", 0)
        hbd = molecule_info.get("hbd", 0)
        hba = molecule_info.get("hba", 0)
        tpsa = molecule_info.get("tpsa", 0)
        rotatable_bonds = molecule_info.get("rotatable_bonds", 0)
        aromatic_rings = molecule_info.get("aromatic_rings", 0)
        heavy_atoms = molecule_info.get("heavy_atoms", 0)
        formal_charge = molecule_info.get("formal_charge", 0)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #f0f4f8 0%, #ffffff 100%);
                    min-height: 100vh;
                    color: #2c3e50;
                    line-height: 1.6;
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}

                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}

                .title {{
                    font-size: 2.5rem;
                    font-weight: 300;
                    color: #4A90E2;
                    margin-bottom: 10px;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .subtitle {{
                    font-size: 1.1rem;
                    color: #7f8c8d;
                    font-weight: 300;
                }}

                .main-content {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 30px;
                    margin-bottom: 30px;
                }}

                .molecule-section {{
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    padding: 30px;
                    text-align: center;
                }}

                .molecule-image {{
                    margin: 20px 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}

                .molecule-image img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 8px;
                }}

                .properties-section {{
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }}

                .card {{
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    padding: 20px;
                    transition: transform 0.2s;
                }}

                .card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 16px rgba(0,0,0,0.15);
                }}

                .card-title {{
                    font-size: 1.2rem;
                    font-weight: 600;
                    color: #2c3e50;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}

                .card-icon {{
                    width: 20px;
                    height: 20px;
                    fill: #4A90E2;
                }}

                .property-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                }}

                .property-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    border-radius: 8px;
                    border-left: 4px solid #4A90E2;
                    transition: all 0.2s;
                }}

                .property-item:hover {{
                    background: linear-gradient(135deg, #e3f2fd 0%, #f8f9fa 100%);
                    transform: translateX(4px);
                }}

                .property-label {{
                    font-weight: 500;
                    color: #7f8c8d;
                    font-size: 0.9rem;
                }}

                .property-value {{
                    font-weight: 600;
                    color: #2c3e50;
                    font-size: 1rem;
                }}

                .property-unit {{
                    font-size: 0.8rem;
                    color: #95a5a6;
                    margin-left: 4px;
                }}

                .smiles-display {{
                    background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
                    border-radius: 8px;
                    padding: 15px;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9rem;
                    color: #2c3e50;
                    border-left: 4px solid #50C878;
                    word-break: break-all;
                }}

                .download-section {{
                    text-align: center;
                    margin-top: 20px;
                }}

                .btn {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    padding: 12px 24px;
                    cursor: pointer;
                    font-size: 1rem;
                    font-weight: 500;
                    transition: all 0.2s;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    margin: 0 10px;
                }}

                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }}

                .btn-secondary {{
                    background: linear-gradient(135deg, #50C878 0%, #4A90E2 100%);
                }}

                @media (max-width: 768px) {{
                    .main-content {{
                        grid-template-columns: 1fr;
                    }}

                    .property-grid {{
                        grid-template-columns: 1fr;
                    }}

                    .title {{
                        font-size: 2rem;
                    }}

                    .molecule-section {{
                        padding: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 class="title">{title}</h1>
                    <p class="subtitle">2D Molecular Structure Analysis</p>
                </div>

                <div class="main-content">
                    <div class="molecule-section">
                        <h3 style="color: #2c3e50; margin-bottom: 20px;">Molecular Structure</h3>
                        <div class="molecule-image">
                            <img src="data:image/png;base64,{molecule_image}"
                                 alt="2D Molecular Structure"
                                 style="max-width: 100%; height: auto;">
                        </div>
                        <div class="download-section">
                            <button class="btn" onclick="downloadImage()">Download PNG</button>
                            <button class="btn btn-secondary" onclick="copySMILES()">Copy SMILES</button>
                        </div>
                    </div>

                    <div class="properties-section">
                        <div class="card">
                            <h3 class="card-title">
                                <svg class="card-icon" viewBox="0 0 24 24">
                                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                                </svg>
                                Basic Properties
                            </h3>
                            <div class="property-grid">
                                <div class="property-item">
                                    <span class="property-label">Molecular Weight</span>
                                    <span class="property-value">{mol_weight:.2f}<span class="property-unit">Da</span></span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">Heavy Atoms</span>
                                    <span class="property-value">{heavy_atoms}</span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">Formal Charge</span>
                                    <span class="property-value">{formal_charge}</span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">Aromatic Rings</span>
                                    <span class="property-value">{aromatic_rings}</span>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <h3 class="card-title">
                                <svg class="card-icon" viewBox="0 0 24 24">
                                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                                </svg>
                                Drug Properties
                            </h3>
                            <div class="property-grid">
                                <div class="property-item">
                                    <span class="property-label">LogP</span>
                                    <span class="property-value">{logp:.2f}</span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">TPSA</span>
                                    <span class="property-value">{tpsa:.2f}<span class="property-unit">Å²</span></span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">H-Bond Donors</span>
                                    <span class="property-value">{hbd}</span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">H-Bond Acceptors</span>
                                    <span class="property-value">{hba}</span>
                                </div>
                                <div class="property-item">
                                    <span class="property-label">Rotatable Bonds</span>
                                    <span class="property-value">{rotatable_bonds}</span>
                                </div>
                            </div>
                        </div>

                        <div class="card">
                            <h3 class="card-title">
                                <svg class="card-icon" viewBox="0 0 24 24">
                                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                                </svg>
                                SMILES Notation
                            </h3>
                            <div class="smiles-display">{smiles}</div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                function downloadImage() {{
                    const img = document.querySelector('.molecule-image img');
                    const link = document.createElement('a');
                    link.download = 'molecule_structure.png';
                    link.href = img.src;
                    link.click();
                }}

                function copySMILES() {{
                    const smiles = '{smiles}';
                    navigator.clipboard.writeText(smiles).then(function() {{
                        alert('SMILES copied to clipboard!');
                    }});
                }}
            </script>
        </body>
        </html>
        """
