// frontend/src/utils.js
export const iso = (date) => {
  const d = new Date(date);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

export const fromIso = (value) => {
  const [y, m, d] = String(value).split("-").map(Number);
  return new Date(y, m - 1, d);
};

export const fmtDay = (value) => fromIso(value).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
export const fmtShort = (value) => fromIso(value).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

export const todayIso = () => iso(new Date());

export const to12h = (hhmm) => {
  const [h, m] = hhmm.split(":").map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h >= 12 ? "PM" : "AM"}`;
};

const ISO_RE = /^\d{4}-\d{2}-\d{2}$/;
export const showDue = (v) => (ISO_RE.test(v) ? fmtShort(v) : v);
export const isOverdue = (v, status) => ISO_RE.test(v) && v < todayIso() && status !== "done";