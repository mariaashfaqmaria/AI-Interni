// frontend/src/pages/Tasks.jsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import api, { errorMessage } from "../api";
import { isOverdue, showDue } from "../utils";
import AddItemModal from "../components/AddItemModal";
import { useToast } from "../components/Toast";

const COLUMNS = [
  { id: "todo", title: "To do" },
  { id: "progress", title: "In progress" },
  { id: "done", title: "Done" },
];

export default function Tasks({ phase = "Project tasks" }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [over, setOver] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [params] = useSearchParams();
  const toast = useToast();
  const q = (params.get("q") || "").toLowerCase();

  useEffect(() => {
    api.get("/tasks")
      .then(({ data }) => setTasks(data))
      .catch((e) => toast(errorMessage(e, "Could not load tasks."), "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  // Optimistic: move the card right away, roll back if the API fails
  const update = async (id, changes) => {
    const previous = tasks;
    setTasks((old) => old.map((t) => (t.id === id ? { ...t, ...changes } : t)));
    try {
      const { data } = await api.patch(`/tasks/${id}`, changes);
      setTasks((old) => old.map((t) => (t.id === id ? data : t)));
    } catch (e) {
      setTasks(previous);
      toast(errorMessage(e, "Could not update task."), "error");
    }
  };

  const drop = (e, status) => {
    e.preventDefault();
    const id = Number(e.dataTransfer.getData("id"));
    const task = tasks.find((t) => t.id === id);
    setOver(null);
    if (task && task.status !== status) update(id, { status });
  };

  const add = async (values) => {
    try {
      const { data } = await api.post("/tasks", { ...values, status: "todo" });
      setTasks((old) => [...old, data]);
      setShowAdd(false);
      toast("Task added");
    } catch (e) {
      toast(errorMessage(e, "Could not add task."), "error");
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/tasks/${id}`);
      setTasks((old) => old.filter((t) => t.id !== id));
      toast("Task deleted");
    } catch (e) {
      toast(errorMessage(e, "Could not delete task."), "error");
    }
  };

  const nextStatus = (s) => COLUMNS[(COLUMNS.findIndex((c) => c.id === s) + 1) % COLUMNS.length].id;
  const visible = tasks.filter((t) => t.title.toLowerCase().includes(q));
  const done = tasks.filter((t) => t.status === "done").length;
  const pct = tasks.length ? (done / tasks.length) * 100 : 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Tasks</h1>
          <p className="sub">
            Track daily work by status. Tasks come from the generated plan.
            {q && <> Showing results for “{q}”.</>}
          </p>
        </div>
        <button className="btn" onClick={() => setShowAdd(true)}><Plus size={16} /> Add task</button>
      </div>

      <section className="card">
        <div className="phase"><strong>{phase}</strong><span>{done} of {tasks.length} done</span></div>
        <div className="bar" style={{ marginTop: 16 }}><i style={{ width: `${pct}%` }} /></div>
      </section>

      <div className="board">
        {COLUMNS.map((c) => {
          const items = visible.filter((t) => t.status === c.id);
          return (
            <div key={c.id} className={`col ${over === c.id ? "over" : ""}`}
                 onDragOver={(e) => { e.preventDefault(); setOver(c.id); }}
                 onDragLeave={() => setOver(null)} onDrop={(e) => drop(e, c.id)}>
              <h3>{c.title} <span className="count">{items.length}</span></h3>
              {loading && <div className="skeleton" style={{ height: 70 }} />}
              {!loading && items.length === 0 && <p className="empty">Drop a task here</p>}
              {items.map((t) => (
                <div key={t.id} draggable
                     className={`task p-${String(t.priority).toLowerCase()} ${isOverdue(t.due, t.status) ? "overdue" : ""}`}
                     onDragStart={(e) => e.dataTransfer.setData("id", String(t.id))}>
                  <p>{t.title}</p>
                  <div className="meta">
                    <span className={`badge b-${String(t.priority).toLowerCase()}`}>{t.priority}</span>
                    <span>{showDue(t.due)}{isOverdue(t.due, t.status) && " · overdue"}</span>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <button className="btn soft" onClick={() => update(t.id, { status: nextStatus(t.status) })}>Move</button>
                    <button className="btn soft" onClick={() => remove(t.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {showAdd && <AddItemModal title="Add task" kind="task" onSave={add} onClose={() => setShowAdd(false)} />}
    </>
  );
}