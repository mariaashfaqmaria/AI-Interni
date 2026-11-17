// frontend/src/pages/Login.jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bot } from "lucide-react";
import api from "../api";
import PasswordField from "../components/PasswordField";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { username, password });
      localStorage.setItem("token", data.access_token);
      navigate("/", { replace: true });
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <Bot size={48} className="accent" />
        <h2>AI Project Architect</h2>
        <input placeholder="Username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <PasswordField placeholder="Password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="btn" type="submit" disabled={loading || !username || !password}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
        {error && <p className="error">{error}</p>}
        <p className="switch">New here? <Link to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}