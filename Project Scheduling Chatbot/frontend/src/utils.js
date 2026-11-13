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