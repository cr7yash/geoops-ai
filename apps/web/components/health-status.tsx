"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";

type HealthResponse = {
  status: "ok";
  service: string;
  environment: string;
  version: string;
};

type HealthState =
  | { kind: "checking" }
  | { kind: "healthy"; data: HealthResponse; checkedAt: Date }
  | { kind: "unavailable"; message: string };

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    typeof candidate.service === "string" &&
    typeof candidate.environment === "string" &&
    typeof candidate.version === "string"
  );
}

export function HealthStatus() {
  const [state, setState] = useState<HealthState>({ kind: "checking" });
  const requestSequence = useRef(0);

  const checkHealth = useCallback(async () => {
    const requestId = ++requestSequence.current;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5_000);

    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(`API responded with HTTP ${response.status}`);

      const payload: unknown = await response.json();
      if (!isHealthResponse(payload))
        throw new Error("API returned an unexpected health response");

      if (requestId === requestSequence.current) {
        setState({ kind: "healthy", data: payload, checkedAt: new Date() });
      }
    } catch (error) {
      if (requestId === requestSequence.current) {
        const message =
          error instanceof Error ? error.message : "Unable to reach the API";
        setState({ kind: "unavailable", message });
      }
    } finally {
      window.clearTimeout(timeout);
    }
  }, []);

  useEffect(() => {
    const initialCheck = window.setTimeout(() => void checkHealth(), 0);
    return () => {
      window.clearTimeout(initialCheck);
      requestSequence.current += 1;
    };
  }, [checkHealth]);

  const recheckHealth = () => {
    setState({ kind: "checking" });
    void checkHealth();
  };

  const isHealthy = state.kind === "healthy";

  return (
    <article className="panel health-panel" data-testid="health-panel">
      <div className="panel-heading">
        <div>
          <p className="panel-kicker">Live service check</p>
          <h2>API gateway</h2>
        </div>
        <span
          className={`status-chip status-${state.kind}`}
          role="status"
          aria-live="polite"
        >
          <span className="status-indicator" />
          {state.kind === "checking"
            ? "Checking"
            : state.kind === "healthy"
              ? "Operational"
              : "Unavailable"}
        </span>
      </div>

      <div className="health-orbit" aria-hidden="true">
        <span
          className={
            isHealthy ? "health-core health-core-ready" : "health-core"
          }
        >
          {state.kind === "checking" ? "···" : isHealthy ? "200" : "!"}
        </span>
      </div>

      {state.kind === "healthy" && (
        <dl className="health-details">
          <div>
            <dt>Service</dt>
            <dd>{state.data.service}</dd>
          </div>
          <div>
            <dt>Environment</dt>
            <dd>{state.data.environment}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>v{state.data.version}</dd>
          </div>
          <div>
            <dt>Checked</dt>
            <dd>
              {state.checkedAt.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </dd>
          </div>
        </dl>
      )}

      {state.kind === "checking" && (
        <p className="health-message">Contacting {API_BASE_URL}/health…</p>
      )}

      {state.kind === "unavailable" && (
        <div className="health-error" role="alert">
          <p>{state.message}</p>
          <span>Start the API with `make api`, then try again.</span>
        </div>
      )}

      <div className="health-footer">
        <code>{API_BASE_URL}/health</code>
        <button
          disabled={state.kind === "checking"}
          onClick={recheckHealth}
          type="button"
        >
          Recheck
        </button>
      </div>
    </article>
  );
}
