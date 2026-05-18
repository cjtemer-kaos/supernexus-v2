import base64
import requests
import time
import mss
import os

# Configuración
# La URL apunta a Hermes (Remote Node) a través de Tailscale
OLLAMA_URL = "http://100.83.38.20:11434/api/generate"
MODEL = "moondream"
SCREENSHOT_PATH = "local_vision.png"

def capture_screen():
    with mss.mss() as sct:
        # Captura el monitor principal
        sct.shot(output=SCREENSHOT_PATH)
    return SCREENSHOT_PATH

def analyze_screen(image_path):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    prompt = "¿Hay algún nodo en ROJO o con mensaje de ERROR en la interfaz de ComfyUI? Describe brevemente lo que ves."
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("response", "Sin respuesta.")
        else:
            return f"Error de Ollama: {response.status_code}"
    except Exception as e:
        return f"Error de conexión: {e}"

def main():
    print(f"--- Nexus Vision Loop (${USERNAME} -> Hermes) Iniciado ---")
    while True:
        print("\n[Capturando y Analizando...]")
        img = capture_screen()
        result = analyze_screen(img)
        print(f"Nexus ve: {result}")
        
        # Esperar 5 segundos antes de la siguiente revisión
        time.sleep(5)

if __name__ == "__main__":
    main()
