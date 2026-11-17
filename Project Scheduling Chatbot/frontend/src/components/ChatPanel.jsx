// frontend/src/components/ChatPanel.jsx

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Send, User, MessageSquare, Copy, Check, Trash2 } from "lucide-react";
import api from "../api";

const QUICK = ["Explain architecture", "Show tech stack", "Suggest evaluation"];
const welcome = () => ({ role: "bot", text: "Hi! Ask me about your projects or schedule.", time: new Date() });
const clock = (d) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export default function ChatPanel({ full = false }) {
  const [messages, setMessages] = useState([welcome()]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("From document");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(null);
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const bottom = useRef(null);
  const box = useRef(null);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const send = async (override) => {
    const text = (override ?? input).trim();
    if (!text || loading) return;
    setMessages((m) => [...m, { role: "user", text, time: new Date() }]);
    setInput("");
    if (box.current) box.current.style.height = "auto";
    setLoading(true);
    try {
      const { data } = await api.post("/chat", { message: text, thread_id: threadId, mode });
      setMessages((m) => [...m, { role: "bot", text: data.reply, time: new Date() }]);
    } catch {
      setMessages((m) => [...m, { role: "bot", text: "Something went wrong. Please try again.", time: new Date() }]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const grow = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
  };

  const copy = async (i, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(null), 1500);
    } catch { /* clipboard blocked */ }
  };

  const clear = () => { setMessages([welcome()]); setThreadId(crypto.randomUUID()); };

  return (
    <section className={`card chat ${full ? "full" : ""}`}>
      <div className="card-head">
        <h3 className="card-title"><MessageSquare size={20} className="accent" /> Ask Our AI Chatbot</h3>
        <button className="icon-btn" onClick={clear} aria-label="Clear chat" title="Clear chat"><Trash2 size={18} /></button>
      </div>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`row ${m.role}`}>
            {m.role === "bot" && <div className="bubble-avatar"><Bot size={22} /></div>}
            <div>
              <div className={`msg ${m.role}`}>
                {m.role === "bot" ? <div className="md"><ReactMarkdown>{m.text}</ReactMarkdown></div> : m.text}
              </div>
              <div className="msg-meta">
                {clock(m.time)}
                {m.role === "bot" && i > 0 && (
                  <button className="icon-btn" onClick={() => copy(i, m.text)} aria-label="Copy reply">
                    {copied === i ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                )}
              </div>
            </div>
            {m.role === "user" && <div className="bubble-avatar user"><User size={20} /></div>}
          </div>
        ))}
        {loading && (
          <div className="row bot">
            <div className="bubble-avatar"><Bot size={22} /></div>
            <div className="msg bot"><span className="typing"><i /><i /><i /></span></div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      {messages.length === 1 && (
        <div className="chips">
          {QUICK.map((q) => <button key={q} className="chip" onClick={() => send(q)}>{q}</button>)}
        </div>
      )}

      <div className="input-row">
        <select value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Answer mode">
          <option value="From document">From document</option>
          <option value="General advice">General advice</option>
        </select>
        <textarea ref={box} rows={1} value={input} placeholder="Type your message... (Shift+Enter for new line)"
                  onChange={grow} onKeyDown={onKeyDown} aria-label="Message" />
        <button className="btn send" onClick={() => send()} disabled={loading} aria-label="Send"><Send size={20} /></button>
      </div>
    </section>
  );
}