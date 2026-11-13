// frontend/src/pages/Dashboard.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, FolderOpen, CheckCircle2, CalendarDays, BarChart3, Lightbulb, Zap, ArrowRight, MessageSquare, ClipboardCheck, CheckSquare, Clock, Heart, GraduationCap, Building2 } from "lucide-react";
import api, { errorMessage } from "../api";
import ChatPanel from "../components/ChatPanel";
import Calendar from "../components/Calendar";
import { fmtShort } from "../utils";

const statMeta = [
  { icon: FolderOpen, key: "total_projects", label: "Total Projects", color: "#5b3fd9" },
  { icon: CheckCircle2, key: "active_projects", label: "Active Projects", color: "#16a34a" },
  { icon: CalendarDays, key: "scheduled_tasks", label: "Scheduled Tasks", color: "#2563eb" },
  { icon: BarChart3, key: "overall_progress", label: "Overall Progress", color: "#f59e0b" },
];
const icons = [Heart, GraduationCap, Building2];
const colors = ["#e11d48", "#2563eb", "#2563eb"];
const actions = [
  { to: "/chatbot", label: "New Chat", icon: MessageSquare, cls: "purple" },
  { to: "/planner", label: "Plan Project", icon: ClipboardCheck, cls: "blue" },
  { to: "/tasks", label: "View Tasks", icon: CheckSquare, cls: "green" },
  { to: "/history", label: "View History", icon: Clock, cls: "orange" },
];

export default function Dashboard() {
  const [stats, setStats] = useState({});
  const [suggestions, setSuggestions] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true); setError("");
    try {
      const [s, p, t] = await Promise.all([api.get("/dashboard/stats"), api.get("/projects/suggestions"), api.get("/tasks")]);
      setStats(s.data); setSuggestions(p.data); setTasks(t.data.slice(0, 5));
    } catch (e) { setError(errorMessage(e, "Could not load dashboard information.")); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const toggle = async (task) => {
    const status = task.status === "done" ? "todo" : "done";
    try { const { data } = await api.patch(`/tasks/${task.id}`, { status }); setTasks((old) => old.map((x) => x.id === data.id ? data : x)); }
    catch (e) { setError(errorMessage(e, "Could not update task.")); }
  };
  return (
    <div className="grid">
      <div className="col">
        <section className="banner"><div><h1>Welcome to<br />AI Project Architect!</h1><p>Discover, plan and schedule your AI projects with the power of AI.</p></div><Bot size={120} strokeWidth={1.2} /></section>
        <div className="stats">{statMeta.map(({ icon: Icon, key, label, color }) => <div key={key} className="card stat"><Icon size={38} color={color} /><div><b>{stats[key] ?? (loading ? "…" : "0")}</b><span>{label}</span></div></div>)}</div>
        {error && <p className="error">{error}</p>}
        <ChatPanel />
        <section className="card"><div className="card-head"><h3 className="card-title"><CheckSquare size={20} className="accent" /> Your Tasks</h3><Link className="link" to="/tasks">View All <ArrowRight size={14} /></Link></div>
          {tasks.map((t) => <div key={t.id} className="task"><input type="checkbox" checked={t.status === "done"} onChange={() => toggle(t)} /><span className={t.status === "done" ? "muted" : ""}>{t.title}</span><span className={`pill ${t.status === "done" ? "done" : "high"}`}>{t.status === "done" ? "Completed" : t.priority}</span><small className="muted">{t.due}</small></div>)}
          {!loading && tasks.length === 0 && <p className="muted">No tasks yet. Generate a plan or add tasks from Tasks.</p>}
        </section>
      </div>
      <div className="col">
        <section className="card"><div className="card-head"><h3 className="card-title"><Lightbulb size={20} color="#f59e0b" /> Project Suggestions</h3><Link className="link" to="/explorer">View All <ArrowRight size={14} /></Link></div>
          {suggestions.map((p, i) => { const Icon = icons[i % icons.length]; return <div key={p.id} className="suggest"><div className="sg-icon"><Icon size={30} color={colors[i % colors.length]} /></div><div><b>{p.name}</b><p>{p.description}</p></div><Link className="btn small" to="/planner" state={{ project: p.name }}>Select</Link></div>; })}
          {!loading && suggestions.length === 0 && <p className="muted">No project suggestions available.</p>}
        </section>
        <Calendar />
        <section className="card"><h3 className="card-title"><Zap size={20} color="#f59e0b" /> Quick Actions</h3><div className="actions">{actions.map(({ to, label, icon: Icon, cls }) => <Link key={label} to={to} className={`action ${cls}`}><Icon size={18} /> {label}</Link>)}</div></section>
      </div>
    </div>
  );
}