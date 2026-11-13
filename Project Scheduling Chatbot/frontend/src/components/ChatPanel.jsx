// frontend/src/components/ChatPanel.jsx
import { useState, useRef, useEffect } from "react";
import { Bot, Send, User, MessageSquare } from "lucide-react";
import api from "../api";

export default function ChatPanel({ full = false }) {
  const [messages, setMessages] = useState([
    { role: "bot", text: "Hi! Ask me about your projects or schedule." },
  ]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("From document");
  const [loading, setLoading] = useState(false);
  const [threadId] = useState(() => crypto.randomUUID());
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);
    try {
      const { data } = await api.post("/chat", { message: text, thread_id: threadId, mode });
      setMessages((m) => [...m, { role: "bot", text: data.reply }]);
    } catch {
      setMessages((m) => [...m, { role: "bot", text: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={`card chat ${full ? "full" : ""}`}>
      <h3 className="card-title"><MessageSquare size={20} className="accent" /> Ask Our AI Chatbot</h3>
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`row ${m.role}`}>
            {m.role === "bot" && <div className="bubble-avatar"><Bot size={22} /></div>}
            <div className={`msg ${m.role}`}>{m.text}</div>
            {m.role === "user" && <div className="bubble-avatar user"><User size={20} /></div>}
          </div>
        ))}
        {loading && <div className="row bot"><div className="bubble-avatar"><Bot size={22} /></div><div className="msg bot">Thinking...</div></div>}
        <div ref={bottom} />
      </div>
      <div className="input-row">
        <select value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Answer mode">
          <option value="From document">From document</option>
          <option value="General advice">General advice</option>
        </select>
        <input value={input} placeholder="Type your message..." onChange={(e) => setInput(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && send()} />
        <button className="btn send" onClick={send} disabled={loading}><Send size={20} /></button>
      </div>
    </section>
  );
}