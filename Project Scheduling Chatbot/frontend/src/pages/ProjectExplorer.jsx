// frontend/src/pages/ProjectExplorer.jsx
import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const C = {
  primary: "#5b3fd6",
  soft: "#ebe8fb",
  text: "#1c1c45",
  muted: "#6b6b8a",
  border: "#e4e2f5",
};

const FILTERS = [
  "All",
  "Healthcare",
  "Education",
  "Finance",
  "Agriculture",
  "E-commerce",
  "Transportation",
  "Real Estate",
  "Entertainment",
  "Cybersecurity",
  "Environment",
  "Beginner",
  "Manufacturing",
  "Tourism",
  "Sports",
  "Food Service",
  "Government",
  "Energy",
];

const chip = (active) => ({
  padding: "8px 18px",
  borderRadius: 999,
  border: 0,
  cursor: "pointer",
  fontSize: 15,
  background: active ? C.primary : C.soft,
  color: active ? "#fff" : C.primary,
});

const tag = {
  padding: "8px 16px",
  borderRadius: 999,
  background: C.soft,
  color: C.primary,
  fontSize: 15,
};

export default function ProjectExplorer() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const [page, setPage] = useState(1);

  const [data, setData] = useState({
    items: [],
    total: 0,
    pages: 1,
  });

  const [compare, setCompare] = useState([]);
  const [selected, setSelected] = useState(null);
  const [details, setDetails] = useState(null);
  const [comparison, setComparison] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;

    setLoading(true);
    setError("");

    api
      .get("/projects", {
        params: {
          q: query,
          tag: filter === "All" ? "" : filter,
          page,
          page_size: 100,
        },
      })
      .then(({ data }) => {
        if (alive) {
          setData(data);
        }
      })
      .catch((e) => {
        if (alive) {
          setError(errorMessage(e, "Could not load projects."));
        }
      })
      .finally(() => {
        if (alive) {
          setLoading(false);
        }
      });

    return () => {
      alive = false;
    };
  }, [query, filter, page]);

  const toggleCompare = (id) => {
    setCompare((old) =>
      old.includes(id)
        ? old.filter((x) => x !== id)
        : [...old, id]
    );
  };

  const selectProject = async (project) => {
    setSelected(project.id);
    setError("");

    try {
      await api.post(`/projects/${project.id}/select`);
    } catch (e) {
      setError(
        errorMessage(e, "Could not select this project.")
      );
    }
  };

  const showDetails = async (project) => {
    setError("");

    try {
      const { data } = await api.get(`/projects/${project.id}`);
      setDetails(data);
    } catch (e) {
      setError(
        errorMessage(e, "Could not load project details.")
      );
    }
  };

  const compareProjects = async () => {
    if (compare.length < 2) return;

    setError("");

    try {
      const { data } = await api.get("/projects/compare", {
        params: {
          ids: compare.join(","),
        },
      });

      setComparison(data);
    } catch (e) {
      setError(
        errorMessage(e, "Could not compare projects.")
      );
    }
  };

  return (
    <div
      style={{
        padding: "32px 52px",
        color: C.text,
        minHeight: "100vh",
        background: "#f5f5fb",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 34 }}>
            Project Explorer
          </h1>

          <p style={{ margin: "8px 0 0", color: C.muted }}>
            Browse projects from the document. Filter, compare and
            select.
          </p>
        </div>

        <button
          style={{
            ...chip(false),
            borderRadius: 14,
            padding: "14px 28px",
            fontSize: 16,
          }}
          disabled={compare.length < 2}
          onClick={compareProjects}
        >
          Compare ({compare.length})
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          marginTop: 24,
          flexWrap: "wrap",
        }}
      >
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
          placeholder="Search projects..."
          style={{
            width: 480,
            maxWidth: "100%",
            padding: "18px 22px",
            borderRadius: 14,
            border: `1px solid ${C.border}`,
            fontSize: 16,
            outline: "none",
            background: "#fff",
          }}
        />

        {FILTERS.map((f) => (
          <button
            key={f}
            style={chip(filter === f)}
            onClick={() => {
              setFilter(f);
              setPage(1);
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {details && (
        <section
          style={{
            background: "#fff",
            border: `1px solid ${C.border}`,
            borderRadius: 16,
            padding: 20,
            marginTop: 20,
          }}
        >
          <button
            onClick={() => setDetails(null)}
            style={{ float: "right" }}
          >
            Close
          </button>

          <h2>{details.name}</h2>
          <p>{details.description}</p>

          <p>
            Estimated {details.days} days · {
              details.tags?.includes("source:document-file")
                ? "Source: PDF document"
                : details.tags?.includes("source:seeds-file")
                  ? "Source: seeds file"
                  : "Custom project"
            }
          </p>
        </section>
      )}

      {comparison.length > 0 && (
        <section
          style={{
            background: "#fff",
            border: `1px solid ${C.border}`,
            borderRadius: 16,
            padding: 20,
            marginTop: 20,
          }}
        >
          <button
            onClick={() => setComparison([])}
            style={{ float: "right" }}
          >
            Close comparison
          </button>

          <h2>Project comparison</h2>

          {comparison.map((project) => (
            <p key={project.id}>
              <b>{project.name}</b> — {project.days} days —{" "}
              {project.tags.join(", ")}
            </p>
          ))}
        </section>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(260px, 1fr))",
          gap: 28,
          marginTop: 24,
          maxWidth: 1380,
        }}
      >
        {data.items.map((project) => (
          <div
            key={project.id}
            style={{
              background: "#fff",
              border: `${
                selected === project.id ? 2 : 1
              }px solid ${
                selected === project.id ? C.primary : C.border
              }`,
              borderRadius: 20,
              padding: 26,
            }}
          >
            <div style={{ color: C.muted, fontSize: 15 }}>
              Project {String(project.id).padStart(2, "0")}
            </div>

            <div
              style={{
                fontWeight: 700,
                fontSize: 20,
                margin: "10px 0 14px",
              }}
            >
              {project.name}
            </div>

            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
              }}
            >
              {project.tags.filter((item) => !item.startsWith("source:")).map((item) => (
                <span key={item} style={tag}>
                  {item}
                </span>
              ))}
            </div>

            <div
              style={{
                color: C.muted,
                margin: "26px 0 20px",
                fontSize: 15,
              }}
            >
              Estimated {project.days} days · {
                project.tags?.includes("source:document-file")
                  ? "Source: PDF document"
                  : project.tags?.includes("source:seeds-file")
                    ? "Source: seeds file"
                    : "Custom project"
              }
            </div>

            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <button
                onClick={() => selectProject(project)}
                style={{
                  background: C.primary,
                  color: "#fff",
                  border: 0,
                  borderRadius: 12,
                  padding: "14px 20px",
                  fontSize: 16,
                  cursor: "pointer",
                }}
              >
                Select
              </button>

              <button
                onClick={() => showDetails(project)}
                style={{
                  background: C.soft,
                  color: C.primary,
                  border: 0,
                  borderRadius: 12,
                  padding: "14px 20px",
                  fontSize: 16,
                  cursor: "pointer",
                }}
              >
                Details
              </button>

              <label
                style={{
                  marginLeft: "auto",
                  fontSize: 14,
                  color: C.muted,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={compare.includes(project.id)}
                  onChange={() => toggleCompare(project.id)}
                  style={{ marginRight: 6 }}
                />
                Compare
              </label>
            </div>
          </div>
        ))}
      </div>

      {!loading && !data.items.length && (
        <p style={{ color: C.muted, marginTop: 24 }}>
          No projects match your search.
        </p>
      )}

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          color: C.muted,
          marginTop: 24,
          fontSize: 15,
        }}
      >
        Showing {data.items.length} of {data.total} · Page{" "}
        {data.page || page} of {data.pages || 1}

        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>

        <button
          disabled={page >= (data.pages || 1)}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>

        {loading && "Loading…"}
      </div>
    </div>
  );
}
