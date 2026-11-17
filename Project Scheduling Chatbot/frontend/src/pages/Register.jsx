// frontend/src/pages/Register.jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bot } from "lucide-react";
import api from "../api";
import PasswordField from "../components/PasswordField";

export default function Register() {
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  // Inline validation (shown while typing)
  const errors = {
    username:
      form.username && form.username.length < 3
        ? "Username must be at least 3 characters"
        : "",
    password:
      form.password && form.password.length < 6
        ? "Password must be at least 6 characters"
        : "",
  };

  const invalid =
    !form.username ||
    !form.email ||
    !form.password ||
    errors.username ||
    errors.password;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      localStorage.setItem("token", data.access_token);
      navigate("/", { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Check your details (username 3+, password 6+ characters)"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <Bot size={48} className="accent" />
        <h2>Create account</h2>

        <input
          placeholder="Username"
          autoComplete="username"
          value={form.username}
          onChange={set("username")}
        />
        {errors.username && <small className="field-error">{errors.username}</small>}

        <input
          type="email"
          placeholder="Email"
          autoComplete="email"
          value={form.email}
          onChange={set("email")}
        />

        <PasswordField
          placeholder="Password (min 6 characters)"
          autoComplete="new-password"
          value={form.password}
          onChange={set("password")}
        />
        {errors.password && <small className="field-error">{errors.password}</small>}

        <button className="btn" type="submit" disabled={loading || invalid}>
          {loading ? "Creating..." : "Register"}
        </button>

        {error && <p className="error">{error}</p>}
        <p className="switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}