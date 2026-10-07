"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { formatDateTime, formatLabel, getTickets } from "@/lib/api";
import type {
  Paginated,
  TicketPriority,
  TicketStatus,
  TicketSummary,
} from "@/lib/types";

type ViewState =
  | { kind: "loading" }
  | { kind: "ready"; data: Paginated<TicketSummary> }
  | { kind: "error"; message: string };

export default function TicketsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<TicketStatus | "">("");
  const [priority, setPriority] = useState<TicketPriority | "">("");
  const [state, setState] = useState<ViewState>({ kind: "loading" });

  const query = useMemo(() => {
    const params = new URLSearchParams({ limit: "100" });
    if (search.trim()) params.set("query", search.trim());
    if (status) params.set("status", status);
    if (priority) params.set("priority", priority);
    return params;
  }, [priority, search, status]);

  useEffect(() => {
    const controller = new AbortController();
    getTickets(query, controller.signal)
      .then((data) => setState({ kind: "ready", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setState({
          kind: "error",
          message:
            error instanceof Error ? error.message : "Unable to load tickets",
        });
      });
    return () => controller.abort();
  }, [query]);

  const tickets = state.kind === "ready" ? state.data.items : [];

  return (
    <div className="page-content catalog-page">
      <header className="catalog-header">
        <div>
          <p className="section-kicker">Service demand</p>
          <h1>Tickets</h1>
          <p>Browse current and historical work across all customer sites.</p>
        </div>
        <div className="record-count" aria-live="polite">
          <strong>{state.kind === "ready" ? state.data.total : "—"}</strong>
          <span>matching records</span>
        </div>
      </header>

      <section className="filter-bar" aria-label="Ticket filters">
        <label className="search-field">
          <span>Search tickets</span>
          <input
            onChange={(event) => setSearch(event.target.value)}
            placeholder="ID, equipment, or issue"
            type="search"
            value={search}
          />
        </label>
        <label>
          <span>Status</span>
          <select
            onChange={(event) =>
              setStatus(event.target.value as TicketStatus | "")
            }
            value={status}
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="assigned">Assigned</option>
            <option value="in_progress">In progress</option>
            <option value="on_hold">On hold</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <label>
          <span>Priority</span>
          <select
            onChange={(event) =>
              setPriority(event.target.value as TicketPriority | "")
            }
            value={priority}
          >
            <option value="">All priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
      </section>

      {state.kind === "loading" && (
        <CatalogLoading label="Loading service tickets" />
      )}
      {state.kind === "error" && <CatalogError message={state.message} />}
      {state.kind === "ready" && tickets.length === 0 && (
        <div className="catalog-empty">No tickets match these filters.</div>
      )}
      {tickets.length > 0 && (
        <div className="ticket-table-wrap">
          <table className="ticket-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Customer / site</th>
                <th>Status</th>
                <th>SLA</th>
                <th>Assigned</th>
                <th>Resolution due</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.ticket_id}>
                  <td>
                    <Link
                      className="record-link"
                      href={`/tickets/${ticket.ticket_id}`}
                    >
                      <span>#{ticket.ticket_id}</span>
                      <strong>{ticket.title}</strong>
                      <small>{formatLabel(ticket.equipment_type)}</small>
                    </Link>
                  </td>
                  <td>
                    <strong>{ticket.customer_name}</strong>
                    <small>
                      {ticket.site_name} · {ticket.city}, {ticket.state}
                    </small>
                  </td>
                  <td>
                    <span className={`data-badge status-${ticket.status}`}>
                      {formatLabel(ticket.status)}
                    </span>
                    <span
                      className={`priority-label priority-${ticket.priority}`}
                    >
                      {ticket.priority}
                    </span>
                  </td>
                  <td>
                    <span className={`sla-label sla-${ticket.sla_state}`}>
                      {formatLabel(ticket.sla_state)}
                    </span>
                  </td>
                  <td>
                    {ticket.assigned_technician_name ?? (
                      <span className="muted">Unassigned</span>
                    )}
                  </td>
                  <td className="mono-cell">
                    {formatDateTime(ticket.resolution_due_at)} UTC
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function CatalogLoading({ label }: { label: string }) {
  return (
    <div className="catalog-loading" role="status">
      <span /> {label}…
    </div>
  );
}

function CatalogError({ message }: { message: string }) {
  return (
    <div className="catalog-error" role="alert">
      <strong>Catalog unavailable</strong>
      <span>{message}. Confirm the API is running on port 8000.</span>
    </div>
  );
}
