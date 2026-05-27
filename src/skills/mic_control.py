#!/usr/bin/env python3
"""
MIC ON/OFF - Control de microfono por consola
micon  - Enciende microphone para recibir ordenes
micoff - Apaga microphone
"""

import sys
import threading
import queue
import time
import os
import io
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Skill deshabilitada - requiere audio_controller externo
# from core.mic_control import AudioController
# from core.pc_controller import PCController

class MicControlSkill:
    status = "DISABLED"
    reason = "audio_controller no disponible"

def info():
    return {"skill": "mic_control", "status": status, "reason": reason}

# Estado global
is_listening = False
listen_thread = None
command_queue = queue.Queue()
audio_ctrl = None
pc_ctrl = None

def process_command(text):
    """Procesa comando de voz"""
    text = text.lower().strip()
    print(f"\n>>> VOZ: '{text}'")
    
    # Enviar a Ollama para interpretar
    prompt = f"""El usuario dijo: "{text}"
Responde SOLO con JSON:
- click x,y
- type texto
- press tecla
- hotkey key1 key2
- scroll up/down
- describe
- none

Ejemplo: {{"action": "click", "x": 500, "y": 300}}"""
    
    response = pc_ctrl.ask_ollama(prompt)
    print(f"AI: {response[:300]}")
    
    action = pc_ctrl.parse_action(response)
    result = pc_ctrl.execute(action)
    print(f"[{result}]")

def listen_loop():
    """Loop de escucha"""
    global is_listening, audio_ctrl, pc_ctrl
    
    print("[MIC] Loop iniciado - Di 'salir' para detener")
    
    while is_listening:
        try:
            print("\n[ESCUCHANDO...] (di 'salir' para terminar)")
            # Timeout corto para poder salir rápido
            text, lang = audio_ctrl.listen_for_command(timeout=3)
            
            if not is_listening:
                break
                
            if text.strip() and lang:
                texto = text.lower()
                if "salir" in texto or "quit" in texto or "exit" in texto or "chao" in texto:
                    print("[MIC] Comando salir detectado")
                    break
                # Procesar comando
                print(f">>> VOZ: '{text}'")
                process_command(text)
                    
        except Exception as e:
            if is_listening:
                print(f"Error: {e}")
            time.sleep(0.5)
    
    is_listening = False
    print("[MIC] DETENIDO")

def mic_on():
    """Enciende el microfono"""
    global is_listening, listen_thread, audio_ctrl, pc_ctrl
    
    if is_listening:
        print("[MIC] Ya estaba ENCENDIDO")
        return
    
    print("[MIC] Encendiendo...")
    
    # Inicializar controladores
    audio_ctrl = AudioController("base")
    audio_ctrl.load_model()
    pc_ctrl = PCController()
    
    is_listening = True
    listen_thread = threading.Thread(target=listen_loop)
    listen_thread.start()
    print("[MIC] Listo! (Escribe 'salir' para detener)")
    
    print("[MIC] ENCENDIDO - Puedes dar ordenes de voz")

def mic_off():
    """Apaga el microfono"""
    global is_listening
    
    if not is_listening:
        print("[MIC] Ya estaba APAGADO")
        return
    
    print("[MIC] Apagando...")
    is_listening = False
    
    if listen_thread:
        listen_thread.join(timeout=2)
    
    print("[MIC] APAGADO")

def main():
    global is_listening
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  micon   - Enciende microfono para recibir ordenes de voz")
        print("  micoff  - Apaga microfono")
        print("")
        print("Estado actual:", "ENCENDIDO" if is_listening else "APAGADO")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "micon":
        mic_on()
        # Mantener proceso vivo
        try:
            while is_listening:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[Ctrl+C] Deteniendo...")
            mic_off()
    elif cmd == "micoff":
        mic_off()
    elif cmd == "status":
        print("[MIC] Estado:", "ENCENDIDO" if is_listening else "APAGADO")
    else:
        print(f"Comando desconocido: {cmd}")
        print("Usa: micon | micoff | status")

if __name__ == "__main__":
    main()