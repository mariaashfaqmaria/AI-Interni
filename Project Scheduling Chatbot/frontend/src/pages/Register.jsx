// frontend/src/pages/Register.jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bot } from "lucide-react";
import api from "../api";

export default function Register() {
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
        const { data } = await api.post("/auth/register", form);
      localStorage.setItem("token", data.access_token);
      navigate("/");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Check your details (username 3+, password 6+ characters)");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <Bot size={48} className="accent" />
        <h2>Create account</h2>
        <input placeholder="Username" value={form.username} onChange={set("username")} />
        <input type="email" placeholder="Email" value={form.email} onChange={set("email")} />
        <input type="password" placeholder="Password (min 6 characters)" value={form.password} onChange={set("password")} />
        <button className="btn" type="submit" disabled={loading}>{loading ? "Creating..." : "Register"}</button>
        {error && <p className="error">{error}</p>}
        <p className="switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </form>
    </div>
  );
}
