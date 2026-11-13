// frontend/src/components/Topbar.jsx
import { Menu, Search, Bell } from "lucide-react";

export default function Topbar({ onMenu, user }) {
  const initials = (user?.username || "?").slice(0, 2).toUpperCase();

  return (
    <header className="topbar">
      <button className="icon-btn" onClick={onMenu}><Menu size={22} /></button>
      <div className="search"><Search size={18} /><input placeholder="Search projects, tasks..." /></div>
      <button className="icon-btn"><Bell size={20} /></button>
      <div className="avatar big">{initials}</div>
    </header>
  );
}
