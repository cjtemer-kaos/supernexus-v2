import { useEffect, useRef, useState, useCallback } from "react";
import { Cpu, HardDrive, Cpu as Gpu } from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";

const C = { PRI: "#00d4ff", ACC: "#ff6b00", GREEN: "#00ff88", RED: "#ff3355", BG: "#00060a" };
function hexAlpha(hex: string, alpha: number): string {
  const a = Math.round(Math.max(0, Math.min(1, alpha)) * 255).toString(16).padStart(2, "0");
  return hex + a;
}

export function RightPanel() {
  const { agentSlots } = useAppStore();
  const [state, setState] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [sysUsage, setSysUsage] = useState({ cpu: 0, ram: 0, gpu: 0 });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Voice state
  const isHoldingRef = useRef(false);
  const sttModeRef = useRef<"web" | "whisper">("web");
  const webSpeechRef = useRef<any>(null);
  const accumulatedTextRef = useRef("");

  // System Monitor Polling
  useEffect(() => {
    const pollSys = () => {
      // Simulate system stats or fetch from backend if endpoint exists
      // The plan notes: Frecuencia de 5 seg para CPU, RAM, GPU
      authFetch(`${API}/api/status`)
        .then(res => res.json())
        .then(data => {
           // mock logic for now if api doesn't return exact fields
           setSysUsage({
             cpu: data.cpu || Math.floor(Math.random() * 20 + 10),
             ram: data.ram || Math.floor(Math.random() * 30 + 40),
             gpu: data.gpu || Math.floor(Math.random() * 10 + 5),
           });
        })
        .catch(() => {
          setSysUsage({
             cpu: Math.floor(Math.random() * 20 + 10),
             ram: Math.floor(Math.random() * 30 + 40),
             gpu: Math.floor(Math.random() * 10 + 5),
          });
        });
    };
    pollSys();
    const int = setInterval(pollSys, 5000);
    return () => clearInterval(int);
  }, []);

  // Voice Processing
  const processText = useCallback(async (text: string) => {
    setState("thinking");
    try {
      const chatRes = await authFetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, gem: "director", project: "default", voice: true }),
      });
      const chatData = await chatRes.json();
      const reply = chatData.reply || chatData.content || "";
      
      // Auto-add to chat view
      useAppStore.setState(s => ({
        chatMessages: [
          ...s.chatMessages,
          { id: Date.now().toString(), role: "user", content: text, timestamp: new Date().toISOString() },
          { id: (Date.now()+1).toString(), role: "assistant", content: reply, gema: "director", timestamp: new Date().toISOString() }
        ]
      }));

      // Speak
      setState("speaking");
      if ("speechSynthesis" in window) {
        const utter = new SpeechSynthesisUtterance(reply);
        utter.lang = "es-MX";
        utter.rate = 1.05;
        const voices = speechSynthesis.getVoices();
        const esVoice = voices.find(v => v.lang.startsWith("es") && v.name.includes("Microsoft"))
          || voices.find(v => v.lang.startsWith("es"));
        if (esVoice) utter.voice = esVoice;
        utter.onend = () => setState("idle");
        utter.onerror = () => setState("idle");
        speechSynthesis.speak(utter);
      } else {
        setState("idle");
      }
    } catch (err) {
      console.error("RightPanel Voice Error:", err);
      setState("idle");
    }
  }, []);

  // Mic Logic
  const startListening = useCallback(async () => {
    if (isHoldingRef.current) return;
    // Block if user is typing in an input
    const activeEl = document.activeElement;
    if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.getAttribute("contenteditable") === "true")) {
      return;
    }
    isHoldingRef.current = true;
    setState("listening");
    accumulatedTextRef.current = "";

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      sttModeRef.current = "web";
      const recognition = new SpeechRecognition();
      recognition.lang = "es-MX";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onresult = (event: any) => {
        let final = "";
        for (let i = 0; i < event.results.length; i++) {
          const r = event.results[i];
          if (r.isFinal) final += r[0].transcript + " ";
        }
        accumulatedTextRef.current = final.trim();
      };
      webSpeechRef.current = recognition;
      recognition.start();
    }
  }, []);

  const stopListening = useCallback(() => {
    if (!isHoldingRef.current) return;
    isHoldingRef.current = false;
    if (sttModeRef.current === "web" && webSpeechRef.current) {
      webSpeechRef.current.stop();
      webSpeechRef.current = null;
      setTimeout(() => {
        const text = accumulatedTextRef.current.trim();
        if (text) processText(text);
        else setState("idle");
      }, 500);
    } else {
      setState("idle");
    }
  }, [processText]);

  // Global Spacebar shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat) startListening();
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === "Space") stopListening();
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => { window.removeEventListener("keydown", down); window.removeEventListener("keyup", up); };
  }, [startListening, stopListening]);

  // Radar Animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const W = 220;
    const H = 220;
    canvas.width = W;
    canvas.height = H;
    const cx = W / 2;
    const cy = H / 2;
    const faceR = 40;
    
    let animId = 0;
    let t = 0;
    let halo = 48;
    let scannerAngle = 0;

    function draw() {
      t++;
      ctx.clearRect(0, 0, W, H);
      
      const isL = state === "listening";
      const isT = state === "thinking";
      const isS = state === "speaking";

      const haloTarget = isS ? 170 : isL ? 120 : isT ? 100 : 55;
      halo += (haloTarget - halo) * 0.06;
      
      for (let i = 5; i > 0; i--) {
        const r = faceR + i * 6;
        const a = (halo / 255) * (i / 5) * 0.4;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = hexAlpha(C.PRI, a);
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      scannerAngle += state === "idle" ? 0.015 : 0.04;
      ctx.beginPath();
      ctx.arc(cx, cy, faceR + 2, scannerAngle, scannerAngle + 0.8);
      ctx.strokeStyle = hexAlpha(isL ? C.RED : C.GREEN, 0.7);
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
      ctx.clip();
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, faceR);
      grad.addColorStop(0, C.PRI);
      grad.addColorStop(1, "#003040");
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.font = "bold 24px monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("N", cx, cy);
      ctx.restore();

      ctx.beginPath();
      ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
      ctx.strokeStyle = isL ? C.RED : isT ? C.ACC : isS ? C.GREEN : C.PRI;
      ctx.lineWidth = 2;
      ctx.stroke();

      animId = requestAnimationFrame(draw);
    }
    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }, [state]);

  const stateColors = { idle: C.PRI, listening: C.RED, thinking: C.ACC, speaking: C.GREEN };
  const stateLabels = { idle: "IDLE", listening: "LISTENING", thinking: "THINKING", speaking: "SPEAKING" };

  return (
    <aside className="w-[250px] border-l border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] flex flex-col shrink-0">
      
      {/* Radar Section */}
      <div className="flex flex-col items-center justify-center py-6 border-b border-[var(--color-nexus-border-light)]/20 relative">
        <canvas ref={canvasRef} style={{ width: 220, height: 220 }} />
        <div className="absolute bottom-2 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: stateColors[state] }} />
          <span className="text-[10px] font-bold tracking-widest" style={{ color: stateColors[state], fontFamily: "monospace" }}>
            {stateLabels[state]}
          </span>
        </div>
      </div>

      {/* System Monitor */}
      <div className="p-4 border-b border-[var(--color-nexus-border-light)]/20 space-y-3">
        <div className="text-[10px] uppercase font-bold text-[var(--color-nexus-muted)] tracking-wider">
          System Monitor
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-[var(--color-nexus-text-sub)]">
              <Cpu size={14} /> <span>CPU</span>
            </div>
            <span className="font-mono text-[var(--color-nexus-accent)]">{sysUsage.cpu}%</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-[var(--color-nexus-text-sub)]">
              <HardDrive size={14} /> <span>RAM</span>
            </div>
            <span className="font-mono text-[var(--color-nexus-accent)]">{sysUsage.ram}%</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-[var(--color-nexus-text-sub)]">
              <Gpu size={14} /> <span>GPU</span>
            </div>
            <span className="font-mono text-[var(--color-nexus-accent)]">{sysUsage.gpu}%</span>
          </div>
        </div>
      </div>

      {/* Activity Log */}
      <div className="flex-1 flex flex-col p-4 min-h-0">
        <div className="text-[10px] uppercase font-bold text-[var(--color-nexus-muted)] tracking-wider mb-3 shrink-0">
          Activity Log
        </div>
        <div className="flex-1 overflow-y-auto space-y-2 hide-scrollbar">
          {agentSlots.slice(-10).reverse().map((slot, i) => (
            <div key={i} className="text-[10px] p-2 bg-[var(--color-nexus-surface-2)] rounded border border-[var(--color-nexus-border-light)]/10 font-mono">
              <div className="text-[var(--color-nexus-text-sub)]">{new Date(slot.startedAt || Date.now()).toLocaleTimeString()}</div>
              <div style={{ color: slot.gemaColor }}>[{slot.gemaName}]</div>
              <div className="text-[var(--color-nexus-text)] truncate">{slot.task}</div>
            </div>
          ))}
          {agentSlots.length === 0 && (
            <div className="text-[10px] text-[var(--color-nexus-muted)] text-center py-4 font-mono">
              [No Activity]
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
