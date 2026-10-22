
import { useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [sessionId, setSessionId] = useState("");
  const [enteredId, setEnteredId] = useState("");
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadConversation(event) {
    event.preventDefault();

    const id = enteredId.trim();

    if (!id) {
      setError("Please enter a Session ID.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/chat/history/${encodeURIComponent(id)}`
      );

      if (!response.ok) {
        throw new Error(
          `Could not load conversation (${response.status}).`
        );
      }

      const data = await response.json();

      setSessionId(data.session_id);
      setEnteredId(data.session_id);
      setMessages(data.history || []);
    } catch (err) {
      setError(err.message || "Could not load conversation.");
    } finally {
      setLoading(false);
    }
  }

  function newChat() {
    setSessionId("");
    setEnteredId("");
    setMessages([]);
    setPrompt("");
    setError("");
  }

  async function sendMessage(event) {
    event.preventDefault();

    const message = prompt.trim();

    if (!message || loading) return;

    setError("");
    setPrompt("");

    // Show the user's message immediately.
    setMessages((previous) => [
      ...previous,
      { role: "user", content: message },
    ]);

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          session_id: sessionId || null,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(
          detail || `Chat request failed (${response.status}).`
        );
      }

      const data = await response.json();

      setSessionId(data.session_id);
      setEnteredId(data.session_id);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.response,
        },
      ]);
    } catch (err) {
      setError(
        `${err.message || "Unable to contact the API."} ` +
          "Please check that your FastAPI server is running."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">💬</span>
          <div>
            <h2>Categorical</h2>
            <p>AI Chatbot</p>
          </div>
        </div>

        <div className="sidebar-section">
          <h3>Conversation Session</h3>

          <form onSubmit={loadConversation}>
            <label htmlFor="sessionId">
              Enter existing Session ID
            </label>

            <input
              id="sessionId"
              type="text"
              value={enteredId}
              onChange={(event) => setEnteredId(event.target.value)}
              placeholder="Enter session ID..."
            />

            <button
              className="secondary-button"
              type="submit"
              disabled={loading}
            >
              Load Conversation
            </button>
          </form>

          <button
            className="new-chat-button"
            type="button"
            onClick={newChat}
          >
            <span>＋</span> New Chat
          </button>
        </div>

        {sessionId && (
          <div className="session-card">
            <p>Current Session ID</p>
            <code>{sessionId}</code>
            <button
              type="button"
              className="copy-button"
              onClick={() => {
                navigator.clipboard
                  .writeText(sessionId)
                  .catch(() => setError("Could not copy Session ID."));
              }}
            >
              Copy Session ID
            </button>
          </div>
        )}

        <div className="sidebar-footer">
          <span className="status-dot" />
          FastAPI Backend
          <p>LangGraph · OpenRouter · PostgreSQL</p>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <h1>💬 Categorical Chatbot</h1>
            <p>Ask a question and let your AI assistant help.</p>
          </div>
          <span className="online-badge">● Ready</span>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon">✦</div>
              <h2>How can I help you today?</h2>
              <p>
                Send a message to start a conversation, or load
                an existing session from the sidebar.
              </p>
              <div className="suggestion">
                <span>✧</span>
                <div>
                  <strong>Ask a question</strong>
                  <p>Type your message below to get started.</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((msg, index) => {
                const isAssistant = msg.role === "assistant";

                return (
                  <div
                    className={`message-row ${
                      isAssistant ? "assistant-row" : "user-row"
                    }`}
                    key={`${index}-${msg.role}`}
                  >
                    <div className="avatar">
                      {isAssistant ? "✦" : "You"}
                    </div>
                    <div className="message-content">
                      <span className="message-author">
                        {isAssistant ? "AI Assistant" : "You"}
                      </span>
                      <div className="message-bubble">
                        {msg.content}
                      </div>
                    </div>
                  </div>
                );
              })}

              {loading && (
                <div className="message-row assistant-row">
                  <div className="avatar">✦</div>
                  <div className="message-content">
                    <span className="message-author">
                      AI Assistant
                    </span>
                    <div className="message-bubble typing">
                      <span />
                      <span />
                      <span />
                      <span className="typing-label">
                        Generating response...
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <footer className="composer-area">
          {error && (
            <div className="error-message" role="alert">
              {error}
              <button
                type="button"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          )}

          <form className="composer" onSubmit={sendMessage}>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault();
                  event.currentTarget.form.requestSubmit();
                }
              }}
              placeholder="Ask your question..."
              rows={2}
              disabled={loading}
            />

            <button
              className="send-button"
              type="submit"
              disabled={loading || !prompt.trim()}
              aria-label="Send message"
              title="Send message"
            >
              ➤
            </button>
          </form>

          <p className="composer-note">
            Powered by FastAPI, LangGraph, OpenRouter and PostgreSQL.
            Press Enter to send; Shift + Enter for a new line.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
