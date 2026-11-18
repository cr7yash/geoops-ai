"use client";

import { useEffect, useState } from "react";

import {
  formatDateTime,
  formatLabel,
  getEvaluationRuns,
  runEvaluation,
} from "@/lib/api";
import type { EvaluationRun } from "@/lib/types";

const metricNames = [
  "task_success",
  "tool_selection_accuracy",
  "tool_argument_accuracy",
  "retrieval_recall",
  "citation_correctness",
  "policy_compliance",
  "approval_correctness",
  "p50_latency_ms",
  "p95_latency_ms",
  "token_usage",
  "cost_per_success_usd",
];

function metricValue(name: string, value: number | null | undefined) {
  if (value == null) return "Not reported";
  if (name.endsWith("_ms")) return `${value.toFixed(1)} ms`;
  if (name.endsWith("_usd")) return `$${value.toFixed(6)}`;
  if (name === "token_usage") return value.toFixed(0);
  return `${(value * 100).toFixed(1)}%`;
}

type RunState =
  | { kind: "loading" }
  | { kind: "ready"; runs: EvaluationRun[] }
  | { kind: "error"; message: string };

export function EvaluationWorkspace() {
  const [state, setState] = useState<RunState>({ kind: "loading" });
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [baselineId, setBaselineId] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getEvaluationRuns(controller.signal)
      .then((runs) => setState({ kind: "ready", runs }))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setState({
          kind: "error",
          message:
            reason instanceof Error ? reason.message : "Runs unavailable",
        });
      });
    return () => controller.abort();
  }, []);

  function run() {
    setRunning(true);
    setError("");
    runEvaluation()
      .then((result) => {
        setState((previous) => ({
          kind: "ready",
          runs: [result, ...(previous.kind === "ready" ? previous.runs : [])],
        }));
        setSelectedId(result.run_id);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Run failed"),
      )
      .finally(() => setRunning(false));
  }

  const runs = state.kind === "ready" ? state.runs : [];
  const selected = runs.find((run) => run.run_id === selectedId) ?? runs[0];
  const baseline = runs.find(
    (run) => run.run_id === baselineId && run.run_id !== selected?.run_id,
  );

  return (
    <div className="page-content evaluations-page">
      <header className="approvals-header">
        <div>
          <p className="section-kicker">Agent quality</p>
          <h1>Evaluation runs</h1>
          <p>
            Inspect recorded task outcomes, policy checks, retrieval quality,
            and latency. Compare runs against the same labeled dataset.
          </p>
        </div>
        <button
          className="primary-action evaluation-run"
          disabled={running}
          onClick={run}
          type="button"
        >
          {running ? "Running suite…" : "Run evaluation"}
        </button>
      </header>
      {running && <p role="status">Executing isolated evaluation scenarios…</p>}
      {error && (
        <p className="catalog-error" role="alert">
          {error}
        </p>
      )}
      {state.kind === "loading" && <p role="status">Loading recorded runs…</p>}
      {state.kind === "error" && (
        <p className="catalog-error" role="alert">
          {state.message}
        </p>
      )}
      {state.kind === "ready" && runs.length === 0 && (
        <div className="catalog-empty" role="status">
          No evaluation runs yet. Run the suite to measure agent behavior.
        </div>
      )}
      {selected && (
        <>
          <section className="panel evaluation-selectors">
            <label>
              Selected run
              <select
                value={selected.run_id}
                onChange={(event) => setSelectedId(event.target.value)}
              >
                {runs.map((run) => (
                  <option key={run.run_id} value={run.run_id}>
                    {formatDateTime(run.created_at)} ·{" "}
                    {run.passed ? "Pass" : "Fail"} · {run.run_id.slice(-6)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Compare with
              <select
                value={baselineId}
                onChange={(event) => setBaselineId(event.target.value)}
              >
                <option value="">No baseline</option>
                {runs
                  .filter((run) => run.run_id !== selected.run_id)
                  .map((run) => (
                    <option key={run.run_id} value={run.run_id}>
                      {formatDateTime(run.created_at)} · {run.run_id.slice(-6)}
                    </option>
                  ))}
              </select>
            </label>
          </section>
          {baseline && baseline.dataset_sha256 !== selected.dataset_sha256 && (
            <p role="status">These runs use different dataset revisions.</p>
          )}
          <div className="evaluation-heading">
            <span
              className={`approval-status ${selected.passed ? "status-approved" : "status-failed"}`}
            >
              {selected.passed
                ? "Regression gate passed"
                : "Regression gate failed"}
            </span>
            <span>
              {selected.provider} · {selected.model} · {selected.results.length}{" "}
              cases
            </span>
          </div>
          <section
            className="evaluation-metrics"
            aria-label="Measured evaluation metrics"
          >
            {metricNames.map((name) => (
              <article className="panel" key={name}>
                <p>{formatLabel(name)}</p>
                <strong>{metricValue(name, selected.metrics[name])}</strong>
                {baseline && (
                  <small>
                    Baseline {metricValue(name, baseline.metrics[name])}
                  </small>
                )}
              </article>
            ))}
          </section>
          <section className="panel evaluation-cases">
            <h2>Scenario results</h2>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Outcome</th>
                    <th>Tools</th>
                    <th>Policy</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.results.map((result) => (
                    <tr key={result.case_id}>
                      <td>{formatLabel(result.case_id)}</td>
                      <td>
                        {result.task_success
                          ? "Passed"
                          : (result.error_type ?? "Failed")}
                      </td>
                      <td>
                        {metricValue("tools", result.tool_selection_accuracy)}
                      </td>
                      <td>{metricValue("policy", result.policy_compliance)}</td>
                      <td>{result.latency_ms.toFixed(1)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
