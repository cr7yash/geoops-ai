"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  formatDateTime,
  formatLabel,
  getDispatchRecommendation,
  getTickets,
} from "@/lib/api";
import type {
  DispatchCandidate,
  DispatchRecommendation,
  TicketSummary,
} from "@/lib/types";

type CatalogState =
  | { kind: "loading" }
  | { kind: "ready"; tickets: TicketSummary[] }
  | { kind: "error"; message: string };

type RecommendationState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; result: DispatchRecommendation }
  | { kind: "error"; message: string };

export function DispatchWorkbench({
  initialTicketId,
}: {
  initialTicketId?: string;
}) {
  const [catalog, setCatalog] = useState<CatalogState>({ kind: "loading" });
  const [selectedTicketId, setSelectedTicketId] = useState("");
  const [recommendation, setRecommendation] = useState<RecommendationState>({
    kind: "idle",
  });

  useEffect(() => {
    const controller = new AbortController();
    getTickets(new URLSearchParams({ limit: "100" }), controller.signal)
      .then((data) => {
        const dispatchable = data.items.filter(
          (ticket) =>
            ticket.status !== "completed" && ticket.status !== "cancelled",
        );
        setCatalog({ kind: "ready", tickets: dispatchable });
        const requested = dispatchable.find(
          (ticket) => ticket.ticket_id === initialTicketId,
        );
        const defaultTicket =
          requested ??
          dispatchable.find((ticket) => ticket.ticket_id === "184") ??
          dispatchable[0];
        if (defaultTicket) setRecommendation({ kind: "loading" });
        setSelectedTicketId(defaultTicket?.ticket_id ?? "");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setCatalog({
          kind: "error",
          message:
            error instanceof Error ? error.message : "Unable to load tickets",
        });
      });
    return () => controller.abort();
  }, [initialTicketId]);

  useEffect(() => {
    if (!selectedTicketId) return;
    const controller = new AbortController();
    getDispatchRecommendation(selectedTicketId, controller.signal)
      .then((result) => setRecommendation({ kind: "ready", result }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setRecommendation({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Unable to evaluate dispatch candidates",
        });
      });
    return () => controller.abort();
  }, [selectedTicketId]);

  const selectedTicket =
    catalog.kind === "ready"
      ? catalog.tickets.find((ticket) => ticket.ticket_id === selectedTicketId)
      : undefined;

  return (
    <div className="page-content dispatch-page">
      <header className="dispatch-header">
        <div>
          <p className="section-kicker">Deterministic policy</p>
          <h1>Dispatch recommendations</h1>
          <p>
            Hard eligibility rules run before ranking. Every outcome exposes the
            evidence used to include or reject a technician.
          </p>
        </div>
        <span className="read-only-badge">Read only</span>
      </header>

      <section className="dispatch-control panel" aria-label="Ticket selection">
        <label>
          <span>Service ticket</span>
          <select
            aria-label="Service ticket"
            disabled={catalog.kind !== "ready"}
            onChange={(event) => {
              setRecommendation({ kind: "loading" });
              setSelectedTicketId(event.target.value);
            }}
            value={selectedTicketId}
          >
            {catalog.kind !== "ready" && <option>Loading tickets…</option>}
            {catalog.kind === "ready" &&
              catalog.tickets.map((ticket) => (
                <option key={ticket.ticket_id} value={ticket.ticket_id}>
                  #{ticket.ticket_id} · {ticket.title}
                </option>
              ))}
          </select>
        </label>
        {selectedTicket && (
          <div className="dispatch-ticket-context">
            <span
              className={`priority-label priority-${selectedTicket.priority}`}
            >
              {selectedTicket.priority}
            </span>
            <strong>{selectedTicket.site_name}</strong>
            <span>{selectedTicket.required_certification_ids.join(", ")}</span>
            <Link href={`/tickets/${selectedTicket.ticket_id}`}>
              Open ticket ↗
            </Link>
          </div>
        )}
      </section>

      {catalog.kind === "error" && (
        <div className="catalog-error" role="alert">
          {catalog.message}
        </div>
      )}
      {(catalog.kind === "loading" || recommendation.kind === "loading") && (
        <div className="catalog-loading" role="status">
          <span /> Evaluating eligibility and scores…
        </div>
      )}
      {recommendation.kind === "error" && (
        <div className="catalog-error" role="alert">
          {recommendation.message}
        </div>
      )}
      {recommendation.kind === "ready" && (
        <RecommendationResult result={recommendation.result} />
      )}
    </div>
  );
}

