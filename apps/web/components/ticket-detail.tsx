"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { formatDateTime, formatLabel, getTicket } from "@/lib/api";
import type { TicketDetail } from "@/lib/types";

type DetailState =
  | { kind: "loading" }
  | { kind: "ready"; ticket: TicketDetail }
  | { kind: "not_found" }
  | { kind: "error"; message: string };

export function TicketDetailView({ ticketId }: { ticketId: string }) {
  const [state, setState] = useState<DetailState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getTicket(ticketId, controller.signal)
      .then((ticket) => setState({ kind: "ready", ticket }))
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
            error instanceof Error ? error.message : "Unable to load ticket",
        });
      });
    return () => controller.abort();
  }, [ticketId]);

  if (state.kind === "loading") {
    return (
      <div className="page-content catalog-loading">
        Loading Ticket #{ticketId}…
      </div>
    );
  }
  if (state.kind === "not_found") {
    return (
      <div className="page-content detail-message">
        <p className="section-kicker">Not found</p>
        <h1>Ticket #{ticketId} does not exist.</h1>
        <Link href="/tickets">Return to tickets</Link>
      </div>
    );
  }
  if (state.kind === "error") {
    return <div className="page-content catalog-error">{state.message}</div>;
  }

  const ticket = state.ticket;
  return (
    <div className="page-content detail-page">
      <Link className="back-link" href="/tickets">
        ← All tickets
      </Link>
      <header className="detail-header">
        <div>
          <div className="detail-eyebrow">
            <span>Ticket #{ticket.ticket_id}</span>
            <span className={`priority-label priority-${ticket.priority}`}>
              {ticket.priority}
            </span>
          </div>
          <h1>{ticket.title}</h1>
          <p>{ticket.description}</p>
        </div>
        <div className="detail-statuses">
          <span className={`data-badge status-${ticket.status}`}>
            {formatLabel(ticket.status)}
          </span>
          <span className={`sla-label sla-${ticket.sla_state}`}>
            {formatLabel(ticket.sla_state)}
          </span>
        </div>
      </header>

      {ticket.status !== "completed" && ticket.status !== "cancelled" && (
        <div className="detail-action-row">
          <Link
            className="primary-action"
            href={`/dispatch?ticket=${encodeURIComponent(ticket.ticket_id)}`}
          >
            Evaluate dispatch candidates →
          </Link>
          <span>Read-only policy evaluation; no assignment is changed.</span>
        </div>
      )}

      <div className="detail-grid">
        <section className="panel detail-panel">
          <p className="panel-kicker">Service context</p>
          <dl className="definition-grid">
            <div>
              <dt>Customer</dt>
              <dd>{ticket.customer_name}</dd>
            </div>
            <div>
              <dt>Site</dt>
              <dd>{ticket.site.name}</dd>
            </div>
            <div>
              <dt>Equipment</dt>
              <dd>{formatLabel(ticket.equipment_type)}</dd>
            </div>
            <div>
              <dt>Asset ID</dt>
              <dd>{ticket.equipment_id}</dd>
            </div>
            <div>
              <dt>Required certification</dt>
              <dd>{ticket.required_certification_ids.join(", ")}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatDateTime(ticket.created_at)} UTC</dd>
            </div>
          </dl>
        </section>

        <section className="panel detail-panel">
          <p className="panel-kicker">Site</p>
          <h2>{ticket.site.name}</h2>
          <address>
            {ticket.site.address}
            <br />
            {ticket.site.city}, {ticket.site.state} {ticket.site.postal_code}
          </address>
          <dl className="deadline-list">
            <div>
              <dt>Response due</dt>
              <dd>{formatDateTime(ticket.response_due_at)} UTC</dd>
            </div>
            <div>
              <dt>Resolution due</dt>
              <dd>{formatDateTime(ticket.resolution_due_at)} UTC</dd>
            </div>
          </dl>
          {ticket.site.geocode_status !== "valid" && (
            <p className="warning-note">
              This site has an invalid address and requires review.
            </p>
          )}
          {ticket.site.routing_mode === "simulate_failure" && (
            <p className="warning-note">
              This site is configured to exercise route API failure handling.
            </p>
          )}
        </section>
      </div>

      <section className="panel assignments-panel">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Work history</p>
            <h2>Assignments</h2>
          </div>
          <span className="phase-badge">{ticket.assignments.length}</span>
        </div>
        {ticket.assignments.length === 0 ? (
          <p className="catalog-empty compact">
            No technician is currently assigned.
          </p>
        ) : (
          <div className="assignment-list">
            {ticket.assignments.map((assignment) => (
              <Link
                href={`/technicians/${assignment.technician_id}`}
                key={assignment.assignment_id}
              >
                <span>
                  <strong>{assignment.technician_name}</strong>
                  <small>{formatLabel(assignment.status)}</small>
                </span>
                <span className="mono-cell">
                  {formatDateTime(assignment.scheduled_start)} –{" "}
                  {formatDateTime(assignment.scheduled_end)} UTC
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
