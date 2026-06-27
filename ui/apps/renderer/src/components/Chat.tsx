import { RefObject } from "react";
import "./Chat.css";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  gem?: string;
}

interface ChatProps {
  messages: Message[];
  loading: boolean;
  chatEndRef: RefObject<HTMLDivElement>;
}

function Chat({
  messages,
  loading,
  chatEndRef,
}: ChatProps) {
  return (
    <div className="chat">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome">
            <h2>Bienvenido a NEXUS IA v2.0</h2>
            <p>
              Tu organismo de IA autoevolutivo. Selecciona una gema y
              comienza.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-header">
              <span className="message-role">
                {msg.role === "user"
                  ? "Tu"
                  : msg.role === "system"
                  ? "Sistema"
                  : msg.gem
                  ? msg.gem.charAt(0).toUpperCase() + msg.gem.slice(1)
                  : "NEXUS"}
              </span>
              <span className="message-time">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">
              <pre>{msg.content}</pre>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>
    </div>
  );
}

export default Chat;
