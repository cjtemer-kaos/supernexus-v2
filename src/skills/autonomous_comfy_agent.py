import base64
import requests
import time
import mss
import pyautogui
import json

# Configuración
Remote Node_OLLAMA_URL = "http://100.83.38.20:11434/api/generate"
Remote Node_MINIMAX_URL = "http://100.83.38.20:8000/v1/chat/completions" # Asumiendo API de Minimax en Remote Node
VISION_MODEL = "moondream"
SCREENSHOT_PATH = "agent_vision.png"

# Desactivar el fail-safe de pyautogui para permitir control total (usar con cuidado)
pyautogui.FAILSAFE = True

def capture_screen():
    with mss.mss() as sct:
        sct.shot(output=SCREENSHOT_PATH)
    return SCREENSHOT_PATH

def get_vision_analysis(image_path):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    prompt = "Analiza esta interfaz de ComfyUI. Dime qué nodos ves y si hay alguno con error (color rojo). Necesito coordenadas aproximadas (x,y) de los elementos principales."
    
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False
    }
    
    try:
        res = requests.post(Remote Node_OLLAMA_URL, json=payload, timeout=30)
        return res.json().get("response", "")
    except Exception as e:
        return f"Error de visión: {e}"

def ask_minimax_for_action(vision_data, goal):
    # Aquí es donde el cerebro de Remote Node toma la decisión pesada
    # Usamos un prompt de razonamiento avanzado
    prompt = f"""
    CONTEXTO VISUAL: {vision_data}
    OBJETIVO: {goal}
    
    Eres el cerebro de automatización de Nexus corriendo en Remote Node.
    Tu tarea es decidir el siguiente movimiento de ratón o teclado en ${USERNAME}.
    Responde ÚNICAMENTE en formato JSON:
    {{"action": "move_to", "x": 500, "y": 300, "reason": "descripción"}}
    O
    {{"action": "click", "button": "left"}}
    O
    {{"action": "wait", "seconds": 2}}
    """
    
    # Por ahora simulamos la llamada a Minimax (que implementaremos en la siguiente fase)
    # Si no hay API directa, usaremos un puente SSH
    return {"action": "wait", "reason": "Iniciando cerebro de Hermes..."}

def main():
    goal = "Cargar el flujo de trabajo LTX y ejecutar el render."
    print(f"--- AGENTE AUTÓNOMO NEXUS (Cerebro: Hermes | Cuerpo: ${USERNAME}) ---")
    
    while True:
        print("\n[Hermes Capturando Pantalla...]")
        img = capture_screen()
        
        print("[Hermes Analizando Visión...]")
        vision_info = get_vision_analysis(img)
        print(f"Visión: {vision_info[:100]}...")
        
        print("[Minimax Razonando Acción...]")
        # Delegamos en el cerebro superior
        decision = ask_minimax_for_action(vision_info, goal)
        
        # Ejecutar acción
        print(f"Acción decidida: {decision}")
        if decision["action"] == "move_to":
            pyautogui.moveTo(decision["x"], decision["y"], duration=1)
        elif decision["action"] == "click":
            pyautogui.click()
            
        time.sleep(3)

if __name__ == "__main__":
    main()
