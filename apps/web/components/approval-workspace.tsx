"use client";

import { useEffect, useState } from "react";

import {
  decideApproval,
  formatDateTime,
  formatLabel,
  getApprovals,
} from "@/lib/api";
import type { ApprovalRequest, ApprovalStatus } from "@/lib/types";

type ApprovalState =
  | { kind: "loading" }
  | { kind: "ready"; items: ApprovalRequest[] }
  | { kind: "error"; message: string };

const filters: Array<"all" | ApprovalStatus> = [
  "all",
  "pending",
  "approved",
  "rejected",
  "expired",
];

export function ApprovalWorkspace() {
  const [state, setState] = useState<ApprovalState>({ kind: "loading" });
  const [filter, setFilter] = useState<(typeof filters)[number]>("all");
  const [reviewer, setReviewer] = useState("");
  const [comment, setComment] = useState("");
  const [decidingId, setDecidingId] = useState<string>();
  const [decisionError, setDecisionError] = useState<string>();

  useEffect(() => {
    const controller = new AbortController();
    getApprovals(controller.signal)
      .then((data) => setState({ kind: "ready", items: data.items }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setState({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Unable to load approval requests",
        });
      });
    return () => controller.abort();
  }, []);

  function decide(approvalId: string, decision: "approve" | "reject") {
    if (reviewer.trim().length < 2) return;
    setDecidingId(approvalId);
    setDecisionError(undefined);
    decideApproval(approvalId, decision, {
      decided_by: reviewer.trim(),
      ...(comment.trim() ? { comment: comment.trim() } : {}),
    })
      .then((updated) => {
        setState((current) =>
          current.kind === "ready"
            ? {
                kind: "ready",
                items: current.items.map((item) =>
                  item.approval_id === updated.approval_id ? updated : item,
                ),
              }
            : current,
        );
        setComment("");
      })
      .catch((error: unknown) =>
        setDecisionError(
          error instanceof Error ? error.message : "Approval decision failed",
        ),
      )
      .finally(() => setDecidingId(undefined));
  }

  const visible =
    state.kind === "ready"
      ? state.items.filter((item) => filter === "all" || item.status === filter)
      : [];
  const pending =
    state.kind === "ready"
      ? state.items.filter((item) => item.status === "pending").length
      : 0;

  return (
    <div className="page-content approvals-page">
      <header className="approvals-header">
        <div>
          <p className="section-kicker">Human control boundary</p>
          <h1>Approval queue</h1>
          <p>
            Review validated assignment proposals and their dispatch evidence. A
            decision records authorization only; it does not execute an
            assignment.
          </p>
        </div>
        <span className="phase-badge">{pending} pending</span>
      </header>

      <section
        className="approval-controls panel"
        aria-label="Approval controls"
      >
        <div className="approval-filters" aria-label="Filter approvals">
          {filters.map((value) => (
            <button
              aria-pressed={filter === value}
              key={value}
              onClick={() => setFilter(value)}
              type="button"
            >
              {formatLabel(value)}
            </button>
          ))}
        </div>
        <div className="reviewer-fields">
          <label>
            <span>Reviewer identity</span>
            <input
              aria-label="Reviewer identity"
              maxLength={100}
              onChange={(event) => setReviewer(event.target.value)}
              placeholder="Name or work email"
              value={reviewer}
            />
          </label>
          <label>
            <span>Decision comment</span>
            <input
              aria-label="Decision comment"
              maxLength={500}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Optional review note"
              value={comment}
            />
          </label>
        </div>
      </section>

      {decisionError && (
        <div className="catalog-error" role="alert">
          Decision not saved<span>{decisionError}</span>
        </div>
      )}

      <div className="approval-list" aria-live="polite">
        {state.kind === "loading" && (
          <div className="catalog-loading" role="status">
            <span /> Loading approval queue…
          </div>
        )}
        {state.kind === "error" && (
          <div className="catalog-error" role="alert">
            Approval queue unavailable<span>{state.message}</span>
          </div>
        )}
        {state.kind === "ready" && visible.length === 0 && (
          <div className="catalog-empty" role="status">
            No {filter === "all" ? "" : `${filter} `}approval requests.
          </div>
        )}
        {visible.map((approval) => (
          <ApprovalCard
            approval={approval}
            deciding={decidingId === approval.approval_id}
            key={approval.approval_id}
            onDecide={decide}
            reviewerReady={reviewer.trim().length >= 2}
          />
        ))}
      </div>
    </div>
  );
}

function ApprovalCard({
  approval,
  deciding,
  onDecide,
  reviewerReady,
}: {
  approval: ApprovalRequest;
  deciding: boolean;
  onDecide: (approvalId: string, decision: "approve" | "reject") => void;
  reviewerReady: boolean;
}) {
  const pending = approval.status === "pending";
  return (
    <article className="approval-card panel">
      <header>
        <div>
          <p className="panel-kicker">{approval.approval_id}</p>
          <h2>{approval.ticket_title}</h2>
          <span>Ticket {approval.ticket_id}</span>
        </div>
        <span className={`approval-status status-${approval.status}`}>
          {formatLabel(approval.status)}
        </span>
      </header>

      <div className="approval-transfer">
        <div>
          <span>Current assignee</span>
          <strong>{approval.from_technician_name ?? "Unassigned"}</strong>
        </div>
        <span aria-hidden="true">→</span>
        <div>
          <span>Proposed assignee</span>
          <strong>{approval.to_technician_name}</strong>
          <small>{approval.to_technician_id}</small>
        </div>
      </div>

      <blockquote>{approval.reason}</blockquote>

      <dl className="approval-evidence">
        <div>
          <dt>Eligibility score</dt>
          <dd>{approval.evidence.score.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Travel time</dt>
          <dd>
            {approval.evidence.travel_duration_minutes?.toFixed(1) ?? "—"} min
          </dd>
        </div>
        <div>
          <dt>Distance</dt>
          <dd>{approval.evidence.distance_km?.toFixed(1) ?? "—"} km</dd>
        </div>
        <div>
          <dt>Route</dt>
          <dd>
            {approval.evidence.route_is_estimate
              ? "Estimate"
              : "Provider result"}
          </dd>
        </div>
        <div>
          <dt>Policy</dt>
          <dd>{approval.evidence.policy_version}</dd>
        </div>
        <div>
          <dt>Expires</dt>
          <dd>{formatDateTime(approval.expires_at)}</dd>
        </div>
      </dl>

      <footer>
        <div className="approval-audit">
          <span>Requested by {approval.requested_by}</span>
          <span>{formatDateTime(approval.requested_at)}</span>
          {approval.decided_by && <span>Decided by {approval.decided_by}</span>}
        </div>
        {pending ? (
          <div className="approval-actions">
            <button
              className="reject-action"
              disabled={!reviewerReady || deciding}
              onClick={() => onDecide(approval.approval_id, "reject")}
              type="button"
            >
              Reject
            </button>
            <button
              className="approve-action"
              disabled={!reviewerReady || deciding}
              onClick={() => onDecide(approval.approval_id, "approve")}
              type="button"
            >
              {deciding ? "Saving…" : "Approve"}
            </button>
          </div>
        ) : (
          <small className="execution-note">
            {approval.status === "approved"
              ? "Authorized only · execution awaits Phase 8"
              : "This proposal cannot be executed"}
          </small>
        )}
      </footer>
    </article>
  );
}
