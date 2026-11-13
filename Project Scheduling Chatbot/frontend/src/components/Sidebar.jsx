// frontend/src/components/Sidebar.jsx
import { NavLink, useNavigate } from "react-router-dom";
import { Home, MessageSquare, Folder, ClipboardCheck, Calendar, CheckSquare, History, Bot, LogOut } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/chatbot", label: "Chatbot", icon: MessageSquare },
  { to: "/explorer", label: "Project Explorer", icon: Folder },
  { to: "/planner", label: "Project Planner", icon: ClipboardCheck },
  { to: "/schedule", label: "Schedule", icon: Calendar },
  { to: "/tasks", label: "Tasks", icon: CheckSquare },
  { to: "/history", label: "History", icon: History },
];

export default function Sidebar({ user }) {
  const navigate = useNavigate();
  const initials = (user?.username || "?").slice(0, 2).toUpperCase();

  const logout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <aside className="sidebar">
      <div className="brand"><Bot size={34} /><span>AI Project<br />Architect</span></div>
      <nav className="nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
            <Icon size={20} /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="user">
        <div className="avatar">{initials}</div>
        <div>
          <div>{user?.username || "Loading..."}</div>
          <small>{user?.email || ""}</small>
        </div>
      </div>
      <button className="logout" onClick={logout}><LogOut size={18} /> Logout</button>
    </aside>
  );
}
