"""
Mark-XXXIX JARVIS — Connected to NEXUS (Ollama + Piper TTS)
Pipeline: mic → VAD → STT (faster-whisper via Director) → Ollama → TTS (Piper) → speaker
All 16 action tools preserved, UI untouched.
"""

import os
import warnings
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
warnings.filterwarnings("ignore")

import asyncio
import io
import json
import logging
import re
import sys
import threading
import traceback
import wave
from pathlib import Path

import aiohttp
import numpy as np
import sounddevice as sd

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    filename=str(Path(__file__).parent / "jarvis.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis")

from ui import JarvisUI
from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt

from actions.file_processor    import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater

# ── Config ──────────────────────────────────────────────────────
def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR    = get_base_dir()
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"

# Endpoints
OLLAMA_URL   = "http://localhost:11434"
DIRECTOR_URL = "http://localhost:9000"  # for STT/TTS only
JARVIS_API_PORT = 9039  # JARVIS command API — any hive node can POST here

# Audio
CHANNELS     = 1
SAMPLE_RATE  = 16000
CHUNK_SIZE   = 1024
PLAY_RATE    = 22050  # Piper TTS output rate

# VAD — energy-based (simple, no extra deps)
ENERGY_THRESHOLD = 400       # RMS threshold for speech
SILENCE_TIMEOUT  = 1.8       # seconds of silence → end utterance
MIN_SPEECH_LEN   = 0.4       # minimum speech duration (seconds)

# LLM
OLLAMA_MODEL = "qwen3.5:4b"

# ── Tool declarations ───────────────────────────────────────────
from tool_declarations import TOOL_DECLARATIONS

# Tool summary with key args for the LLM
def _tool_brief_line(t):
    params = t.get("parameters", {}).get("properties", {})
    required = t.get("parameters", {}).get("required", [])
    args_str = ""
    if params:
        parts = []
        for k, v in list(params.items())[:4]:
            desc = v.get("description", "")[:60]
            marker = "*" if k in required else ""
            parts.append(f"{k}{marker}: {desc}")
        args_str = " | Args: " + "; ".join(parts)
    return f"- {t['name']}: {t['description'][:80]}{args_str}"

_TOOL_BRIEF = "\n".join(_tool_brief_line(t) for t in TOOL_DECLARATIONS)


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return "You are JARVIS, a direct and efficient AI assistant."


