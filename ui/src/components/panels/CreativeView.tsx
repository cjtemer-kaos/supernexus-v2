import { useState } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Palette, Music, Megaphone, Loader2, Image, Film } from "lucide-react";



type Tab = "design" | "music" | "producer";

export function CreativeView() {
  const [tab, setTab] = useState<Tab>("design");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "design", label: "Design", icon: <Palette size={13} /> },
    { id: "music", label: "Music", icon: <Music size={13} /> },
    { id: "producer", label: "Producer", icon: <Megaphone size={13} /> },
  ];

  const execute = async () => {
    if (!prompt.trim()) return;
    setLoading(true); setResult(null);
    try {
      let url = "", body: any = {};
      if (tab === "design") { url = `${API}/api/design/generate`; body = { prompt }; }
      else if (tab === "music") { url = `${API}/api/music/generate`; body = { prompt }; }
      else { url = `${API}/api/producer/campaign`; body = { description: prompt }; }

      const res = await authFetch(url, { method: "POST", body: JSON.stringify(body) });
      setResult(JSON.stringify(await res.json(), null, 2));
    } catch (e) { setResult(`Error: ${e}`); }
    setLoading(false);
  };

  const executeSecondary = async () => {
    setLoading(true); setResult(null);
    try {
      let url = "";
      let body: any = {};
      if (tab === "design") { url = `${API}/api/design/storyboard`; body = { prompt }; }
      else if (tab === "producer") { url = `${API}/api/producer/schedule`; body = { campaign: prompt }; }
      else return;

      const res = await authFetch(url, { method: "POST", body: JSON.stringify(body) });
      setResult(JSON.stringify(await res.json(), null, 2));
    } catch (e) { setResult(`Error: ${e}`); }
    setLoading(false);
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
          <Palette size={22} className="text-[var(--color-nexus-accent)]" /> Creative Studio
        </h1>
        <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Diseño, música y producción de contenido</p>
      </div>

      <div className="flex gap-1 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-1">
        {tabs.map(t => (
          <button key={t.id} onClick={() => { setTab(t.id); setResult(null); }}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${tab === t.id ? "bg-[var(--color-nexus-accent)] text-white" : "text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]"}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-4">
        <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={4}
          placeholder={tab === "design" ? "Describe el diseño que quieres generar..." : tab === "music" ? "Describe la música que quieres generar..." : "Describe la campaña de contenido..."}
          className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] outline-none resize-none" />
        <div className="flex gap-2">
          <button onClick={execute} disabled={loading || !prompt.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-50 transition-colors">
            {loading ? <Loader2 size={12} className="animate-spin" /> : tab === "design" ? <Image size={12} /> : tab === "music" ? <Music size={12} /> : <Megaphone size={12} />}
            {tab === "design" ? "Generar diseño" : tab === "music" ? "Generar música" : "Crear campaña"}
          </button>
          {(tab === "design" || tab === "producer") && (
            <button onClick={executeSecondary} disabled={loading || !prompt.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)] disabled:opacity-50 transition-colors">
              <Film size={12} />
              {tab === "design" ? "Storyboard" : "Schedule"}
            </button>
          )}
        </div>
      </div>

      {result && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-2">Resultado</div>
          <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-64 overflow-auto whitespace-pre-wrap">{result}</pre>
        </div>
      )}
    </div>
  );
}
