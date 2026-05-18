const WS_BASE = typeof window !== "undefined"
  ? `ws://${window.location.host}`
  : "ws://localhost:9001";

export type WSMessageType = "start" | "token" | "complete" | "error";

export interface WSMessage {
  type: WSMessageType;
  content?: string;
  gem?: string;
  gem_used?: string;
  tokens_used?: number;
  retry_after?: number;
}

export type WSStatus = "disconnected" | "connecting" | "connected" | "error";

interface UseWSChatOptions {
  onToken?: (token: string) => void;
  onComplete?: (gemUsed: string, tokensUsed: number) => void;
  onError?: (error: string) => void;
}

export function useWSChat(options: UseWSChatOptions = {}) {
  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let status: WSStatus = "disconnected";

  function getToken(): string | null {
    return localStorage.getItem("nexus-token");
  }

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    status = "connecting";
    const token = getToken();
    const url = token ? `${WS_BASE}/api/ws/chat?token=${token}` : `${WS_BASE}/api/ws/chat`;

    ws = new WebSocket(url);

    ws.onopen = () => {
      status = "connected";
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        switch (msg.type) {
          case "token":
            if (msg.content) options.onToken?.(msg.content);
            break;
          case "complete":
            if (msg.gem_used) options.onComplete?.(msg.gem_used, msg.tokens_used || 0);
            break;
          case "error":
            options.onError?.(msg.content || "Unknown error");
            break;
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      status = "disconnected";
      // Auto-reconnect after 2s
      reconnectTimer = setTimeout(connect, 2000);
    };

    ws.onerror = () => {
      status = "error";
    };
  }

  function sendMessage(message: string, gem = "auto") {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connect();
      // Wait for connection
      setTimeout(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ message, gem }));
        }
      }, 500);
      return;
    }
    ws.send(JSON.stringify({ message, gem }));
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws) ws.close();
    ws = null;
    status = "disconnected";
  }

  return { connect, sendMessage, disconnect, getStatus: () => status };
}
