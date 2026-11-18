"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, formatDateTime } from "@/lib/api";

type Summary = {
  active_tickets: number;
  sla_at_risk: number;
  available_technicians: number;
  pending_approvals: number;
  completed_dispatches: number;
  reference_time: string;
  recent_agent_runs: Array<{
    agent_run_id: string;
    model: string;
    started_at: string;
  }>;
};

export function OperationsSummary() {
  const [summary, setSummary] = useState<Summary>();
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/operations`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Unavailable");
        const data: Summary = await response.json();
        setSummary(data);
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError"))
          setError(true);
      });
    return () => controller.abort();
  }, []);
  if (error) return <p role="alert">Operational summary unavailable.</p>;
  if (!summary) return <p role="status">Loading operational summary…</p>;
  return (
    <section aria-label="Current operational records">
      <div className="evaluation-metrics">
        {[
          ["Active tickets", summary.active_tickets],
          ["SLA at risk", summary.sla_at_risk],
          ["Available technicians", summary.available_technicians],
          ["Pending approvals", summary.pending_approvals],
          ["Completed dispatches", summary.completed_dispatches],
        ].map(([label, value]) => (
          <article className="panel" key={label}>
            <p>{label}</p>
            <strong>{value}</strong>
          </article>
        ))}
      </div>
      <p className="summary-reference">
        SLA clock: {formatDateTime(summary.reference_time)} UTC · Synthetic
        operational dataset
      </p>
      {summary.recent_agent_runs.length > 0 && (
        <div className="panel">
          <h2>Recent agent activity</h2>
          <ul className="knowledge-document-list">
            {summary.recent_agent_runs.map((run) => (
              <li key={run.agent_run_id}>
                <strong>{run.model}</strong>
                <small>
                  {formatDateTime(run.started_at)} UTC ·{" "}
                  {run.agent_run_id.slice(-8)}
                </small>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
