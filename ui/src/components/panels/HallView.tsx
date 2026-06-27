import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Users2, RefreshCw, ChevronRight, MessageCircle } from "lucide-react";



interface Room { id: string; name: string; gems: string[]; created_at: string; event_count: number; }
interface Event { timestamp: string; gem: string; type: string; content: string; }

export function HallView() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/hall`);
      const data = await res.json();
      setRooms(data.rooms || data || []);
    } catch { setRooms([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const loadTimeline = async (id: string) => {
    setSelected(id);
    try {
      const res = await authFetch(`${API}/api/hall/${id}/timeline`);
      const data = await res.json();
      setTimeline(data.events || data.timeline || []);
    } catch { setTimeline([]); }
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Users2 size={22} className="text-[var(--color-nexus-accent)]" /> Collaboration Hall
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Salas de colaboración entre gemas con timeline</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="flex gap-4 h-[calc(100vh-220px)]">
        {/* Rooms list */}
        <div className="w-72 shrink-0 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl overflow-y-auto">
          <div className="px-3 py-2 border-b border-[var(--color-nexus-border)] text-[10px] font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">
            Salas ({rooms.length})
          </div>
          {rooms.map((r) => (
            <button key={r.id} onClick={() => loadTimeline(r.id)}
              className={`w-full text-left px-3 py-2.5 border-b border-[var(--color-nexus-border)] hover:bg-[var(--color-nexus-surface-2)] transition-colors ${selected === r.id ? "bg-[var(--color-nexus-accent-bg)]" : ""}`}>
              <div className="flex items-center gap-2">
                <div className="text-xs font-medium text-[var(--color-nexus-text)] flex-1 truncate">{r.name || r.id}</div>
                <ChevronRight size={12} className="text-[var(--color-nexus-muted)]" />
              </div>
              <div className="text-[10px] text-[var(--color-nexus-muted)] mt-0.5">{r.gems?.join(", ")} · {r.event_count || 0} eventos</div>
            </button>
          ))}
          {rooms.length === 0 && <div className="p-4 text-xs text-[var(--color-nexus-muted)] text-center">Sin salas activas</div>}
        </div>

        {/* Timeline */}
        <div className="flex-1 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl overflow-y-auto">
          {selected ? (
            <div className="p-4 space-y-3">
              {timeline.map((ev, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-1 rounded-full shrink-0" style={{ backgroundColor: "var(--color-nexus-accent)" }} />
                  <div>
                    <div className="flex items-center gap-2 text-[10px] text-[var(--color-nexus-muted)]">
                      <span className="font-medium text-[var(--color-nexus-accent)]">{ev.gem}</span>
                      <span className="font-mono">{new Date(ev.timestamp).toLocaleTimeString("es")}</span>
                      <span className="px-1.5 py-0.5 rounded bg-[var(--color-nexus-surface-2)]">{ev.type}</span>
                    </div>
                    <div className="text-xs text-[var(--color-nexus-text-sub)] mt-1">{ev.content}</div>
                  </div>
                </div>
              ))}
              {timeline.length === 0 && <div className="text-center py-8 text-xs text-[var(--color-nexus-muted)]">Sin eventos en esta sala</div>}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <MessageCircle size={40} className="text-[var(--color-nexus-border)] mb-3" />
              <div className="text-sm text-[var(--color-nexus-muted)]">Selecciona una sala para ver el timeline</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
