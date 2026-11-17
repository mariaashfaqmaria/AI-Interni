// frontend/src/pages/Schedule.jsx
import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import api, { errorMessage } from "../api";
import { fmtDay, fromIso, iso } from "../utils";
import AddItemModal from "../components/AddItemModal";
import { useToast } from "../components/Toast";

const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function Schedule() {
  const [tasks, setTasks] = useState([]);
  const [view, setView] = useState("Month");
  const [cursor, setCursor] = useState(new Date());
  const [selected, setSelected] = useState(iso(new Date()));
  const [showAdd, setShowAdd] = useState(false);
  const toast = useToast();

  useEffect(() => {
    api.get("/schedule")
      .then(({ data }) => setTasks(data))
      .catch((e) => toast(errorMessage(e, "Could not load schedule."), "error"));
  }, [toast]);

  const byDate = tasks.reduce((m, t) => { (m[t.date] ||= []).push(t); return m; }, {});
  const dayTasks = byDate[selected] || [];
  const todayKey = iso(new Date());
  const y = cursor.getFullYear();
  const m = cursor.getMonth();
  const lead = new Date(y, m, 1).getDay();
  const count = new Date(y, m + 1, 0).getDate();
  const monthCells = [...Array(lead).fill(null), ...Array.from({ length: count }, (_, i) => i + 1)];
  const cells = [...monthCells, ...Array(Math.max(0, 42 - monthCells.length)).fill(null)];
  const move = (n) => setCursor(new Date(y, m + n, 1));
  const goToday = () => { const now = new Date(); setCursor(now); setSelected(iso(now)); };

  const add = async (values) => {
    try {
      const { data } = await api.post("/schedule", values);
      setTasks((old) => [...old, data]);
      setSelected(values.date);
      setShowAdd(false);
      toast("Schedule item added");
    } catch (e) {
      toast(errorMessage(e, "Could not add schedule item."), "error");
    }
  };

  const exportIcs = async () => {
    try {
      const response = await api.get("/schedule/export.ics", { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "project-schedule.ics";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast(errorMessage(e, "Could not export schedule."), "error");
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/schedule/${id}`);
      setTasks((old) => old.filter((t) => t.id !== id));
      toast("Schedule item removed");
    } catch (e) {
      toast(errorMessage(e, "Could not delete schedule item."), "error");
    }
  };

  const weekDays = () => {
    const d = fromIso(selected);
    d.setDate(d.getDate() - d.getDay());
    return Array.from({ length: 7 }, (_, i) => { const x = new Date(d); x.setDate(d.getDate() + i); return iso(x); });
  };
  const rows = view === "Week" ? weekDays() : Object.keys(byDate).sort();

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Schedule</h1>
          <p className="sub">Your plan days on a calendar. Click a day to see its tasks.</p>
        </div>
        <div className="seg">
          {["Month", "Week", "List"].map((v) => (
            <button key={v} className={view === v ? "on" : ""} onClick={() => setView(v)}>{v}</button>
          ))}
        </div>
      </div>

      <div className="sched">
        <section className="card">
          {view === "Month" ? (
            <>
              <div className="cal-head">
                <h2>{cursor.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}</h2>
                <span>
                  <button className="btn soft" onClick={goToday}>Today</button>{" "}
                  <button className="btn soft" onClick={() => move(-1)} aria-label="Previous month">‹</button>{" "}
                  <button className="btn soft" onClick={() => move(1)} aria-label="Next month">›</button>
                </span>
              </div>
              <div className="grid">
                {DOW.map((d) => <div key={d} className="dow">{d}</div>)}
                {cells.map((n, i) => {
                  if (!n) return <div key={i} className="day blank" />;
                  const key = iso(new Date(y, m, n));
                  const list = byDate[key] || [];
                  return (
                    <button key={i} onClick={() => setSelected(key)}
                            className={`day ${list.length ? "has" : ""} ${key === selected ? "sel" : ""} ${key === todayKey ? "today" : ""}`}>
                      <span className="day-num">{n}</span>
                      {list.length > 0 && <span className="day-badge">{list.length}</span>}
                      {list.slice(0, 2).map((t) => <span key={t.id} className="day-preview">{t.title}</span>)}
                      {list.length > 2 && <span className="day-more">+{list.length - 2} more</span>}
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <>
              <div className="cal-head">
                <h2>{view === "Week" ? "Week of " + fromIso(selected).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "All planned days"}</h2>
                {view === "Week" && (
                  <span className="calendar-nav">
                    <button className="btn soft" onClick={() => {
                      const previous = fromIso(selected);
                      previous.setDate(previous.getDate() - 7);
                      setSelected(iso(previous));
                      setCursor(previous);
                    }} aria-label="Previous week">‹</button>
                    <button className="btn soft" onClick={goToday}>Today</button>
                    <button className="btn soft" onClick={() => {
                      const next = fromIso(selected);
                      next.setDate(next.getDate() + 7);
                      setSelected(iso(next));
                      setCursor(next);
                    }} aria-label="Next week">›</button>
                  </span>
                )}
              </div>
              {view === "Week" ? (
                <div className="week-calendar-grid">
                  {rows.map((d) => {
                    const date = fromIso(d);
                    const list = byDate[d] || [];
                    return (
                      <button
                        type="button"
                        className={`week-day ${d === selected ? "selected" : ""} ${d === todayKey ? "today" : ""}`}
                        key={d}
                        onClick={() => setSelected(d)}
                      >
                        <span className="week-day-name">{date.toLocaleDateString("en-GB", { weekday: "short" })}</span>
                        <span className="week-day-number">{date.getDate()}</span>
                        <span className="week-day-events">
                          {list.map((task) => (
                            <span className="week-event" key={task.id}>
                              <b>{task.time || "All day"}</b>
                              <span>{task.title}</span>
                            </span>
                          ))}
                          {!list.length && <span className="week-empty">No events</span>}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="schedule-list">
                  {rows.map((d) => (
                    <button type="button" className="list-row" key={d} onClick={() => setSelected(d)}>
                      <b>{fmtDay(d)}</b>
                      <div>
                        {(byDate[d] || []).map((t) => <div key={t.id}>{t.title} <span className="sub">{t.time}</span></div>)}
                        {!byDate[d] && <span className="sub">No tasks</span>}
                      </div>
                    </button>
                  ))}
                  {!rows.length && <p className="empty">No scheduled items yet.</p>}
                </div>
              )}
            </>
          )}
        </section>

        <aside className="side">
          <h2>{fmtDay(selected)}</h2>
          {dayTasks.length === 0 && <p className="empty">No tasks on this day.</p>}
          {dayTasks.map((t) => (
            <div className="card task-card" key={t.id}>
              <strong>{t.title}</strong>
              <span>{t.time} · {t.duration}</span>
              <button className="btn soft" onClick={() => remove(t.id)}>Remove</button>
            </div>
          ))}
          <button className="btn soft block" style={{ marginBottom: 14 }} onClick={() => setShowAdd(true)}>
            <Plus size={16} /> Add task
          </button>
          <button className="btn soft block" onClick={exportIcs}>Export calendar file</button>
        </aside>
      </div>

      {showAdd && <AddItemModal title="Add schedule item" kind="schedule" defaultDate={selected}
                                onSave={add} onClose={() => setShowAdd(false)} />}
    </>
  );
}