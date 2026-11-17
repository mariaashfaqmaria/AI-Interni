// frontend/src/components/AddItemModal.jsx

import { useState } from "react";
import Modal from "./Modal";
import { todayIso, to12h } from "../utils";

export default function AddItemModal({ title, kind, defaultDate, onSave, onClose }) {
  const [v, setV] = useState({
    title: "", priority: "Medium", due: todayIso(),
    date: defaultDate || todayIso(), time: "09:00", duration: "1 hr",
  });
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    if (!v.title.trim()) return;
    onSave(
      kind === "task"
        ? { title: v.title.trim(), priority: v.priority, due: v.due }
        : { title: v.title.trim(), date: v.date, time: to12h(v.time), duration: v.duration }
    );
  };

  return (
    <Modal title={title} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>Title
          <input autoFocus required value={v.title} onChange={set("title")} placeholder="e.g. Build data pipeline" />
        </label>
        {kind === "task" ? (
          <>
            <label>Priority
              <select value={v.priority} onChange={set("priority")}>
                <option>High</option><option>Medium</option><option>Low</option>
              </select>
            </label>
            <label>Due date<input type="date" value={v.due} onChange={set("due")} /></label>
          </>
        ) : (
          <>
            <label>Date<input type="date" value={v.date} onChange={set("date")} /></label>
            <label>Time<input type="time" value={v.time} onChange={set("time")} /></label>
            <label>Duration<input value={v.duration} onChange={set("duration")} /></label>
          </>
        )}
        <div className="form-actions">
          <button type="button" className="btn soft" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn">Save</button>
        </div>
      </form>
    </Modal>
  );
}