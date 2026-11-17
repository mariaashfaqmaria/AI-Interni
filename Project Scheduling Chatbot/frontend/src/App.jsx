// frontend/src/App.jsx
import { useEffect, useState } from "react";
import { Routes, Route, Navigate, Outlet, useNavigate } from "react-router-dom";
import api from "./api";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Chatbot from "./pages/Chatbot";
import ProjectExplorer from "./pages/ProjectExplorer";
import ProjectPlanner from "./pages/ProjectPlanner";
import Schedule from "./pages/Schedule";
import Tasks from "./pages/Tasks";
import History from "./pages/History";

const isMobile = () => window.matchMedia("(max-width: 760px)").matches;

function Layout() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(() => !isMobile()); // closed by default on phones
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [authVersion, setAuthVersion] = useState(0);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");
  const token = localStorage.getItem("token");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    let alive = true;
    if (!token) { setChecking(false); return () => { alive = false; }; }
    setChecking(true);
    api.get("/auth/me")
      .then(({ data }) => { if (alive) setUser(data); })
      .catch((err) => {
        if (!alive) return;
        setUser(null);
        if ([401, 403].includes(err.response?.status)) {
          localStorage.removeItem("token");
          navigate("/login", { replace: true });
        }
      })
      .finally(() => { if (alive) setChecking(false); });
    return () => { alive = false; };
  }, [token, authVersion, navigate]);

  const closeOnMobile = () => { if (isMobile()) setOpen(false); };

  if (!token) return <Navigate to="/login" replace />;
  if (checking) {
    return (
      <div className="login-page">
        <div className="skeleton" style={{ width: 260, height: 18 }} />
      </div>
    );
  }

  return (
    <div className="shell">
      {open && <Sidebar user={user} onNavigate={closeOnMobile} />}
      {open && <div className="backdrop" onClick={() => setOpen(false)} />}
      <div className="main">
        <Topbar
          user={user}
          onMenu={() => setOpen((v) => !v)}
          theme={theme}
          onTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
        />
        <div className="page-content">
          <Outlet context={{ user, refreshUser: () => setAuthVersion((v) => v + 1) }} />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/chatbot" element={<Chatbot />} />
        <Route path="/explorer" element={<ProjectExplorer />} />
        <Route path="/planner" element={<ProjectPlanner />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/history" element={<History />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}