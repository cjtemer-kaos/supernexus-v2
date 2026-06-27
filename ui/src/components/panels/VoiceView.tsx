import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Mic, RefreshCw, Volume2, UserCircle, Bot, Play, Square } from "lucide-react";



export function VoiceView() {
  const [status, setStatus] = useState<any>(null);
  const [voices, setVoices] = useState<any[]>([]);
  const [personalities, setPersonalities] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [ttsText, setTtsText] = useState("");
  const [result, setResult] = useState<string | null>(null);

  // NEXUS Voice state
  const [jarvisOnline, setJarvisOnline] = useState(false);
  const [jarvisStarting, setJarvisStarting] = useState(false);

  const checkJarvis = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/jarvis/status`);
      const data = await res.json();
      setJarvisOnline(data.online || data.process_running);
    } catch { setJarvisOnline(false); }
  }, []);

  useEffect(() => { checkJarvis(); const iv = setInterval(checkJarvis, 5000); return () => clearInterval(iv); }, [checkJarvis]);

  const startJarvis = useCallback(async () => {
    setJarvisStarting(true);
    try {
      const res = await authFetch(`${API}/api/jarvis/start`, { method: "POST" });
      const data = await res.json();
      setResult(data.message);
      setTimeout(checkJarvis, 2000);
    } catch (e) { setResult(`Error: ${e}`); }
    setJarvisStarting(false);
  }, [checkJarvis]);

  const stopJarvis = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/jarvis/stop`, { method: "POST" });
      const data = await res.json();
      setResult(data.message);
      checkJarvis();
    } catch (e) { setResult(`Error: ${e}`); }
  }, [checkJarvis]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [st, v, p] = await Promise.all([
        authFetch(`${API}/api/voice/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/voice/voices`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/voice/personalities`).then(r => r.json()).catch(() => null),
      ]);
      setStatus(st);
      // Handle multiple response formats
      let voiceList: any[] = [];
      if (v?.voices) voiceList = Array.isArray(v.voices) ? v.voices : Object.values(v.voices);
      else if (v?.available_voices) voiceList = Array.isArray(v.available_voices) ? v.available_voices : Object.values(v.available_voices);
      else if (Array.isArray(v)) voiceList = v;
      else if (v && typeof v === "object") voiceList = Object.entries(v).map(([k, val]) => ({ id: k, ...((val as any)) }));
      // Also extract from status if available
      if (voiceList.length === 0 && st?.voice_config?.available_voices) {
        voiceList = Array.isArray(st.voice_config.available_voices) ? st.voice_config.available_voices : Object.values(st.voice_config.available_voices);
      }
      setVoices(voiceList);
      setPersonalities(p?.personalities || p || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const speak = async () => {
    if (!ttsText.trim()) return;
    const res = await authFetch(`${API}/api/voice/speak`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: ttsText }),
    });
    setResult(JSON.stringify(await res.json(), null, 2));
  };

  const setPersonality = async (name: string) => {
    const res = await authFetch(`${API}/api/voice/set-personality`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ personality: name }),
    });
    setResult(JSON.stringify(await res.json(), null, 2));
    refresh();
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Mic size={22} className="text-[var(--color-nexus-accent)]" /> Voice System
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">TTS, STT, voces y personalidades</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* NEXUS Voice Control */}
      <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider flex items-center gap-1.5">
            <Bot size={11} /> NEXUS Voice
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${jarvisOnline ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" : "bg-red-500"}`} />
            <span className="text-[10px] font-mono text-[var(--color-nexus-muted)]">{jarvisOnline ? "ONLINE" : "OFFLINE"}</span>
            {jarvisOnline ? (
              <button onClick={stopJarvis} className="p-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all" title="Detener NEXUS Voice">
                <Square size={12} />
              </button>
            ) : (
              <button onClick={startJarvis} disabled={jarvisStarting} className="p-1.5 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-all disabled:opacity-30" title="Iniciar NEXUS Voice">
                {jarvisStarting ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} />}
              </button>
            )}
          </div>
        </div>
      </div>

      {status && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-2">Estado</div>
          <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)]">{JSON.stringify(status, null, 2)}</pre>
        </div>
      )}

      <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
        <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider flex items-center gap-1.5"><Volume2 size={11} /> Text to Speech</div>
        <div className="flex gap-2">
          <input value={ttsText} onChange={e => setTtsText(e.target.value)} placeholder="Texto para hablar..."
            className="flex-1 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none" />
          <button onClick={speak} className="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white">Hablar</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-3 flex items-center gap-1.5"><Volume2 size={11} /> Voces disponibles</div>
          <div className="space-y-1.5 max-h-48 overflow-auto">
            {voices.length > 0 ? voices.map((v: any, i: number) => (
              <div key={i} className="text-[11px] text-[var(--color-nexus-text-sub)] px-2 py-1 bg-[var(--color-nexus-surface-2)] rounded-lg">{typeof v === "string" ? v : v.name || JSON.stringify(v)}</div>
            )) : <div className="text-xs text-[var(--color-nexus-muted)]">Sin voces</div>}
          </div>
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-3 flex items-center gap-1.5"><UserCircle size={11} /> Personalidades</div>
          <div className="space-y-1.5 max-h-48 overflow-auto">
            {personalities.length > 0 ? personalities.map((p: any, i: number) => {
              const name = typeof p === "string" ? p : p.name;
              return (
                <button key={i} onClick={() => setPersonality(name)}
                  className="w-full text-left text-[11px] text-[var(--color-nexus-text-sub)] px-2 py-1.5 bg-[var(--color-nexus-surface-2)] rounded-lg hover:border-[var(--color-nexus-accent)] hover:text-[var(--color-nexus-accent)] transition-colors">
                  {name}
                </button>
              );
            }) : <div className="text-xs text-[var(--color-nexus-muted)]">Sin personalidades</div>}
          </div>
        </div>
      </div>

      {result && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-2">Resultado</div>
          <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-32 overflow-auto">{result}</pre>
        </div>
      )}
    </div>
  );
}