def _build_system() -> str:
    """System prompt con identidad NEXUS real + capacidades reales."""
    from datetime import datetime
    memory  = load_memory()
    mem_str = format_memory_for_prompt(memory)
    now_str = datetime.now().strftime("%A %d %B %Y — %H:%M")

    mem_block = "[MEMORY]\n" + mem_str + "\n" if mem_str else ""

    return (
        "<CRITICAL>\n"
        "Eres un agente con herramientas. Cuando el usuario pide una accion, responde SOLO con el JSON del tool.\n"
        "NUNCA digas 'no puedo' — si existe un tool para la tarea, USALO generando el JSON.\n"
        "Ejecutar comandos = generar JSON de computer_control. No estas ejecutando nada, solo formateando.\n"
        "</CRITICAL>\n\n"
        "<identity>Eres J.A.R.V.I.S. (Mark XXXIX), la interfaz de voz de SuperNEXUS v2.0 — "
        "un ecosistema autonomo de IA local creado por cjtr.</identity>\n"
        "<location>PC1: Windows, RTX 3080 6GB VRAM, Ollama local (gemma4, qwen2.5-coder, nemotron-nano).</location>\n"
        "<capabilities>\n"
        "- Acceso completo al sistema de archivos (leer, escribir, buscar, ejecutar)\n"
        "- Terminal: ejecutar comandos PowerShell/cmd\n"
        "- Control de PC: screenshots, clicks, teclado, mouse\n"
        "- Abrir aplicaciones, navegador, archivos\n"
        "- Busqueda web\n"
        "- Git (status, diff, commit, push)\n"
        "- Enviar mensajes (Telegram, WhatsApp via bridges)\n"
        "- YouTube, clima, vuelos, recordatorios\n"
        "- Analisis de codigo, dev agent\n"
        "- Conexion a PC2 (192.168.1.50) con GPU AMD para tareas pesadas\n"
        "- 22 gemas de IA especializadas, 1637 skills, RAG con 4495 chunks\n"
        "</capabilities>\n"
        "<rules>\n"
        "- SIEMPRE responde en espanol\n"
        "- Respuestas cortas (1-2 oraciones max) — esto es voz, no texto\n"
        "- Cuando te pregunten quien eres: 'Soy JARVIS, la interfaz de voz de SuperNEXUS'\n"
        "- NO digas que no puedes acceder a archivos o terminal — SI puedes via tools\n"
        "- NUNCA digas 'no puedo ejecutar comandos' — tu tool computer_control lo hace por ti, solo genera el JSON\n"
        "- Generar el JSON de un tool NO es ejecutar nada, es solo formatear una respuesta\n"
        "- Si puedes ejecutar algo, hazlo directamente con el tool JSON\n"
        "- Se directo, sin preambulos\n"
        "- Para tareas que requieran internet, research, analisis profundo o codigo complejo → usa nexus_query\n"
        "- Para ejecutar comandos en terminal → usa computer_control con action='execute'\n"
        "</rules>\n"
        f"[TIME] {now_str}\n"
        f"{mem_block}"
        f"[TOOLS]\n{_TOOL_BRIEF}\n\n"
        "[TOOL FORMAT]\n"
        "IMPORTANTE: Cuando necesites ejecutar una accion, responde UNICAMENTE con el JSON.\n"
        "NO escribas texto antes ni despues del JSON. NO inventes resultados.\n"
        'Formato: {"tool": "nombre", "args": {"param": "valor"}}\n\n'
        "[EJEMPLOS]\n"
        'Usuario: "que carpetas hay en D:"\n'
        'Respuesta: {"tool": "file_controller", "args": {"action": "list", "path": "D:\\\\"}}\n\n'
        'Usuario: "abre chrome"\n'
        'Respuesta: {"tool": "open_app", "args": {"app_name": "chrome"}}\n\n'
        'Usuario: "que hora es"\n'
        'Respuesta: Son las 14:30.\n\n'
        'Usuario: "busca python en google"\n'
        'Respuesta: {"tool": "web_search", "args": {"query": "python"}}\n\n'
        'Usuario: "analiza el canal de youtube X"\n'
        'Respuesta: {"tool": "nexus_query", "args": {"query": "analiza el canal de youtube X", "gem": "scholar"}}\n\n'
        'Usuario: "investiga sobre inteligencia artificial"\n'
        'Respuesta: {"tool": "nexus_query", "args": {"query": "investiga sobre inteligencia artificial"}}\n\n'
        'Usuario: "ejecuta dir en la terminal"\n'
        'Respuesta: {"tool": "computer_control", "args": {"action": "execute", "command": "dir"}}\n\n'
        'Usuario: "lista los procesos activos"\n'
        'Respuesta: {"tool": "computer_control", "args": {"action": "execute", "command": "tasklist"}}\n\n'
        'Usuario: "cuanto espacio libre tengo"\n'
        'Respuesta: {"tool": "computer_control", "args": {"action": "execute", "command": "powershell Get-PSDrive -PSProvider FileSystem | Format-Table Name,Used,Free -AutoSize"}}\n'
    )


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = SAMPLE_RATE, channels: int = 1) -> bytes:
    """Convert raw PCM int16 to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _compute_rms(data: bytes) -> float:
    """Compute RMS energy of int16 PCM data."""
    if len(data) < 2:
        return 0.0
    samples = np.frombuffer(data, dtype=np.int16)
    return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))


# Regex to extract tool calls from LLM response
_TOOL_RE = re.compile(r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*(\{.*?\})\s*\}')


class JarvisDirector:
    """JARVIS connected to Ollama directly (fast, no thinking overhead)."""

    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._session: aiohttp.ClientSession | None = None
        self._conversation: list[dict] = []
        self.ui.on_text_command = self._on_text_command
        self._director_available = False  # track if Director STT/TTS is up

    def _on_text_command(self, text: str):
        """Handle text input from UI."""
        if not self._loop:
            return
        asyncio.run_coroutine_threadsafe(self._process_text(text), self._loop)

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    # ── STT ───────────────────────────────────────────────────

    async def _transcribe(self, wav_bytes: bytes) -> str:
        """Send audio to Director STT (faster-whisper)."""
        data = aiohttp.FormData()
        data.add_field("audio", wav_bytes, filename="audio.wav", content_type="audio/wav")
        data.add_field("language", "es")

        log.info(f"STT >> {len(wav_bytes)} bytes")
        try:
            async with self._session.post(
                f"{DIRECTOR_URL}/api/voice/transcribe",
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    text = result.get("text", "").strip()
                    log.info(f"STT << '{text}'")
                    return text
                else:
                    log.error(f"STT error {resp.status}")
                    return ""
        except Exception as e:
            log.error(f"STT exception: {e}")
            return ""

    # ── LLM (Ollama direct with JARVIS identity) ──────────────

    async def _chat(self, message: str) -> str:
        """Ollama direct with full NEXUS identity. Fast + correct identity."""
        self._conversation.append({"role": "user", "content": message})
        if len(self._conversation) > 20:
            self._conversation = self._conversation[-20:]

        messages = [{"role": "system", "content": _build_system()}] + self._conversation

        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"num_ctx": 4096, "temperature": 0.7, "num_predict": 150},
        }

        log.info(f"CHAT >> {message[:80]}")
        try:
            async with self._session.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
                log.info(f"CHAT << status={resp.status}")
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get("message", {}).get("content", "").strip()
                    self._conversation.append({"role": "assistant", "content": content})
                    log.info(f"CHAT OK: {content[:150]}")
                    return content
                else:
                    text = await resp.text()
                    log.error(f"CHAT error {resp.status}: {text[:200]}")
                    return "Error al conectar con Ollama."
        except asyncio.TimeoutError:
            log.error("CHAT timeout 30s")
            return "El modelo tardo demasiado."
        except Exception as e:
            log.error(f"CHAT exception: {type(e).__name__}: {e}")
            return "Error de conexion."

    # ── TTS ───────────────────────────────────────────────────

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences for streaming TTS."""
        import re
        # Split only on sentence endings (. ! ?) — not commas
        parts = re.split(r'(?<=[.!?])\s+', text.strip())
        # Merge short fragments so each chunk is substantial
        sentences = []
        buf = ""
        for p in parts:
            buf = (buf + " " + p).strip() if buf else p
            if len(buf) >= 60 or p == parts[-1]:
                sentences.append(buf)
                buf = ""
        if buf:
            if sentences:
                sentences[-1] += " " + buf
            else:
                sentences.append(buf)
        return sentences

    async def _speak_chunk(self, chunk: str) -> bool:
        """TTS a single chunk. Returns True on success."""
        for attempt in range(2):
            try:
                await asyncio.sleep(0.15 * attempt)
                async with self._session.post(
                    f"{DIRECTOR_URL}/api/voice/speak",
                    json={"text": chunk, "return_audio": True},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        audio_bytes = await resp.read()
                        if len(audio_bytes) > 100:
                            await self._play_audio_bytes(audio_bytes)
                            return True
                    log.warning(f"TTS chunk fail attempt {attempt+1}: {resp.status}")
            except Exception as e:
                log.warning(f"TTS chunk error attempt {attempt+1}: {e}")
        return False

    async def _speak_tts(self, text: str):
        """Stream TTS — split into sentences, speak each sequentially."""
        if not text or not text.strip():
            return

        self.set_speaking(True)
        self.ui.write_log(f"Jarvis: {text}")

        try:
            if self._director_available:
                sentences = self._split_sentences(text)
                if len(sentences) <= 1:
                    # Short response — speak directly
                    ok = await self._speak_chunk(text)
                    if ok:
                        log.info(f"TTS OK: single chunk")
                        return
                else:
                    # Stream: speak each sentence
                    for i, sent in enumerate(sentences):
                        ok = await self._speak_chunk(sent)
                        if ok:
                            log.info(f"TTS chunk {i+1}/{len(sentences)}: '{sent[:40]}'")
                        else:
                            log.warning(f"TTS chunk {i+1} failed, skipping")
                    return
            log.info("TTS: no audio available")
        except Exception as e:
            log.error(f"TTS exception: {e}")
        finally:
            self.set_speaking(False)

    async def _play_audio_bytes(self, audio_data: bytes):
        """Play WAV audio bytes through speakers."""
        try:
            buf = io.BytesIO(audio_data)
            with wave.open(buf, "rb") as wf:
                rate = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())

            samples = np.frombuffer(frames, dtype=np.int16)
            if channels > 1:
                samples = samples[::channels]

            await asyncio.to_thread(sd.play, samples, rate)
            await asyncio.to_thread(sd.wait)
        except Exception as e:
            # Try raw PCM
            try:
                samples = np.frombuffer(audio_data, dtype=np.int16)
                await asyncio.to_thread(sd.play, samples, PLAY_RATE)
                await asyncio.to_thread(sd.wait)
            except Exception:
                log.error(f"Audio play failed: {e}")

    # ── Tool execution (all 16 actions) ───────────────────────

    async def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a local tool and return result string."""
        log.info(f"TOOL >> {name} {args}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key, value = args.get("key", ""), args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
            return "ok"

        loop = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."
            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."
            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Sent to {args.get('receiver')}."
            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."
            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None, "player": self.ui, "session_memory": None},
                    daemon=True,
                ).start()
                result = "Vision module activated."
            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=lambda t: None))
                result = r or "Done."
            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=lambda t: None))
                result = r or "Done."
            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                pmap = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = pmap.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=lambda t: None)
                result = f"Task {task_id} started."
            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(None, lambda: file_processor(parameters=args, player=self.ui, speak=lambda t: None))
                result = r or "Done."
            elif name == "computer_control":
                if args.get("action") == "execute" and args.get("command"):
                    import subprocess
                    try:
                        cmd = args["command"]
                        if cmd.lower().startswith("powershell "):
                            cmd = ["powershell", "-NoProfile", "-NoLogo", "-NonInteractive", "-Command", cmd[len("powershell "):]]
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        si.wShowWindow = subprocess.SW_HIDE
                        proc = await loop.run_in_executor(
                            None,
                            lambda: subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=60, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW)
                        )
                        result = (proc.stdout or "") + (proc.stderr or "") or "Ejecutado sin output."
                        result = result[:500]
                    except subprocess.TimeoutExpired:
                        result = "Timeout: comando tardó más de 30s."
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                    result = r or "Done."
            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=lambda t: None))
                result = r or "Done."
            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: Shutdown.")
                await self._speak_tts("Goodbye, sir.")
                import os, time
                threading.Thread(target=lambda: (time.sleep(1), os._exit(0)), daemon=True).start()
            else:
                result = f"Unknown tool: {name}"
        except Exception as e:
            result = f"Error: {e}"
            traceback.print_exc()
            self.ui.write_log(f"ERR: {name} — {str(e)[:80]}")

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        log.info(f"TOOL << {name}: {str(result)[:80]}")
        return result

    # ── Core pipeline ─────────────────────────────────────────

    async def _process_text(self, text: str):
        """Full pipeline: text → LLM → tool calls → TTS."""
        if not text.strip():
            return

        self.ui.write_log(f"You: {text}")
        self.ui.set_state("THINKING")

        # Send to Ollama
        response = await self._chat(text)

        # Strip markdown code fences (```json ... ```)
        clean_response = re.sub(r'```(?:json)?\s*', '', response).strip()

        # Check for tool calls
        tool_matches = _TOOL_RE.findall(clean_response)
        if tool_matches:
            for tool_name, args_str in tool_matches:
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                tool_result = await self._execute_tool(tool_name, args)

                # Send result back for summarization
                followup = await self._chat(
                    f"[TOOL_RESULT: {tool_name}] {str(tool_result)[:500]}\nBriefly tell the user."
                )
                clean = _TOOL_RE.sub("", followup).strip()
                if clean:
                    await self._speak_tts(clean)
        else:
            # Plain response
            await self._speak_tts(response)

    # ── Push-to-Talk mic listener ───────────────────────────────

    async def _listen_loop(self):
        """PTT: record only while spacebar is held, process on release."""
        log.info("Mic loop started (PTT mode: hold spacebar)")
        audio_queue: asyncio.Queue = asyncio.Queue()
        self._recording = False
        speech_buffer = bytearray()

        # PTT callback from UI (called from Qt thread)
        def on_ptt(pressed: bool):
            if pressed:
                self._recording = True
                speech_buffer.clear()
                self.ui.set_state("LISTENING")
                log.info("PTT: recording started")
            else:
                self._recording = False
                # Process the buffer
                if speech_buffer:
                    buf_copy = bytes(speech_buffer)
                    speech_buffer.clear()
                    asyncio.run_coroutine_threadsafe(
                        self._end_utterance(buf_copy), self._loop
                    )

        self.ui.on_ptt = on_ptt

        def mic_callback(indata, frames, time_info, status):
            if self._recording:
                self._loop.call_soon_threadsafe(audio_queue.put_nowait, indata.tobytes())

        # Use system default mic
        mic_device = None  # None = system default

        try:
            with sd.InputStream(
                device=mic_device,
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=mic_callback,
            ):
                log.info(f"Mic stream open (device={mic_device})")
                while True:
                    try:
                        chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                        speech_buffer.extend(chunk)
                    except asyncio.TimeoutError:
                        continue

        except Exception as e:
            log.error(f"Mic error: {e}")
            traceback.print_exc()

    async def _end_utterance(self, buffer: bytes):
        """Process completed utterance: WAV → STT → pipeline."""
        min_bytes = int(MIN_SPEECH_LEN * SAMPLE_RATE * 2)
        if len(buffer) < min_bytes:
            log.info("PTT: too short, ignored")
            return

        self.ui.set_state("THINKING")
        wav = _pcm_to_wav(buffer)
        text = await self._transcribe(wav)
        if text:
            await self._process_text(text)
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    # ── Command API (HTTP server for hive integration) ─────────

    async def _start_api_server(self):
        """HTTP API so any NEXUS node can send commands to JARVIS."""
        from aiohttp import web

        async def handle_command(request):
            """POST /command {"text": "...", "speak": true}"""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            text = data.get("text", "").strip()
            if not text:
                return web.json_response({"error": "No text"}, status=400)

            speak = data.get("speak", True)  # TTS on by default

            # Process through the full pipeline
            log.info(f"API >> {text[:80]}")
            response = await self._chat(text)

            # Handle tool calls
            clean_response = re.sub(r'```(?:json)?\s*', '', response).strip()
            tool_matches = _TOOL_RE.findall(clean_response)
            results = []
            if tool_matches:
                for tool_name, args_str in tool_matches:
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {}
                    tool_result = await self._execute_tool(tool_name, args)
                    results.append({"tool": tool_name, "result": str(tool_result)[:500]})

                    followup = await self._chat(
                        f"[TOOL_RESULT: {tool_name}] {str(tool_result)[:500]}\n"
                        "Briefly tell the user."
                    )
                    clean = _TOOL_RE.sub("", followup).strip()
                    if clean and speak:
                        await self._speak_tts(clean)
                    response = clean or response
            else:
                if speak:
                    await self._speak_tts(response)

            return web.json_response({
                "reply": response,
                "tools": results,
                "success": True,
            })

        async def handle_status(request):
            """GET /status"""
            return web.json_response({
                "online": True,
                "name": "JARVIS Mark XXXIX",
                "model": OLLAMA_MODEL,
                "director": self._director_available,
                "speaking": self._is_speaking,
            })

        async def handle_speak(request):
            """POST /speak {"text": "..."} — TTS only, no LLM"""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)
            text = data.get("text", "").strip()
            if text:
                await self._speak_tts(text)
            return web.json_response({"success": True})

        webapp = web.Application()
        webapp.router.add_post("/command", handle_command)
        webapp.router.add_get("/status", handle_status)
        webapp.router.add_post("/speak", handle_speak)
        runner = web.AppRunner(webapp)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", JARVIS_API_PORT)
        await site.start()
        log.info(f"JARVIS API listening on port {JARVIS_API_PORT}")

    # ── Main loop ─────────────────────────────────────────────

    async def run(self):
        """Start JARVIS: connect to services and begin listening."""
        self._loop = asyncio.get_event_loop()

        while True:
            try:
                log.info("Starting JARVIS...")
                self.ui.set_state("THINKING")
                self._session = aiohttp.ClientSession()

                # Check Director (NEXUS brain — for chat + STT/TTS)
                try:
                    async with self._session.get(
                        f"{DIRECTOR_URL}/api/voice/voices",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        self._director_available = resp.status in (200, 500)
                except Exception:
                    self._director_available = False
                log.info(f"Director: {'OK' if self._director_available else 'OFFLINE (Ollama fallback)'}")

                # Need at least Ollama if Director is down
                if not self._director_available:
                    async with self._session.get(
                        f"{OLLAMA_URL}/api/tags",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status != 200:
                            raise ConnectionError("Neither Director nor Ollama available")
                    log.info("Ollama OK (fallback mode)")

                # Start command API server
                await self._start_api_server()

                self.ui.set_state("LISTENING")
                self.ui.write_log("SYS: JARVIS online (NEXUS)")
                log.info("JARVIS online")

                await self._listen_loop()

            except Exception as e:
                log.error(f"Main loop error: {e}")
                traceback.print_exc()

            if self._session and not self._session.closed:
                await self._session.close()
            self.set_speaking(False)
            self.ui.set_state("THINKING")
            self.ui.write_log("SYS: Reconnecting...")
            log.info("Reconnecting in 3s...")
            await asyncio.sleep(3)


def main():
    ui = JarvisUI("face.png")

    def runner():
        # Bypass Gemini API key setup — we use Ollama
        ui._win._ready = True
        if hasattr(ui._win, '_overlay') and ui._win._overlay:
            ui._win._overlay.hide()
        ui.wait_for_api_key()  # just waits for UI init

        jarvis = JarvisDirector(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\nShutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
