// frontend/src/components/Topbar.jsx
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Menu, Search, Bell, Moon, Sun } from "lucide-react";

const TITLES = {
  "/": "Dashboard", "/chatbot": "Chatbot", "/explorer": "Project Explorer",
  "/planner": "Project Planner", "/schedule": "Schedule", "/tasks": "Tasks", "/history": "History",
};

export default function Topbar({ onMenu, user, theme, onTheme }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [bell, setBell] = useState(false);
  const initials = (user?.username || "?").slice(0, 2).toUpperCase();

  const search = (e) => {
    e.preventDefault();
    navigate(`/tasks?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <header className="topbar">
      <button className="icon-btn" onClick={onMenu} aria-label="Toggle menu"><Menu size={22} /></button>
      <h2 className="page-title">{TITLES[pathname] || "AI Project Architect"}</h2>
      <form className="search" onSubmit={search} role="search">
        <Search size={18} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tasks..." aria-label="Search tasks" />
      </form>
      <button className="icon-btn" onClick={onTheme} aria-label="Toggle dark mode">
        {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
      </button>
      <div className="bell-wrap">
        <button className="icon-btn" onClick={() => setBell((v) => !v)} aria-label="Notifications"><Bell size={20} /></button>
        {bell && <div className="popover card">No new notifications</div>}
      </div>
      <div className="avatar big" title={user?.username}>{initials}</div>
    </header>
  );
}