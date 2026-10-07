"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { formatDateTime, formatLabel, getTechnician } from "@/lib/api";
import type { TechnicianDetail } from "@/lib/types";

type DetailState =
  | { kind: "loading" }
  | { kind: "ready"; technician: TechnicianDetail }
  | { kind: "not_found" }
  | { kind: "error"; message: string };

export function TechnicianDetailView({
  technicianId,
}: {
  technicianId: string;
}) {
  const [state, setState] = useState<DetailState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getTechnician(technicianId, controller.signal)
      .then((technician) => setState({ kind: "ready", technician }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        if (error instanceof Error && error.message === "not_found") {
          setState({ kind: "not_found" });
          return;
        }
        setState({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Unable to load technician",
        });
      });
    return () => controller.abort();
  }, [technicianId]);

  if (state.kind === "loading") {
    return (
      <div className="page-content catalog-loading">
        Loading {technicianId}…
      </div>
    );
  }
  if (state.kind === "not_found") {
    return (
      <div className="page-content detail-message">
        <p className="section-kicker">Not found</p>
        <h1>Technician {technicianId} does not exist.</h1>
        <Link href="/technicians">Return to technicians</Link>
      </div>
    );
  }
  if (state.kind === "error") {
    return <div className="page-content catalog-error">{state.message}</div>;
  }

  const technician = state.technician;
  return (
    <div className="page-content detail-page">
      <Link className="back-link" href="/technicians">
        ← All technicians
      </Link>
      <header className="detail-header technician-detail-header">
        <span className="avatar avatar-large" aria-hidden="true">
          {technician.name
            .split(" ")
            .map((part) => part[0])
            .join("")}
        </span>
        <div>
          <div className="detail-eyebrow">
            <span>{technician.technician_id}</span>
            <span className={`data-badge tech-${technician.status}`}>
              {formatLabel(technician.status)}
            </span>
          </div>
          <h1>{technician.name}</h1>
          <p>{technician.home_city} field operations</p>
        </div>
      </header>

      <div className="detail-grid">
        <section className="panel detail-panel">
          <p className="panel-kicker">Performance</p>
          <dl className="definition-grid">
            <div>
              <dt>Completed jobs</dt>
              <dd>{technician.completed_jobs}</dd>
            </div>
            <div>
              <dt>Average rating</dt>
              <dd>{technician.average_rating.toFixed(1)} / 5</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{technician.email}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>{technician.phone}</dd>
            </div>
          </dl>
          <div className="skill-list detail-skills">
            {technician.skill_tags.map((skill) => (
              <span key={skill}>{formatLabel(skill)}</span>
            ))}
          </div>
        </section>

        <section className="panel detail-panel">
          <p className="panel-kicker">Qualifications</p>
          <div className="certification-list">
            {technician.certifications.map((certification) => (
              <div key={certification.certification_id}>
                <span>
                  <strong>{certification.name}</strong>
                  <small>{certification.certification_id}</small>
                </span>
                <span
                  className={`cert-validity cert-${certification.validity}`}
                >
                  {formatLabel(certification.validity)}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel assignments-panel">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Schedule</p>
            <h2>Assignments</h2>
          </div>
          <span className="phase-badge">{technician.assignments.length}</span>
        </div>
        {technician.assignments.length === 0 ? (
          <p className="catalog-empty compact">
            No assignments in this dataset.
          </p>
        ) : (
          <div className="assignment-list">
            {technician.assignments.map((assignment) => (
              <Link
                href={`/tickets/${assignment.ticket_id}`}
                key={assignment.assignment_id}
              >
                <span>
                  <strong>
                    #{assignment.ticket_id} · {assignment.ticket_title}
                  </strong>
                  <small>{formatLabel(assignment.status)}</small>
                </span>
                <span className="mono-cell">
                  {formatDateTime(assignment.scheduled_start)} UTC
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
