class VisionSkill:
    name = "vision"
    
    def __init__(self):
        self.last_image = None
    
    def analyze(self, image_path=None, custom_prompt=None, model="qwen2.5vl:7b"):
        import base64, requests, os
        
        # Configuración centralizada: PC2 (Hermes) es el motor de visión soberano
        PC2_IP = "100.83.38.20"
        OLLAMA_URL = f"http://{PC2_IP}:11434"
        VISION_MODEL = model # Usamos el modelo pasado por parámetro
        
        if not image_path:
            image_path = self.last_image
        
        if not image_path or not os.path.exists(image_path):
            return {"error": "No image provided", "suggestion": "Provide image path or attach screenshot"}
        
        prompt = custom_prompt or "Describe esta imagen en detalle. ¿Qué elementos de UI ves? ¿Cuál es el contexto? (Responde en español)"
        
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            
            r = requests.post(f"{OLLAMA_URL}/api/generate",
                json={"model": VISION_MODEL, "prompt": prompt, "images": [img_b64], "stream": False},
                timeout=300) # Tiempo extendido para modelos pesados como Qwen VL
            
            if r.status_code == 200:
                return {"response": r.json().get("response", ""), "image": image_path, "node": "PC2", "model": VISION_MODEL}
            else:
                return {"error": f"Ollama PC2 Error: {r.text}", "status": r.status_code}
        except Exception as e:
            return {"error": f"Fallo de conexión con PC2 Vision: {str(e)}"}
    
    def detect_ui(self, image_path):
        return self.analyze(image_path, "Describe the UI elements, buttons, menus, forms. What framework does it use?")
    
    def detect_error(self, image_path):
        return self.analyze(image_path, "Analyze this screenshot. Is there an error message? What does it say?")
    
    def detect_data(self, image_path):
        return self.analyze(image_path, "Describe any charts, graphs, tables or data visualizations. What data do you see?")
    
    def info(self):
        return {"name": "vision", "methods": ["analyze", "detect_ui", "detect_error", "detect_data"]}


class ImageAnalyzer:
    """Automatic image analyzer that processes screenshots when attached"""
    
    def __init__(self):
        import os
        from pathlib import Path
        _project = Path(__file__).resolve().parents[2]
        self.temp_dir = str(_project / "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def process_image(self, image_path, context=""):
        import base64, requests, os
        
        if not os.path.exists(image_path):
            return {"error": "Image not found", "path": image_path}
        
        # Auto-detect context from the conversation
        prompt = self._infer_prompt(context)
        
        PC2_IP = "100.83.38.20"
        OLLAMA_URL = f"http://{PC2_IP}:11434/api/generate"
        VISION_MODEL = "qwen2.5vl:7b"
        
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            
            r = requests.post(OLLAMA_URL,
                json={"model": VISION_MODEL, "prompt": prompt, "images": [img_b64], "stream": False},
                timeout=300)
            
            if r.status_code == 200:
                response = r.json().get("response", "")
                # Parse response into structured analysis
                return self._parse_analysis(response, context)
            else:
                return {"error": r.text, "status": r.status_code}
        except Exception as e:
            return {"error": f"Fallo de conexión con PC2 Vision: {str(e)}"}
    
    def _infer_prompt(self, context):
        context = context.lower()
        if any(w in context for w in ["error", "bug", "crash", "fail", "exception", "traceback", "error"]):
            return "Analyze this error screenshot. What is the error message? What causes it? How to fix it?"
        if any(w in context for w in ["ui", "button", "menu", "interface", "design", "layout", "panel"]):
            return "Describe the UI. What elements are present? What framework (React, Vue, etc)? What is the layout?"
        if any(w in context for w in ["data", "chart", "graph", "table", "metrics", "statistics"]):
            return "Describe the data visualizations. What charts? What data values do you see?"
        if any(w in context for w in ["code", "log", "terminal", "console"]):
            return "Analyze this code/log screenshot. What does it show? Any errors?"
        if any(w in context for w in ["documentation", "readme", "doc", "manual"]):
            return "Summarize this documentation. What is being explained?"
        return "Describe what you see in this image in detail."
    
    def _parse_analysis(self, response, context):
        return {
            "analysis": response,
            "context": context,
            "type": self._detect_type(context),
            "actions": self._suggest_actions(response, context)
        }
    
    def _detect_type(self, context):
        context = context.lower()
        if "error" in context: return "error"
        if "ui" in context: return "ui"
        if "data" in context: return "data"
        return "general"
    
    def _suggest_actions(self, response, context):
        suggestions = []
        response_lower = response.lower()
        
        if "error" in context or "error" in response_lower:
            suggestions.append("debug_fix")
            suggestions.append("search_solution")
        if "button" in response_lower or "menu" in response_lower:
            suggestions.append("analyze_ui")
            suggestions.append("generate_code")
        if "chart" in response_lower or "graph" in response_lower:
            suggestions.append("extract_data")
        return suggestions
    
    def info(self):
        return {"name": "image_analyzer", "capability": "Auto-analyze screenshots"}


class ScreenCaptureSkill:
    """Handles automatic screenshot processing"""
    
    name = "screen_capture"
    
    def __init__(self):
        self.analyzer = ImageAnalyzer()
        self.screenshots = []
    
    def capture_and_analyze(self, prompt=None):
        """Auto-capture screen and analyze (Supports Windows and Linux)"""
        import subprocess, os, tempfile, platform
        
        # Take screenshot based on OS
        output = os.path.join(tempfile.gettempdir(), f"capture_{int(__import__('time').time())}.png")
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["powershell", "-Command", 
                    f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bitmap.Save('{output}')"],
                    capture_output=True, timeout=10)
            else:
                # Linux support (scrot)
                subprocess.run(["scrot", "-o", output], capture_output=True, timeout=10)
        except Exception as e:
            return {"error": f"Could not capture screen: {str(e)}"}
        
        if not os.path.exists(output):
            return {"error": "Capture failed or screenshot tool missing"}
        
        return self.analyzer.process_image(output, prompt or "")
    
    def process_path(self, image_path, context=""):
        if not os.path.exists(image_path):
            return {"error": "Image not found"}
        return self.analyzer.process_image(image_path, context)
    
    def info(self):
        return {"name": "screen_capture", "methods": ["capture_and_analyze", "process_path"]}