function RecommendationResult({ result }: { result: DispatchRecommendation }) {
  const recommended = result.eligible_candidates[0];

  return (
    <div className="dispatch-results" aria-live="polite">
      <section className="policy-strip" aria-label="Policy evaluation context">
        <div>
          <span>Policy</span>
          <strong>{result.policy_version}</strong>
        </div>
        <div>
          <span>Window</span>
          <strong>
            {formatDateTime(result.service_window_start)}–
            {formatDateTime(result.service_window_end)} UTC
          </strong>
        </div>
        <div>
          <span>Radius</span>
          <strong>{result.maximum_distance_km} km</strong>
        </div>
        <div>
          <span>Evaluated</span>
          <strong>{result.total_evaluated} technicians</strong>
        </div>
      </section>

      {recommended ? (
        <section className="recommendation-hero panel">
          <div className="recommendation-rank" aria-label="Rank one">
            01
          </div>
          <div className="recommendation-copy">
            <p className="panel-kicker">Recommended technician</p>
            <h2>{recommended.technician_name}</h2>
            <p>
              Passed availability, certification, schedule, location, and
              service-radius gates.
            </p>
            <div className="recommendation-facts">
              <span>{recommended.distance_km} km straight-line estimate</span>
              <span>{recommended.active_assignment_count} active jobs</span>
              <span>{recommended.matched_certification_ids.join(", ")}</span>
            </div>
            <Link href={`/technicians/${recommended.technician_id}`}>
              Review technician profile →
            </Link>
          </div>
          <div className="score-block">
            <strong>{recommended.score?.toFixed(1)}</strong>
            <span>of 100</span>
          </div>
          {recommended.score_breakdown && (
            <ScoreBreakdown candidate={recommended} />
          )}
        </section>
      ) : (
        <section className="no-recommendation panel" role="status">
          <span aria-hidden="true">!</span>
          <div>
            <p className="panel-kicker">Manual review required</p>
            <h2>No technician passed every eligibility gate.</h2>
            <p>
              The policy does not relax certifications, availability, schedule,
              valid location, or the {result.maximum_distance_km} km service
              radius to force a result.
            </p>
          </div>
        </section>
      )}

      {result.eligible_candidates.length > 0 && (
        <section className="panel candidate-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Ranked output</p>
              <h2>Eligible candidates</h2>
            </div>
            <span className="phase-badge">
              {result.eligible_candidates.length}
            </span>
          </div>
          <div className="candidate-list">
            {result.eligible_candidates.map((candidate) => (
              <Link
                href={`/technicians/${candidate.technician_id}`}
                key={candidate.technician_id}
              >
                <span className="candidate-rank">
                  {String(candidate.rank).padStart(2, "0")}
                </span>
                <span>
                  <strong>{candidate.technician_name}</strong>
                  <small>
                    {candidate.distance_km} km ·{" "}
                    {candidate.active_assignment_count} active jobs
                  </small>
                </span>
                <strong className="candidate-score">
                  {candidate.score?.toFixed(1)}
                </strong>
              </Link>
            ))}
          </div>
        </section>
      )}

      <details className="exclusion-panel panel">
        <summary>
          <span>
            <small>Eligibility audit</small>
            Why {result.excluded_candidates.length} technicians were excluded
          </span>
          <span aria-hidden="true">+</span>
        </summary>
        <div className="exclusion-list">
          {result.excluded_candidates.map((candidate) => (
            <div key={candidate.technician_id}>
              <span>
                <strong>{candidate.technician_name}</strong>
                <small>{candidate.technician_id}</small>
              </span>
              <span className="reason-list">
                {candidate.exclusion_reasons.map((reason) => (
                  <span key={reason}>{formatLabel(reason)}</span>
                ))}
              </span>
              <span className="mono-cell">
                {candidate.distance_km === null
                  ? "No distance"
                  : `${candidate.distance_km} km`}
              </span>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

function ScoreBreakdown({ candidate }: { candidate: DispatchCandidate }) {
  const breakdown = candidate.score_breakdown;
  if (!breakdown) return null;
  const items = [
    ["Certification", breakdown.certification, 25],
    ["Proximity", breakdown.proximity, 30],
    ["Workload", breakdown.workload, 20],
    ["Performance", breakdown.performance, 15],
    ["Experience", breakdown.experience, 10],
  ] as const;

  return (
    <dl className="score-breakdown">
      {items.map(([label, value, maximum]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            <span style={{ width: `${(value / maximum) * 100}%` }} />
            <small>
              {value.toFixed(1)} / {maximum}
            </small>
          </dd>
        </div>
      ))}
    </dl>
  );
}
