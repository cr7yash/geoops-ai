"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

import { askAgent, formatLabel } from "@/lib/api";
import type { AgentChatResponse } from "@/lib/types";

type AgentState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: AgentChatResponse }
  | { kind: "error"; message: string };

const examplePrompts = [
  "Who is the best technician for ticket 184?",
  "What procedure should I use to troubleshoot ticket 184?",
  "Show open critical tickets",
  "Assign James Chen to ticket 184",
];

export function AgentWorkspace() {
  const [prompt, setPrompt] = useState(examplePrompts[0]);
  const [sessionId, setSessionId] = useState<string>();
  const [state, setState] = useState<AgentState>({ kind: "idle" });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = prompt.trim();
    if (message.length < 2) return;
    setState({ kind: "loading" });
    askAgent({ message, ...(sessionId ? { session_id: sessionId } : {}) })
      .then((data) => {
        setSessionId(data.session_id);
        setState({ kind: "ready", data });
      })
      .catch((error: unknown) =>
        setState({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "The operations agent is unavailable",
        }),
      );
  }

  return (
    <div className="page-content agent-page">
      <header className="agent-header">
        <div>
          <p className="section-kicker">Evidence-led assistance</p>
          <h1>Agent workspace</h1>
          <p>
            Ask about tickets, technician eligibility, route-aware dispatch, and
            operational source documents. Every fact passes through a typed,
            read-only tool.
          </p>
        </div>
        <span className="read-only-badge">Approval gated</span>
      </header>

      <div className="agent-layout">
        <section className="agent-conversation" aria-label="Agent conversation">
          <form className="agent-composer panel" onSubmit={submit}>
            <label htmlFor="agent-prompt">Operational question</label>
            <textarea
              id="agent-prompt"
              maxLength={2000}
              onChange={(event) => setPrompt(event.target.value)}
              rows={4}
              value={prompt}
            />
            <div className="agent-examples" aria-label="Example questions">
              {examplePrompts.map((example) => (
                <button
                  key={example}
                  onClick={() => setPrompt(example)}
                  type="button"
                >
                  {example}
                </button>
              ))}
            </div>
            <div className="agent-submit-row">
              <p>Responses show tool evidence, not hidden reasoning.</p>
              <button disabled={state.kind === "loading"} type="submit">
                {state.kind === "loading" ? "Investigating…" : "Ask GeoOps"}
              </button>
            </div>
          </form>

          <div className="agent-output" aria-live="polite">
            {state.kind === "idle" && (
              <div className="agent-empty panel">
                <span aria-hidden="true">⌁</span>
                <div>
                  <strong>Start with an operational question.</strong>
                  <p>
                    Recommendations are read-only. Assignment requests create a
                    proposal for a human decision; they never execute here.
                  </p>
                </div>
              </div>
            )}
            {state.kind === "loading" && (
              <div className="catalog-loading" role="status">
                <span /> Checking operational evidence…
              </div>
            )}
            {state.kind === "error" && (
              <div className="catalog-error" role="alert">
                Agent unavailable
                <span>{state.message}</span>
              </div>
            )}
            {state.kind === "ready" && <AgentResult response={state.data} />}
          </div>
        </section>

        <aside
          className="agent-boundary panel"
          aria-labelledby="boundary-title"
        >
          <p className="panel-kicker">Control boundary</p>
          <h2 id="boundary-title">Approval before action</h2>
          <ul>
            <li>Strict tool inputs</li>
            <li>Application-service access only</li>
            <li>Cited document passages</li>
            <li>Route estimates labeled</li>
            <li>No assignment execution tool</li>
          </ul>
          <p>
            A mutation request can create a validated proposal. Human approval
            records authorization, while assignment execution remains outside
            this phase.
          </p>
        </aside>
      </div>
    </div>
  );
}

function AgentResult({ response }: { response: AgentChatResponse }) {
  return (
    <article className="agent-result panel">
      <div className="agent-result-heading">
        <div>
          <p className="panel-kicker">Agent response</p>
          <h2>Operational answer</h2>
        </div>
        <span
          className={
            response.requires_approval ? "approval-needed" : "read-only-badge"
          }
        >
          {response.requires_approval ? "Approval required" : "Read only"}
        </span>
      </div>
      <p className="agent-answer">{response.answer}</p>

      {response.recommended_action && (
        <div className="agent-recommendation">
          <span>Recommended next review</span>
          <strong>{response.recommended_action.label}</strong>
          <small>No assignment has been changed.</small>
          {response.recommended_action.approval_id && (
            <Link href="/approvals">Open approval queue →</Link>
          )}
        </div>
      )}

      {response.sources.length > 0 && (
        <section
          className="agent-evidence-section"
          aria-labelledby="agent-sources"
        >
          <h3 id="agent-sources">Cited sources</h3>
          <ol className="agent-source-list">
            {response.sources.map((source) => (
              <li key={source.chunk_id}>
                <strong>{source.title}</strong>
                <span>{source.section}</span>
                <cite>{source.citation}</cite>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section className="agent-evidence-section" aria-labelledby="agent-tools">
        <div className="agent-tools-heading">
          <h3 id="agent-tools">Tool evidence</h3>
          <span>{response.tools_used.length} calls</span>
        </div>
        {response.tools_used.length === 0 ? (
          <p className="agent-no-tools">No operational tool was run.</p>
        ) : (
          <ol className="agent-tool-list">
            {response.tools_used.map((tool, index) => (
              <li key={`${tool.tool}-${index}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{formatLabel(tool.tool)}</strong>
                  <p>{tool.summary}</p>
                </div>
                <small>{tool.latency_ms.toFixed(1)} ms</small>
              </li>
            ))}
          </ol>
        )}
      </section>

      <footer className="agent-run-meta">
        <span>{formatLabel(response.model_provider)}</span>
        <span>{response.model_name}</span>
        <span>{Math.round(response.confidence * 100)}% confidence</span>
        <span>Trace {response.trace_id.slice(0, 12)}</span>
      </footer>
    </article>
  );
}
