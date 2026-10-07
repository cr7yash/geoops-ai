"use client";

import { FormEvent, useEffect, useState } from "react";

import { formatLabel, getKnowledgeDocuments, searchKnowledge } from "@/lib/api";
import type {
  KnowledgeDocumentList,
  KnowledgeDocumentType,
  KnowledgeSearchResponse,
} from "@/lib/types";

type DocumentState =
  | { kind: "loading" }
  | { kind: "ready"; data: KnowledgeDocumentList }
  | { kind: "error"; message: string };

type SearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: KnowledgeSearchResponse }
  | { kind: "error"; message: string };

const documentTypes: KnowledgeDocumentType[] = [
  "manual",
  "contract",
  "service_report",
  "incident_history",
  "policy",
];

export function KnowledgeWorkspace() {
  const [documents, setDocuments] = useState<DocumentState>({
    kind: "loading",
  });
  const [search, setSearch] = useState<SearchState>({ kind: "idle" });
  const [query, setQuery] = useState(
    "What should be checked first for compressor pressure loss?",
  );
  const [documentType, setDocumentType] = useState("");
  const [equipmentType, setEquipmentType] = useState("");
  const [customerId, setCustomerId] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getKnowledgeDocuments(controller.signal)
      .then((data) => setDocuments({ kind: "ready", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setDocuments({
          kind: "error",
          message:
            error instanceof Error
              ? error.message
              : "Unable to load the knowledge catalog",
        });
      });
    return () => controller.abort();
  }, []);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 3) return;
    setSearch({ kind: "loading" });
    searchKnowledge({
      query: normalizedQuery,
      ...(customerId.trim() ? { customer_id: customerId.trim() } : {}),
      ...(equipmentType.trim()
        ? { equipment_type: equipmentType.trim().toLowerCase() }
        : {}),
      ...(documentType
        ? { document_type: documentType as KnowledgeDocumentType }
        : {}),
      limit: 6,
    })
      .then((data) => setSearch({ kind: "ready", data }))
      .catch((error: unknown) =>
        setSearch({
          kind: "error",
          message:
            error instanceof Error ? error.message : "Knowledge search failed",
        }),
      );
  }

  return (
    <div className="page-content knowledge-page">
      <header className="knowledge-header">
        <div>
          <p className="section-kicker">Enterprise evidence</p>
          <h1>Knowledge retrieval</h1>
          <p>
            Search operational manuals, contracts, service history, incidents,
            and policies. Results are source passages—not generated answers.
          </p>
        </div>
        <span className="read-only-badge">Read only</span>
      </header>

      <div className="knowledge-layout">
        <section
          className="knowledge-search-column"
          aria-label="Knowledge search"
        >
          <form className="knowledge-search panel" onSubmit={submitSearch}>
            <label className="knowledge-query">
              <span>Operational question</span>
              <textarea
                aria-label="Operational question"
                maxLength={500}
                onChange={(event) => setQuery(event.target.value)}
                rows={4}
                value={query}
              />
            </label>
            <div className="knowledge-filters">
              <label>
                <span>Document type</span>
                <select
                  aria-label="Document type"
                  onChange={(event) => setDocumentType(event.target.value)}
                  value={documentType}
                >
                  <option value="">All types</option>
                  {documentTypes.map((value) => (
                    <option key={value} value={value}>
                      {formatLabel(value)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Equipment</span>
                <input
                  aria-label="Equipment type"
                  onChange={(event) => setEquipmentType(event.target.value)}
                  placeholder="e.g. compressor"
                  value={equipmentType}
                />
              </label>
              <label>
                <span>Customer ID</span>
                <input
                  aria-label="Customer ID"
                  onChange={(event) => setCustomerId(event.target.value)}
                  placeholder="e.g. C-002"
                  value={customerId}
                />
              </label>
            </div>
            <div className="knowledge-search-footer">
              <p>
                Deterministic local embeddings · cosine similarity · cited
                passages
              </p>
              <button disabled={search.kind === "loading"} type="submit">
                {search.kind === "loading" ? "Searching…" : "Search sources"}
              </button>
            </div>
          </form>

          <div aria-live="polite" className="knowledge-results">
            {search.kind === "idle" && (
              <div className="knowledge-prompt panel">
                <span aria-hidden="true">↳</span>
                <div>
                  <strong>Search before drawing a conclusion.</strong>
                  <p>
                    Retrieved text remains separate from structured ticket and
                    dispatch data until the agent phase combines them.
                  </p>
                </div>
              </div>
            )}
            {search.kind === "loading" && (
              <div className="catalog-loading" role="status">
                <span /> Ranking source passages…
              </div>
            )}
            {search.kind === "error" && (
              <div className="catalog-error" role="alert">
                Knowledge search unavailable
                <span>{search.message}</span>
              </div>
            )}
            {search.kind === "ready" && search.data.sources.length === 0 && (
              <div className="catalog-empty" role="status">
                No source passages matched the query and filters.
              </div>
            )}
            {search.kind === "ready" && search.data.sources.length > 0 && (
              <section aria-labelledby="sources-title">
                <div className="knowledge-result-heading">
                  <div>
                    <p className="panel-kicker">Retrieval output</p>
                    <h2 id="sources-title">Ranked source passages</h2>
                  </div>
                  <span>{search.data.result_count} cited</span>
                </div>
                <ol className="source-list">
                  {search.data.sources.map((source) => (
                    <li className="source-card panel" key={source.chunk_id}>
                      <div className="source-rank">
                        <span>{String(source.rank).padStart(2, "0")}</span>
                        <strong>
                          {Math.max(0, source.score * 100).toFixed(1)}%
                        </strong>
                        <small>similarity</small>
                      </div>
                      <div className="source-content">
                        <div className="source-meta">
                          <span>{formatLabel(source.document_type)}</span>
                          {source.equipment_type && (
                            <span>{formatLabel(source.equipment_type)}</span>
                          )}
                          {source.customer_id && (
                            <span>{source.customer_id}</span>
                          )}
                        </div>
                        <h3>{source.title}</h3>
                        <p className="source-section">{source.section}</p>
                        <blockquote>{source.excerpt}</blockquote>
                        <footer>
                          <cite>{source.citation}</cite>
                          <span>{source.storage_uri}</span>
                        </footer>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </div>
        </section>

        <aside
          className="knowledge-catalog panel"
          aria-labelledby="catalog-title"
        >
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Indexed originals</p>
              <h2 id="catalog-title">Source catalog</h2>
            </div>
            {documents.kind === "ready" && (
              <span className="phase-badge">{documents.data.total}</span>
            )}
          </div>
          {documents.kind === "loading" && (
            <div className="catalog-loading compact" role="status">
              <span /> Loading documents…
            </div>
          )}
          {documents.kind === "error" && (
            <div className="catalog-error compact" role="alert">
              {documents.message}
            </div>
          )}
          {documents.kind === "ready" && (
            <ul className="knowledge-document-list">
              {documents.data.items.map((document) => (
                <li key={document.document_id}>
                  <span>{formatLabel(document.document_type)}</span>
                  <strong>{document.title}</strong>
                  <small>
                    v{document.version}
                    {document.equipment_type
                      ? ` · ${formatLabel(document.equipment_type)}`
                      : ""}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  );
}
