import { useEffect, useRef, useState, useCallback } from "react";
import { X, Volume2, VolumeX } from "lucide-react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";

const API_BASE = API;
const AVATAR_IMG = "/avatar-director.png";

// Color scheme
const C = {
  PRI: "#00d4ff",
  ACC: "#ff6b00",
  GREEN: "#00ff88",
  RED: "#ff3355",
  TEXT: "#8ffcff",
  BG: "#00060a",
};

interface Props {
  onClose: () => void;
}

type AvatarState = "idle" | "listening" | "thinking" | "speaking";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
}

interface PulseRing {
  radius: number;
  alpha: number;
  speed: number;
}

export function AvatarWindow({ onClose }: Props) {
  const [state, setState] = useState<AvatarState>("idle");
  const [transcript, setTranscript] = useState("");
  const [_response, setResponse] = useState("");

  // Draggable state — clamp to visible viewport
  const [pos, setPos] = useState(() => {
    const vw = document.documentElement.clientWidth || window.innerWidth;
    return { x: Math.max(0, vw - 300), y: 48 };
  });
  const draggingRef = useRef(false);
  const dragOffsetRef = useRef({ x: 0, y: 0 });
  const [muted, setMuted] = useState(false);
  const [_voices, setVoices] = useState<{id: string; name: string}[]>([]);
  const [_selectedVoice, setSelectedVoice] = useState("davefx-medium");

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const faceImgRef = useRef<HTMLImageElement | null>(null);
  const faceLoadedRef = useRef(false);
  const animRef = useRef<number>(0);
  const stateRef = useRef<AvatarState>("idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isHoldingRef = useRef(false);
  const timeRef = useRef(0);

  // HUD animation state refs
  const haloRef = useRef(48);
  const arcAnglesRef = useRef([0, 0, 0]);
  const scannerAngleRef = useRef(0);
  const particlesRef = useRef<Particle[]>([]);
  const pulseRingsRef = useRef<PulseRing[]>([]);
  const waveformRef = useRef<number[]>(new Array(36).fill(0));
  const faceScaleRef = useRef(1.0);

  stateRef.current = state;

  // Load available voices
  useEffect(() => {
    authFetch(`${API_BASE}/api/voice/voices`).then(r => r.json()).then(data => {
      const list = data?.voices || data || {};
      const arr = Object.entries(list).map(([id, v]: [string, any]) => ({ id, name: v.name || id }));
      if (arr.length) setVoices(arr);
    }).catch(() => {});
  }, []);

  void setVoices; void setSelectedVoice; // keep for future voice selector

  // Load face image
  useEffect(() => {
    const img = new Image();
    img.src = AVATAR_IMG;
    img.onload = () => {
      faceImgRef.current = img;
      faceLoadedRef.current = true;
    };
    img.onerror = () => {
      faceLoadedRef.current = false;
    };
  }, []);

  // Canvas HUD render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const W = 480;
    const H = 480;
    canvas.width = W;
    canvas.height = H;
    const cx = W / 2;
    const cy = H / 2;
    const faceR = 80;

    function draw() {
      const s = stateRef.current;
      const t = timeRef.current++;
      ctx.clearRect(0, 0, W, H);

      // --- Halo glow ---
      const haloTarget = s === "speaking" ? 170 : s === "listening" ? 120 : s === "thinking" ? 100 : 55;
      haloRef.current += (haloTarget - haloRef.current) * 0.06;
      for (let i = 10; i > 0; i--) {
        const r = faceR + i * 8;
        const a = (haloRef.current / 255) * (i / 10) * 0.4;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = hexAlpha(C.PRI, a);
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // --- Pulse rings ---
      const spawnRate = s === "speaking" ? 0.07 : s === "listening" ? 0.04 : 0.02;
      if (Math.random() < spawnRate) {
        pulseRingsRef.current.push({ radius: faceR + 10, alpha: 0.6, speed: 0.8 + Math.random() * 0.5 });
      }
      pulseRingsRef.current = pulseRingsRef.current.filter((p) => {
        p.radius += p.speed;
        p.alpha -= 0.008;
        if (p.alpha <= 0) return false;
        ctx.beginPath();
        ctx.arc(cx, cy, p.radius, 0, Math.PI * 2);
        ctx.strokeStyle = hexAlpha(C.PRI, p.alpha);
        ctx.lineWidth = 1;
        ctx.stroke();
        return true;
      });

      // --- Spinning arc rings ---
      const speeds = [0.012, -0.018, 0.009];
      const radii = [faceR * 2.4, faceR * 2.0, faceR * 1.6];
      const arcLens = [0.7, 0.5, 0.9];
      for (let i = 0; i < 3; i++) {
        arcAnglesRef.current[i] += speeds[i] * (s === "speaking" ? 2.5 : s === "thinking" ? 1.5 : 1);
        const a = arcAnglesRef.current[i];
        ctx.beginPath();
        ctx.arc(cx, cy, radii[i], a, a + arcLens[i]);
        ctx.strokeStyle = hexAlpha(C.PRI, 0.5);
        ctx.lineWidth = 1.5;
        ctx.stroke();
        // opposite side
        ctx.beginPath();
        ctx.arc(cx, cy, radii[i], a + Math.PI, a + Math.PI + arcLens[i] * 0.6);
        ctx.strokeStyle = hexAlpha(C.ACC, 0.3);
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // --- Tick marks ---
      for (let deg = 0; deg < 360; deg += 10) {
        const rad = (deg * Math.PI) / 180;
        const outer = faceR * 2.6;
        const inner = deg % 30 === 0 ? outer - 10 : outer - 5;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(rad) * inner, cy + Math.sin(rad) * inner);
        ctx.lineTo(cx + Math.cos(rad) * outer, cy + Math.sin(rad) * outer);
        ctx.strokeStyle = hexAlpha(C.PRI, deg % 30 === 0 ? 0.6 : 0.25);
        ctx.lineWidth = deg % 30 === 0 ? 1.5 : 0.8;
        ctx.stroke();
      }

      // --- Scanner arc ---
      scannerAngleRef.current += s === "idle" ? 0.015 : 0.04;
      const sa = scannerAngleRef.current;
      ctx.beginPath();
      ctx.arc(cx, cy, faceR + 2, sa, sa + 0.8);
      ctx.strokeStyle = hexAlpha(s === "listening" ? C.RED : C.GREEN, 0.7);
      ctx.lineWidth = 3;
      ctx.stroke();

      // --- Crosshair ---
      const gap = faceR * 0.3;
      const len = faceR * 1.2;
      ctx.strokeStyle = hexAlpha(C.PRI, 0.2);
      ctx.lineWidth = 0.8;
      // horizontal
      ctx.beginPath();
      ctx.moveTo(cx - len, cy);
      ctx.lineTo(cx - gap, cy);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx + gap, cy);
      ctx.lineTo(cx + len, cy);
      ctx.stroke();
      // vertical
      ctx.beginPath();
      ctx.moveTo(cx, cy - len);
      ctx.lineTo(cx, cy - gap);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx, cy + gap);
      ctx.lineTo(cx, cy + len);
      ctx.stroke();

      // --- Corner brackets ---
      const bSize = 18;
      const bOff = faceR * 2.5;
      ctx.strokeStyle = hexAlpha(C.PRI, 0.5);
      ctx.lineWidth = 1.5;
      const corners = [
        [cx - bOff, cy - bOff, 1, 1],
        [cx + bOff, cy - bOff, -1, 1],
        [cx - bOff, cy + bOff, 1, -1],
        [cx + bOff, cy + bOff, -1, -1],
      ];
      for (const [x, y, dx, dy] of corners) {
        ctx.beginPath();
        ctx.moveTo(x + dx * bSize, y);
        ctx.lineTo(x, y);
        ctx.lineTo(x, y + dy * bSize);
        ctx.stroke();
      }

      // --- Face image (circular clip) ---
      const scaleTarget = s === "speaking" ? 1.08 + Math.sin(t * 0.15) * 0.03 : 1.0;
      faceScaleRef.current += (scaleTarget - faceScaleRef.current) * 0.1;
      const sc = faceScaleRef.current;
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
      ctx.clip();
      if (faceLoadedRef.current && faceImgRef.current) {
        const sz = faceR * 2 * sc;
        ctx.drawImage(faceImgRef.current, cx - sz / 2, cy - sz / 2, sz, sz);
      } else {
        // Fallback gradient
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, faceR);
        grad.addColorStop(0, C.PRI);
        grad.addColorStop(1, "#003040");
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.fillStyle = "#fff";
        ctx.font = "bold 48px monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("N", cx, cy);
      }
      ctx.restore();

      // Face border
      ctx.beginPath();
      ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
      ctx.strokeStyle = s === "listening" ? C.RED : s === "thinking" ? C.ACC : s === "speaking" ? C.GREEN : C.PRI;
      ctx.lineWidth = 2;
      ctx.stroke();

      // --- Particles (speaking) ---
      if (s === "speaking" && Math.random() < 0.3) {
        const angle = Math.random() * Math.PI * 2;
        particlesRef.current.push({
          x: cx + Math.cos(angle) * faceR,
          y: cy + Math.sin(angle) * faceR,
          vx: Math.cos(angle) * (1 + Math.random()),
          vy: Math.sin(angle) * (1 + Math.random()),
          life: 1,
          maxLife: 40 + Math.random() * 30,
          size: 1 + Math.random() * 2,
        });
      }
      particlesRef.current = particlesRef.current.filter((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.life += 1;
        const a = 1 - p.life / p.maxLife;
        if (a <= 0) return false;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * a, 0, Math.PI * 2);
        ctx.fillStyle = hexAlpha(C.PRI, a * 0.7);
        ctx.fill();
        return true;
      });

      // --- Waveform bars ---
      const barCount = 36;
      const barW = 4;
      const barGap = 2;
      const waveX = cx - ((barCount * (barW + barGap)) / 2);
      const waveY = cy + faceR + 60;
      for (let i = 0; i < barCount; i++) {
        let target: number;
        if (s === "speaking") {
          target = 5 + Math.random() * 30;
        } else if (s === "listening") {
          target = 5 + Math.random() * 15;
        } else {
          target = 2 + Math.sin(t * 0.05 + i * 0.3) * 4;
        }
        waveformRef.current[i] += (target - waveformRef.current[i]) * 0.3;
        const h = waveformRef.current[i];
        ctx.fillStyle = hexAlpha(
          s === "listening" ? C.RED : s === "speaking" ? C.GREEN : C.PRI,
          s === "idle" ? 0.3 : 0.7
        );
        ctx.fillRect(waveX + i * (barW + barGap), waveY - h, barW, h);
      }

      // --- Status label ---
      const labels: Record<AvatarState, [string, string]> = {
        idle: ["⊘ IDLE", C.PRI],
        listening: ["● LISTENING", C.RED],
        thinking: ["◈ THINKING", C.ACC],
        speaking: ["● SPEAKING", C.GREEN],
      };
      const [label, color] = labels[s];
      const blink = s === "idle" || t % 40 < 30;
      if (blink) {
        ctx.fillStyle = color;
        ctx.font = "bold 11px monospace";
        ctx.textAlign = "center";
        ctx.fillText(label, cx, cy - faceR - 30);
      }

      animRef.current = requestAnimationFrame(draw);
    }

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, []);

  // --- Speak helper: server TTS → fallback browser speechSynthesis ---
  const speakReply = useCallback(async (text: string) => {
    setState("speaking");
    // Try server TTS first (Piper/Edge — higher quality)
    try {
      const ttsRes = await authFetch(`${API_BASE}/api/voice/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "audio/*" },
        body: JSON.stringify({ text }),
      });
      if (ttsRes.ok && (ttsRes.headers.get("content-type") || "").includes("audio")) {
        const audioBlob = await ttsRes.blob();
        if (audioBlob.size > 0) {
          const url = URL.createObjectURL(audioBlob);
          const audio = new Audio(url);
          audioRef.current = audio;
          return new Promise<void>((resolve) => {
            audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
            audio.onerror = () => { URL.revokeObjectURL(url); resolve(); };
            audio.play().catch(() => resolve());
          });
        }
      }
    } catch {}

    // Fallback: browser native speechSynthesis (zero deps, works offline)
    if ("speechSynthesis" in window) {
      return new Promise<void>((resolve) => {
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = "es-MX";
        utter.rate = 1.05;
        // Pick best Spanish voice available
        const voices = speechSynthesis.getVoices();
        const esVoice = voices.find(v => v.lang.startsWith("es") && v.name.includes("Microsoft"))
          || voices.find(v => v.lang.startsWith("es"));
        if (esVoice) utter.voice = esVoice;
        utter.onend = () => resolve();
        utter.onerror = () => resolve();
        speechSynthesis.speak(utter);
      });
    }
  }, []);

  // --- Process recognized text through Director ---
  const processText = useCallback(async (text: string) => {
    setTranscript(text);
    setState("thinking");
    try {
      const chatRes = await authFetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, gem: "director", project: "default", voice: true }),
      });
      const chatData = await chatRes.json();
      const reply = chatData.reply || chatData.content || "";
      setResponse(reply);

      if (!muted && reply) {
        await speakReply(reply);
      }
    } catch (err) {
      console.error("Avatar error:", err);
      setResponse("Error de comunicación con el Director.");
    }
    setState("idle");
  }, [muted, speakReply]);

  // --- STT: Web Speech API (instant) → fallback MediaRecorder + Whisper ---
  const webSpeechRef = useRef<any>(null);
  const sttModeRef = useRef<"web" | "whisper">("web");
  const accumulatedTextRef = useRef("");

  // Detect if Web Speech API is available
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    sttModeRef.current = SpeechRecognition ? "web" : "whisper";
  }, []);

  const startListening = useCallback(async () => {
    if (isHoldingRef.current) return;
    isHoldingRef.current = true;
    setState("listening");
    setTranscript("");
    accumulatedTextRef.current = "";

    if (sttModeRef.current === "web") {
      // --- Web Speech API: instant transcription, no upload ---
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.lang = "es-MX";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event: any) => {
        let interim = "";
        let final = "";
        for (let i = 0; i < event.results.length; i++) {
          const r = event.results[i];
          if (r.isFinal) final += r[0].transcript + " ";
          else interim += r[0].transcript;
        }
        accumulatedTextRef.current = final.trim();
        setTranscript((final + interim).trim() || "...");
      };

      recognition.onerror = (e: any) => {
        console.warn("SpeechRecognition error:", e.error);
        if (e.error === "not-allowed") sttModeRef.current = "whisper";
      };

      webSpeechRef.current = recognition;
      recognition.start();
    } else {
      // --- Fallback: record audio → server Whisper ---
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        mediaRecorderRef.current = recorder;
        audioChunksRef.current = [];
        recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
        recorder.start();
      } catch (err) {
        console.error("Mic error:", err);
        setState("idle");
        isHoldingRef.current = false;
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    if (!isHoldingRef.current) return;
    isHoldingRef.current = false;

    if (sttModeRef.current === "web" && webSpeechRef.current) {
      // Web Speech API — instant, text already accumulated
      webSpeechRef.current.stop();
      webSpeechRef.current = null;
      const text = accumulatedTextRef.current.trim();
      if (text) {
        processText(text);
      } else {
        setState("idle");
      }
    } else if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      // Whisper fallback — upload recorded audio
      const recorder = mediaRecorderRef.current;
      recorder.onstop = async () => {
        recorder.stream?.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (blob.size === 0) { setState("idle"); return; }

        setState("thinking");
        const form = new FormData();
        form.append("audio", blob, "recording.webm");
        form.append("language", "es");
        try {
          const res = await authFetch(`${API_BASE}/api/voice/transcribe`, { method: "POST", body: form });
          const data = await res.json();
          const text = data.text?.trim();
          if (!text) { setState("idle"); return; }
          processText(text);
        } catch {
          setResponse("Error de transcripción.");
          setState("idle");
        }
      };
      recorder.stop();
    }
  }, [processText]);

  // Keyboard: hold space (only when not typing in input/textarea)
  useEffect(() => {
    const isTyping = () => {
      const tag = document.activeElement?.tagName;
      return tag === "INPUT" || tag === "TEXTAREA" || (document.activeElement as HTMLElement)?.isContentEditable;
    };
    const down = (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat && !isTyping() && stateRef.current !== "thinking" && stateRef.current !== "speaking") {
        e.preventDefault();
        startListening();
      }
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === "Space" && !isTyping()) {
        e.preventDefault();
        stopListening();
      }
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => { window.removeEventListener("keydown", down); window.removeEventListener("keyup", up); };
  }, [startListening, stopListening]);

  // Drag handlers
  const onDragStart = useCallback((e: React.MouseEvent) => {
    draggingRef.current = true;
    dragOffsetRef.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
    const onMove = (ev: MouseEvent) => {
      if (!draggingRef.current) return;
      const vw = document.documentElement.clientWidth;
      const vh = document.documentElement.clientHeight;
      const nx = Math.max(0, Math.min(vw - 280, ev.clientX - dragOffsetRef.current.x));
      const ny = Math.max(0, Math.min(vh - 100, ev.clientY - dragOffsetRef.current.y));
      setPos({ x: nx, y: ny });
    };
    const onUp = () => {
      draggingRef.current = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [pos]);

  // Cleanup
  useEffect(() => {
    return () => { cancelAnimationFrame(animRef.current); audioRef.current?.pause(); };
  }, []);

  const stateColors: Record<AvatarState, string> = {
    idle: C.PRI,
    listening: C.RED,
    thinking: C.ACC,
    speaking: C.GREEN,
  };

  const stateLabels: Record<AvatarState, string> = {
    idle: "Mantén Espacio para hablar",
    listening: "Escuchando...",
    thinking: "Procesando...",
    speaking: "Hablando...",
  };

  return (
    <div
      className="fixed z-50 animate-nexus-in pointer-events-auto"
      style={{ left: pos.x, top: pos.y, width: 280 }}
    >
      <div
        className="relative w-full overflow-hidden rounded-2xl border shadow-2xl"
        style={{
          backgroundColor: C.BG,
          borderColor: hexAlpha(stateColors[state], 0.3),
          boxShadow: `0 0 80px ${stateColors[state]}25, inset 0 0 60px ${C.BG}`,
        }}
      >
        {/* Draggable Header */}
        <div
          className="flex items-center justify-between px-3 py-2 cursor-grab active:cursor-grabbing select-none"
          style={{ borderBottom: `1px solid ${hexAlpha(C.PRI, 0.15)}` }}
          onMouseDown={onDragStart}
        >
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: stateColors[state] }} />
            <span className="text-[10px] font-bold tracking-wider" style={{ color: C.TEXT, fontFamily: "monospace" }}>
              DIRECTOR
            </span>
          </div>
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setMuted(!muted)}
              className="p-1 rounded-md transition-colors"
              style={{ color: muted ? C.RED : C.PRI }}
            >
              {muted ? <VolumeX size={12} /> : <Volume2 size={12} />}
            </button>
            <button onClick={onClose} className="p-1 rounded-md transition-colors" style={{ color: C.PRI }}>
              <X size={12} />
            </button>
          </div>
        </div>

        {/* HUD Canvas */}
        <div className="flex justify-center py-2">
          <canvas ref={canvasRef} width={480} height={480} className="w-[220px] h-[220px] mx-auto" />
        </div>

        {/* State label */}
        <div className="text-center pb-1">
          <span className="text-xs font-medium tracking-widest" style={{ color: stateColors[state], fontFamily: "monospace" }}>
            {stateLabels[state]}
          </span>
        </div>

        {/* Live transcript (only while listening/thinking — ephemeral) */}
        {transcript && (state === "listening" || state === "thinking") && (
          <div className="px-3 pb-1">
            <div className="text-[10px] rounded px-2 py-1 truncate" style={{ backgroundColor: `${C.PRI}10`, color: C.TEXT }}>
              {transcript}
            </div>
          </div>
        )}

        {/* Mic button */}
        <div className="flex justify-center pb-3">
          <button
            onMouseDown={startListening}
            onMouseUp={stopListening}
            onMouseLeave={stopListening}
            onTouchStart={startListening}
            onTouchEnd={stopListening}
            disabled={state === "thinking" || state === "speaking"}
            className="p-3 rounded-full transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              backgroundColor: state === "listening" ? `${C.RED}30` : `${C.PRI}15`,
              color: state === "listening" ? C.RED : C.PRI,
              boxShadow: state === "listening" ? `0 0 20px ${C.RED}40` : "none",
              transform: state === "listening" ? "scale(1.1)" : "scale(1)",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

function hexAlpha(hex: string, alpha: number): string {
  const a = Math.round(Math.max(0, Math.min(1, alpha)) * 255).toString(16).padStart(2, "0");
  return hex + a;
}
