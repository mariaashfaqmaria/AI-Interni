// frontend/src/pages/Login.jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bot } from "lucide-react";
import api from "../api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/auth/login", { username, password });
      localStorage.setItem("token", data.access_token);
      navigate("/");
    } catch {
      setError("Invalid username or password");
    }
  };

  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <Bot size={48} className="accent" />
        <h2>AI Project Architect</h2>
        <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="btn" type="submit">Sign in</button>
        {error && <p className="error">{error}</p>}
        <p className="switch">New here? <Link to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}
