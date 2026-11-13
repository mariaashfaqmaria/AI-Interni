import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Plus, Send, Bot, User, MessageSquare } from "lucide-react";
import api, { errorMessage } from "../api";
import "../chatbot-response.css";

const quick = [
  "Explain architecture",
  "Show tech stack",
  "Suggest evaluation",
];


function AssistantMessage({ text }) {
  const lines = String(text ?? "").split(/\r?\n/);

  return (
    <div className="assistant-response">
      {lines.map((line, index) => {
        const value = line.trim();

        if (!value) {
          return <div className="assistant-response-gap" key={`gap-${index}`} />;
        }

        if (/^#{1,3}\s+/.test(value)) {
          return (
            <div className="assistant-response-heading" key={index}>
              {value.replace(/^#{1,3}\s+/, "")}
            </div>
          );
        }

        if (/^[-*•]\s+/.test(value)) {
          return (
            <div className="assistant-response-bullet" key={index}>
              <span aria-hidden="true">•</span>
              <span>{value.replace(/^[-*•]\s+/, "")}</span>
            </div>
          );
        }

        return <p className="assistant-response-paragraph" key={index}>{value}</p>;
      })}
    </div>
  );
}

export default function Chatbot() {
  const location = useLocation();
  const navigate = useNavigate();

  const [chats, setChats] = useState([]);
  const [threadId, setThreadId] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);
  const [file, setFile] = useState(null);

  const [input, setInput] = useState("");
  const [mode, setMode] = useState("From document");

  const [loading, setLoading] = useState(false);
  const [openingChatId, setOpeningChatId] = useState(null);
  const [error, setError] = useState("");

  const messagesRef = useRef(null);
  const activeRequestRef = useRef(false);
  const openingChatRef = useRef(false);

  // Load saved conversations, newest first.
  const loadChats = useCallback(async () => {
    try {
      const { data } = await api.get("/conversations", {
        params: { type: "chat" },
      });

      const chatList = Array.isArray(data) ? data : [];

      setChats(
        [...chatList].sort(
          (a, b) =>
            new Date(b.updated_at || 0) - new Date(a.updated_at || 0)
        )
      );

      return chatList;
    } catch (e) {
      setError(errorMessage(e, "Could not load chat history."));
      return [];
    }
  }, []);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Scroll only the conversation messages area.
  useEffect(() => {
    const container = messagesRef.current;

    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, loading]);

  // Convert backend message history into the frontend format.
  const normalizeMessages = (history) => {
    if (!Array.isArray(history)) return [];

    return history.map((message) => ({
      role:
        message.role === "user" || message.role === "human"
          ? "user"
          : "bot",
      text: message.text ?? message.content ?? "",
      sources: message.sources || null,
    }));
  };

  // Convert historical and current source formats into one list.
  const normalizeSources = (history) => {
    if (!Array.isArray(history)) return [];

    return history.reduce((allSources, message) => {
      if (!message.sources) return allSources;

      if (Array.isArray(message.sources)) {
        return [...allSources, ...message.sources];
      }

      return [...allSources, message.sources];
    }, []);
  };

  // Open a previous conversation from Recent Chats.
  const openChat = async (chat) => {
    if (
      loading ||
      activeRequestRef.current ||
      openingChatRef.current
    ) {
      return;
    }

    if (String(conversationId) === String(chat.id)) {
      return;
    }

    openingChatRef.current = true;
    setOpeningChatId(chat.id);
    setError("");

    try {
      // Retrieve the complete conversation history before changing the
      // active thread, so a failed request cannot change the current chat.
      const { data } = await api.get(
        `/conversations/${encodeURIComponent(chat.id)}`
      );

      const restoredThreadId = data.thread_id || chat.thread_id;

      if (!restoredThreadId) {
        throw new Error(
          "This conversation does not contain a valid thread ID."
        );
      }

      // Restore selected conversation identity.
      setConversationId(data.id ?? chat.id);
      setThreadId(restoredThreadId);

      // Restore previous messages.
      const restoredMessages = normalizeMessages(data.messages);
      setMessages(restoredMessages);

      // Restore sources from historical messages.
      setSources(normalizeSources(data.messages));

      setFile(data.file || null);
      setInput("");

    } catch (e) {
      console.error("Open conversation error:", e);

      setError(
        errorMessage(e, "Could not open the selected conversation.")
      );
    } finally {
      openingChatRef.current = false;
      setOpeningChatId(null);
    }
  };

  // Restore a conversation opened from another module.
  useEffect(() => {
    const id = location.state?.threadId;

    if (!id) return;

    let alive = true;

    const restoreChat = async () => {
      try {
        setError("");

        const { data } = await api.get(
          `/conversations/by-thread/${encodeURIComponent(id)}`
        );

        if (!alive) return;

        setConversationId(data.id);
        setThreadId(data.thread_id);
        setMessages(normalizeMessages(data.messages));
        setSources(normalizeSources(data.messages));
        setFile(data.file || null);
        setInput("");

      } catch (e) {
        if (alive) {
          setError(
            errorMessage(e, "Could not restore this conversation.")
          );
        }
      }
    };

    restoreChat();

    navigate(location.pathname, {
      replace: true,
      state: {},
    });

    return () => {
      alive = false;
    };
  }, [location.state, location.pathname, navigate]);

  // Start a completely new conversation.
  const newChat = () => {
    if (loading || openingChatRef.current) return;

    setThreadId(null);
    setConversationId(null);
    setMessages([]);
    setSources([]);
    setFile(null);
    setInput("");
    setError("");
  };

  // Send a message in the current or selected conversation.
  const send = async (text) => {
    const message = (text ?? input).trim();

    if (
      !message ||
      loading ||
      openingChatRef.current ||
      activeRequestRef.current
    ) {
      return;
    }

    activeRequestRef.current = true;

    setInput("");
    setError("");

    setMessages((old) => [
      ...old,
      { role: "user", text: message },
    ]);

    setLoading(true);

    try {
      const { data } = await api.post("/chat", {
        message,
        thread_id: threadId,
        mode,
      });

      // Keep the thread ID returned by the backend.
      setThreadId(data.thread_id);
      setConversationId(data.conversation_id);

      setFile(data.file || null);

      setSources(
        mode === "From document" ? data.sources || [] : []
      );

      setMessages((old) => [
        ...old,
        {
          role: "bot",
          text: data.reply,
        },
      ]);

      // Refresh Recent Chats after saving the new conversation turn.
      await loadChats();

    } catch (e) {
      console.error("Chat request error:", e);

      setMessages((old) => [
        ...old,
        {
          role: "bot",
          text: errorMessage(e, "The chatbot request failed."),
        },
      ]);
    } finally {
      setLoading(false);
      activeRequestRef.current = false;
    }
  };

  return (
    <div className="chatbot-page">

      {/* Chatbot Heading */}
      <div className="chatbot-header">
        <div>
          <h1>Chatbot</h1>
          <p>
            Ask questions about the project document; answers show their sources.
          </p>
        </div>

        <button
          className="new-chat-btn"
          onClick={newChat}
          disabled={loading || openingChatId !== null}
        >
          <Plus size={18} />
          New chat
        </button>
      </div>

      {error && (
        <p className="chatbot-error">
          {error}
        </p>
      )}

      <div className="chatbot-layout">

        {/* Recent Chats */}
        <aside className="chatbot-panel recent-panel">
          <h3>Recent chats</h3>

          <div className="recent-chat-list">
            {chats.map((chat) => {
              const isSelected =
                String(conversationId) === String(chat.id);

              const isOpening =
                String(openingChatId) === String(chat.id);

              return (
                <button
                  key={chat.id}
                  type="button"
                  className={`recent-chat-item ${
                    isSelected ? "selected" : ""
                  }`}
                  onClick={() => openChat(chat)}
                  disabled={
                    loading ||
                    openingChatId !== null ||
                    activeRequestRef.current
                  }
                  title={chat.title}
                >
                  <MessageSquare size={16} />

                  <span>
                    {chat.title || "Untitled conversation"}
                  </span>

                  {isOpening && (
                    <span className="chat-loading-label">
                      Loading...
                    </span>
                  )}
                </button>
              );
            })}

            {!chats.length && (
              <p className="empty-chat-text">
                No saved chats yet.
              </p>
            )}
          </div>
        </aside>

        {/* Conversation Panel */}
        <section className="chatbot-panel conversation-panel">

          <div className="messages-area" ref={messagesRef}>
            {messages.map((message, index) => (
              <div
                key={`${conversationId || "new"}-${index}`}
                className={`message-row ${
                  message.role === "user"
                    ? "user-message"
                    : "bot-message"
                }`}
              >
                <div className="message-avatar">
                  {message.role === "user" ? (
                    <User size={18} />
                  ) : (
                    <Bot size={20} />
                  )}
                </div>

                <div className="message-bubble">
                  {message.role === "bot" ? (
                    <AssistantMessage text={message.text} />
                  ) : (
                    message.text
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message-row bot-message">
                <div className="message-avatar">
                  <Bot size={20} />
                </div>

                <div className="message-bubble thinking">
                  Thinking...
                </div>
              </div>
            )}

            {openingChatId !== null && (
              <div className="chat-loading-message">
                Loading previous conversation...
              </div>
            )}

            {!messages.length &&
              !loading &&
              openingChatId === null && (
                <div className="chat-empty-state">
                  <Bot size={42} />
                  <h3>How can I help you?</h3>
                  <p>
                    Ask anything about your project document.
                  </p>
                </div>
              )}
          </div>

          {/* Input Area */}
          <div className="chat-input-section">

            <div className="quick-questions">
              {quick.map((question) => (
                <button
                  key={question}
                  onClick={() => send(question)}
                  disabled={loading || openingChatId !== null}
                >
                  {question}
                </button>
              ))}
            </div>

            <div className="chat-input-row">
              <input
                value={input}
                placeholder="Type your message..."
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                disabled={loading || openingChatId !== null}
              />

              <button
                className="chat-send-btn"
                onClick={() => send()}
                disabled={
                  loading ||
                  openingChatId !== null ||
                  !input.trim()
                }
              >
                <Send size={19} />
                Send
              </button>
            </div>
          </div>
        </section>

        {/* Sources and Answer Mode */}
        <aside className="chatbot-panel sources-panel">

          <h3>Sources used</h3>

          <div className="sources-list">

            {file && (
              <div className="source-file">
                {file}
              </div>
            )}

            {sources.map((source, index) => {
              // Historical sources from backend are strings.
              if (typeof source === "string") {
                return (
                  <div
                    key={`source-${index}`}
                    className="source-item"
                  >
                    {source}
                  </div>
                );
              }

              // Current project sources contain project metadata; older
              // page-based document sources are still supported.
              const sourceLabel = source.project_title
                ? `${source.project_title} · ${source.source_type || "project"}`
                : source.page
                  ? `Page ${source.page}`
                  : source.source_type || "Document source";

              return (
                <div
                  key={`source-${index}`}
                  className="source-item"
                >
                  {sourceLabel}
                  {Number.isFinite(Number(source.match)) && (
                    <> · match {Number(source.match).toFixed(2)}</>
                  )}
                </div>
              );
            })}

            {!sources.length && !file && (
              <p className="empty-chat-text">
                No sources yet.
              </p>
            )}
          </div>

          <h3 className="answer-mode-heading">
            Answer mode
          </h3>

          <div className="answer-mode-options">
            {["From document", "General advice"].map((answerMode) => (
              <button
                key={answerMode}
                className={
                  mode === answerMode ? "active-mode" : ""
                }
                onClick={() => setMode(answerMode)}
              >
                {answerMode}
              </button>
            ))}
          </div>

        </aside>

      </div>
    </div>
  );
}
