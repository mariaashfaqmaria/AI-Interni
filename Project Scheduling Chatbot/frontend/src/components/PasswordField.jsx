// frontend/src/components/PasswordField.jsx
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export default function PasswordField({ value, onChange, placeholder, autoComplete }) {
  const [show, setShow] = useState(false);
  return (
    <div className="pw">
      <input type={show ? "text" : "password"} value={value} onChange={onChange}
             placeholder={placeholder} autoComplete={autoComplete} />
      <button type="button" className="icon-btn" onClick={() => setShow((s) => !s)}
              aria-label={show ? "Hide password" : "Show password"}>
        {show ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}