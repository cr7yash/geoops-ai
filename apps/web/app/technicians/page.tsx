"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { formatLabel, getTechnicians } from "@/lib/api";
import type {
  Paginated,
  TechnicianStatus,
  TechnicianSummary,
} from "@/lib/types";

type ViewState =
  | { kind: "loading" }
  | { kind: "ready"; data: Paginated<TechnicianSummary> }
  | { kind: "error"; message: string };

export default function TechniciansPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<TechnicianStatus | "">("");
  const [state, setState] = useState<ViewState>({ kind: "loading" });

  const query = useMemo(() => {
    const params = new URLSearchParams({ limit: "100" });
    if (search.trim()) params.set("query", search.trim());
    if (status) params.set("status", status);
    return params;
  }, [search, status]);

  useEffect(() => {
    const controller = new AbortController();
    getTechnicians(query, controller.signal)
      .then((data) => setState({ kind: "ready", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setState({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Unable to load technicians",
        });
      });
    return () => controller.abort();
  }, [query]);

  const technicians = state.kind === "ready" ? state.data.items : [];

  return (
    <div className="page-content catalog-page">
      <header className="catalog-header">
        <div>
          <p className="section-kicker">Field capacity</p>
          <h1>Technicians</h1>
          <p>
            Review availability, certifications, workload, and service history.
          </p>
        </div>
        <div className="record-count" aria-live="polite">
          <strong>{state.kind === "ready" ? state.data.total : "—"}</strong>
          <span>matching technicians</span>
        </div>
      </header>

      <section
        className="filter-bar technician-filters"
        aria-label="Technician filters"
      >
        <label className="search-field">
          <span>Search technicians</span>
          <input
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Name, city, or skill"
            type="search"
            value={search}
          />
        </label>
        <label>
          <span>Availability</span>
          <select
            onChange={(event) =>
              setStatus(event.target.value as TechnicianStatus | "")
            }
            value={status}
          >
            <option value="">All statuses</option>
            <option value="available">Available</option>
            <option value="dispatched">Dispatched</option>
            <option value="off_duty">Off duty</option>
            <option value="unavailable">Unavailable</option>
          </select>
        </label>
      </section>

      {state.kind === "loading" && (
        <div className="catalog-loading">Loading technicians…</div>
      )}
      {state.kind === "error" && (
        <div className="catalog-error" role="alert">
          {state.message}. Confirm the API is running on port 8000.
        </div>
      )}
      {state.kind === "ready" && technicians.length === 0 && (
        <div className="catalog-empty">No technicians match these filters.</div>
      )}

      <div className="technician-grid">
        {technicians.map((technician) => (
          <Link
            className="technician-card"
            href={`/technicians/${technician.technician_id}`}
            key={technician.technician_id}
          >
            <div className="technician-card-head">
              <span className="avatar" aria-hidden="true">
                {technician.name
                  .split(" ")
                  .map((part) => part[0])
                  .join("")}
              </span>
              <span className={`data-badge tech-${technician.status}`}>
                {formatLabel(technician.status)}
              </span>
            </div>
            <div>
              <p className="record-id">{technician.technician_id}</p>
              <h2>{technician.name}</h2>
              <p>{technician.home_city}</p>
            </div>
            <div className="skill-list">
              {technician.skill_tags.slice(0, 3).map((skill) => (
                <span key={skill}>{formatLabel(skill)}</span>
              ))}
            </div>
            <dl className="technician-stats">
              <div>
                <dt>Rating</dt>
                <dd>{technician.average_rating.toFixed(1)}</dd>
              </div>
              <div>
                <dt>Jobs</dt>
                <dd>{technician.completed_jobs}</dd>
              </div>
              <div>
                <dt>Active</dt>
                <dd>{technician.active_assignment_count}</dd>
              </div>
            </dl>
            {technician.certifications.some(
              (item) => item.validity === "expiring_soon",
            ) && <p className="warning-note">Certification expiring soon</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}
