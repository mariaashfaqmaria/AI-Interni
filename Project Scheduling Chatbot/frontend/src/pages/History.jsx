// frontend/src/pages/History.jsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, Download, MessageSquare, FileText, Trash2 } from "lucide-react";
import api, { errorMessage } from "../api";

const C = {
  primary: "#168f82",
  primaryDark: "#11796f",
  soft: "#e5f3f1",
  text: "#203344",
  muted: "#667b87",
  border: "#dfe8eb",
  card: "var(--card, #ffffff)",
  background: "var(--bg, #f4f7f8)",
};

const buttonStyle = (primary = false) => ({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 8,
  padding: "11px 16px",
  borderRadius: 10,
  border: primary ? "1px solid #168f82" : `1px solid ${C.border}`,
  background: primary ? C.primary : C.card,
  color: primary ? "#ffffff" : C.text,
  fontSize: 14,
  fontWeight: 650,
  cursor: "pointer",
});

export default function History() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [openingId, setOpeningId] = useState(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const { data } = await api.get("/conversations", {
          params: {
            q: query,
            type: filter === "All" ? "all" : filter.toLowerCase() === "chats" ? "chat" : "plan",
          },
        });
        if (alive) setItems(Array.isArray(data) ? data : []);
      } catch (e) {
        if (alive) setError(errorMessage(e, "Could not load history."));
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    return () => { alive = false; };
  }, [query, filter]);

  // Chat records open directly in the Chatbot. Plan records remain in the preview panel.
  const open = async (item) => {
    if (openingId !== null) return;
    setOpeningId(item.id);
    setError("");
    try {
      const { data } = await api.get(`/conversations/${encodeURIComponent(item.id)}`);
      const conversationType = String(data.type || item.type || "").toLowerCase();

      if (conversationType === "chat") {
        const threadId = data.thread_id || item.thread_id;
        if (!threadId) {
          setSelected(data);
          setError("This saved chat does not include a thread ID, so it cannot be resumed from the Chatbot.");
          return;
        }
        navigate("/chatbot", { state: { conversationId: data.id ?? item.id, threadId } });
        return;
      }

      setSelected(data);
    } catch (e) {
      setError(errorMessage(e, "Could not open conversation."));
    } finally {
      setOpeningId(null);
    }
  };

  const resumeSelected = () => {
    const threadId = selected?.thread_id;
    if (!threadId) {
      setError("This conversation does not have a thread ID and cannot be resumed.");
      return;
    }
    navigate("/chatbot", { state: { conversationId: selected.id, threadId } });
  };

  const exportAll = async () => {
    setError("");
    try {
      const { data } = await api.get("/conversations/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "history.json";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(errorMessage(e, "Could not export history."));
    }
  };

  const remove = async (id) => {
    setError("");
    try {
      await api.delete(`/conversations/${encodeURIComponent(id)}`);
      setItems((old) => old.filter((item) => item.id !== id));
      if (selected?.id === id) setSelected(null);
    } catch (e) {
      setError(errorMessage(e, "Could not delete conversation."));
    }
  };

  const filtered = useMemo(() => items, [items]);
  const selectedIsChat = String(selected?.type || "").toLowerCase() === "chat";

  return (
    <main className="history-page">
      <header className="history-header">
        <div>
          <span className="history-eyebrow">YOUR WORKSPACE</span>
          <h1>History</h1>
          <p>Pick up where you left off. Your previous chats and project plans are kept here.</p>
        </div>
        <button type="button" style={buttonStyle(false)} onClick={exportAll}>
          <Download size={16} /> Export all
        </button>
      </header>

      {error && <div className="history-error" role="alert">{error}</div>}

      <div className="history-layout">
        <section className="history-list-panel">
          <div className="history-search-wrap">
            <input
              className="history-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search conversations..."
              aria-label="Search conversations"
            />
          </div>

          <div className="history-filters" role="group" aria-label="Filter history">
            {["All", "Chats", "Plans"].map((value) => (
              <button
                type="button"
                key={value}
                className={`history-filter ${filter === value ? "active" : ""}`}
                onClick={() => setFilter(value)}
              >
                {value}
              </button>
            ))}
            <span className="history-count">{filtered.length} items</span>
          </div>

          <div className="history-items">
            {loading && <p className="history-empty">Loading your history...</p>}
            {!loading && filtered.map((item) => {
              const isChat = String(item.type || "").toLowerCase() === "chat";
              const isOpening = openingId === item.id;
              return (
                <button
                  type="button"
                  key={item.id}
                  className="history-item"
                  onClick={() => open(item)}
                  disabled={openingId !== null}
                  aria-label={`${isChat ? "Open chat" : "View plan"}: ${item.title || "Untitled"}`}
                >
                  <span className={`history-item-icon ${isChat ? "chat" : "plan"}`}>
                    {isChat ? <MessageSquare size={18} /> : <FileText size={18} />}
                  </span>
                  <span className="history-item-content">
                    <strong>{item.title || "Untitled conversation"}</strong>
                    <span>{item.when || "Date unavailable"} · {item.count ?? 0} messages · {isChat ? "Chat" : "Plan"}</span>
                  </span>
                  <span className="history-item-action">
                    {isOpening ? "Opening..." : <ArrowUpRight size={18} />}
                  </span>
                </button>
              );
            })}
            {!loading && !filtered.length && (
              <div className="history-empty">
                <MessageSquare size={26} />
                <strong>No conversations found</strong>
                <span>Try another search or choose a different filter.</span>
              </div>
            )}
          </div>
        </section>

        <aside className="history-preview-panel">
          {selected ? (
            <>
              <div className="history-preview-heading">
                <span className="history-eyebrow">CONVERSATION PREVIEW</span>
                <h2>{selected.title || "Untitled conversation"}</h2>
                <p>{selected.when || "Date unavailable"} · {selected.count ?? selected.messages?.length ?? 0} messages</p>
              </div>
              <div className="history-message-list">
                {selected.messages?.map((message, index) => (
                  <article className={`history-message ${message.role === "user" ? "from-user" : "from-bot"}`} key={`${selected.id}-${index}`}>
                    <strong>{message.role === "bot" || message.role === "assistant" ? "AI Assistant" : "You"}</strong>
                    <p>{message.text ?? message.content ?? ""}</p>
                    {message.sources && <small>Sources: {Array.isArray(message.sources) ? message.sources.join(", ") : message.sources}</small>}
                  </article>
                ))}
                {!selected.messages?.length && <p className="history-empty">No message preview is available.</p>}
              </div>
              <div className="history-preview-actions">
                {selectedIsChat && (
                  <button type="button" style={buttonStyle(true)} onClick={resumeSelected}>
                    <MessageSquare size={16} /> Resume in Chatbot
                  </button>
                )}
                <button type="button" style={buttonStyle(false)} onClick={() => remove(selected.id)}>
                  <Trash2 size={16} /> Delete
                </button>
              </div>
            </>
          ) : (
            <div className="history-preview-empty">
              <span className="history-preview-empty-icon"><MessageSquare size={25} /></span>
              <h2>Your conversations, in one place</h2>
              <p>Select a saved plan to preview it, or click any chat to continue it directly in the Chatbot.</p>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}