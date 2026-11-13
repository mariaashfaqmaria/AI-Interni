// frontend/src/pages/ProjectPlanner.jsx
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import api, { errorMessage } from "../api";
import { iso } from "../utils";

const STEPS = [
  {
    key: "research",
    title: "Research",
    text: "Retrieve context from the document",
  },
  {
    key: "plan",
    title: "Project plan",
    text: "Objective, architecture, milestones",
  },
  {
    key: "tasks",
    title: "Daily tasks",
    text: "Beginner-friendly daily tasks",
  },
  {
    key: "checklist",
    title: "Checklist",
    text: "Checkbox list grouped by phase",
  },
];

const LABEL = {
  waiting: "Waiting",
  progress: "In progress",
  done: "Done",
};

const INITIAL_PROGRESS = {
  research: 0,
  plan: 0,
  tasks: 0,
  checklist: 0,
};

export default function ProjectPlanner() {
  const location = useLocation();

  const [projects, setProjects] = useState([]);

  const [form, setForm] = useState({
    project: location.state?.project || "",
    start: iso(new Date()),
    days: 14,
    hours: 2,
    beginner: true,
    weekends_off: true,
  });

  const [progress, setProgress] = useState(INITIAL_PROGRESS);
  const [plan, setPlan] = useState(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load available projects
  useEffect(() => {
    api
      .get("/projects", { params: { page: 1, page_size: 100 } })
      .then(({ data }) => {
        const items = data.items || [];

        setProjects(items);

        setForm((old) => ({
          ...old,
          project: old.project || items[0]?.name || "",
        }));
      })
      .catch((e) => {
        setError(errorMessage(e, "Could not load projects."));
      });
  }, []);

  // Update form fields
  const set = (key) => (e) => {
    setForm((old) => ({
      ...old,
      [key]: e.target.value,
    }));
  };

  // Toggle boolean settings
  const toggle = (key) => {
    setForm((old) => ({
      ...old,
      [key]: !old[key],
    }));
  };

  // Determine progress status
  const status = (value) => {
    if (value >= 100) return "done";
    if (value > 0) return "progress";
    return "waiting";
  };

  // Generate project plan using SSE streaming
  const generate = async () => {
    if (!form.project) {
      setError("Please select a project.");
      return;
    }

    setLoading(true);
    setError("");
    setSaved(false);
    setPlan(null);
    setProgress({ ...INITIAL_PROGRESS });

    try {
      const response = await fetch("/api/plans/generate/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          project: form.project,
          start: form.start,
          days: Number(form.days),
          hours: Number(form.hours),
          beginner: form.beginner,
          weekends_off: form.weekends_off,
        }),
      });

      if (!response.ok) {
        let detail = "Plan generation failed.";

        try {
          const data = await response.json();
          detail = data.detail || detail;
        } catch {
          // Keep the default error message
        }

        throw new Error(detail);
      }

      if (!response.body) {
        throw new Error(
          "Streaming response is not available in this browser."
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let completed = false;

      // Process one SSE event
      const processBlock = (block) => {
        const line = block
          .split(/\r?\n/)
          .find((item) => item.startsWith("data:"));

        if (!line) return;

        const event = JSON.parse(line.slice(5).trim());

        if (event.step === "error") {
          throw new Error(
            event.detail || "Plan generation failed."
          );
        }

        if (event.step === "complete") {
          setPlan(event.plan);

          setProgress({
            research: 100,
            plan: 100,
            tasks: 100,
            checklist: 100,
          });

          completed = true;
          return;
        }

        // The backend uses "outline" for the project plan step.
        const progressKey =
          event.step === "outline" ? "plan" : event.step;

        if (
          Object.prototype.hasOwnProperty.call(
            INITIAL_PROGRESS,
            progressKey
          )
        ) {
          setProgress((old) => ({
            ...old,
            [progressKey]: 100,
          }));
        }
      };

      // Read the streaming response
      while (!completed) {
        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by blank lines
        const blocks = buffer.split(/\r?\n\r?\n/);

        buffer = blocks.pop() || "";

        for (const block of blocks) {
          processBlock(block);

          if (completed) break;
        }
      }

      // Process any remaining data
      if (!completed) {
        buffer += decoder.decode();

        if (buffer.trim()) {
          processBlock(buffer);
        }
      }

      if (!completed) {
        throw new Error(
          "The planner stream ended before a plan was returned."
        );
      }
    } catch (e) {
      setError(e.message || errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  // Save generated plan to schedule
  const save = async () => {
    if (!plan?.id) return;

    setError("");

    try {
      await api.post(`/plans/${plan.id}/save-to-schedule`);

      setSaved(true);
    } catch (e) {
      setError(
        errorMessage(e, "Could not save the plan to your schedule.")
      );
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Project Planner</h1>
          <p className="sub">
            Turn a selected project into a plan, daily tasks and a
            checklist.
          </p>
        </div>

        <button
          className="btn"
          onClick={generate}
          disabled={loading}
        >
          {loading ? "Generating..." : "Generate plan"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="planner">
        {/* Plan Settings */}
        <section className="card">
          <h2>Plan settings</h2>

          <label className="label">Project</label>

          <select
            className="input"
            value={form.project}
            onChange={set("project")}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>

          <label className="label">Start date</label>

          <input
            className="input"
            type="date"
            value={form.start}
            onChange={set("start")}
          />

          <label className="label">Duration (days)</label>

          <input
            className="input"
            type="number"
            min="1"
            max="60"
            value={form.days}
            onChange={(e) =>
              setForm((old) => ({
                ...old,
                days: Math.max(
                  1,
                  Math.min(60, Number(e.target.value) || 1)
                ),
              }))
            }
          />

          <label className="label">Hours per day</label>

          <input
            className="input"
            type="number"
            min="1"
            max="12"
            value={form.hours}
            onChange={(e) =>
              setForm((old) => ({
                ...old,
                hours: Math.max(
                  1,
                  Math.min(12, Number(e.target.value) || 1)
                ),
              }))
            }
          />

          <button
            className={`chip ${form.beginner ? "" : "off"}`}
            onClick={() => toggle("beginner")}
            type="button"
          >
            Beginner
          </button>

          <button
            className={`chip ${form.weekends_off ? "" : "off"}`}
            onClick={() => toggle("weekends_off")}
            type="button"
          >
            Weekends off
          </button>

          <button
            className="btn block"
            style={{ marginTop: 28 }}
            onClick={generate}
            disabled={loading}
          >
            {loading ? "Generating..." : "Generate plan"}
          </button>
        </section>

        {/* Generation Progress */}
        <section>
          <h2>Generation progress</h2>

          <div className="stack">
            {STEPS.map((step) => {
              const currentStatus = status(progress[step.key]);

              return (
                <div className="card step" key={step.key}>
                  <div className="step-top">
                    <strong>{step.title}</strong>

                    <span className={`badge b-${currentStatus}`}>
                      {LABEL[currentStatus]}
                    </span>
                  </div>

                  <p>{step.text}</p>

                  <div className="bar">
                    <i
                      style={{
                        width: `${progress[step.key]}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Plan Preview */}
        <section
          className="card preview"
          style={{ minHeight: 440 }}
        >
          <h2>Plan preview</h2>

          {plan ? (
            <>
              <h3>{plan.project}</h3>

              <p>{plan.objective}</p>

              <p>
                Total: {plan.total_hours} hours · {plan.days} days
              </p>

              <h3>Architecture</h3>

              <ul>
                {plan.architecture?.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>

              <h3>Daily tasks</h3>

              <div
                style={{
                  maxHeight: 220,
                  overflowY: "auto",
                }}
              >
                {plan.tasks?.map((task, index) => (
                  <p key={index}>
                    <b>
                      {task.date} · {task.time}
                    </b>{" "}
                    — {task.title} ({task.duration})
                  </p>
                ))}
              </div>

              <button
                className="btn block"
                onClick={save}
                disabled={saved}
              >
                {saved ? "Saved to schedule" : "Save to schedule"}
              </button>
            </>
          ) : (
            <>
              <p>Your generated plan will appear here.</p>

              <button className="btn soft block" disabled>
                Edit plan
              </button>

              <button className="btn block" disabled>
                Save to schedule
              </button>
            </>
          )}
        </section>
      </div>
    </>
  );
}
