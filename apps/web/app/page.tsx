import { HealthStatus } from "@/components/health-status";

const foundationItems = [
  { label: "Web console", detail: "Next.js · TypeScript", ready: true },
  { label: "API gateway", detail: "FastAPI · Pydantic", ready: true },
  {
    label: "Operational data",
    detail: "55 deterministic tickets",
    ready: true,
  },
  { label: "Dispatch engine", detail: "Scheduled for Phase 3", ready: false },
] as const;

export default function Home() {
  return (
    <div className="page-content">
      <section className="hero" aria-labelledby="page-title">
        <div className="hero-copy">
          <p className="section-kicker">Operations control plane</p>
          <h1 id="page-title">
            Field operations, grounded in the real state of work.
          </h1>
          <p className="hero-description">
            Explore service demand and technician capacity across a
            deterministic Bay Area dataset. Every record comes from the typed
            operational API and is ready for dispatch reasoning in the next
            phase.
          </p>
        </div>
        <div className="coordinate-card" aria-label="Dataset coverage">
          <div className="coordinate-grid" aria-hidden="true" />
          <span className="coordinate-marker" aria-hidden="true">
            <span />
          </span>
          <div className="coordinate-copy">
            <span>Bay Area service territory</span>
            <strong>25 customer sites</strong>
            <strong>15 field technicians</strong>
          </div>
        </div>
      </section>

      <section className="status-grid" aria-label="Platform status">
        <HealthStatus />

        <article className="panel foundation-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Build sequence</p>
              <h2>Platform foundation</h2>
            </div>
            <span className="phase-badge">Phase 2</span>
          </div>

          <ul className="foundation-list">
            {foundationItems.map((item) => (
              <li key={item.label}>
                <span className={item.ready ? "check check-ready" : "check"}>
                  {item.ready ? "✓" : "—"}
                </span>
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.detail}</small>
                </span>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="principles" aria-labelledby="principles-title">
        <div className="principles-heading">
          <p className="section-kicker">Data posture</p>
          <h2 id="principles-title">
            Operationally useful before AI enters the loop.
          </h2>
        </div>
        <div className="principle-grid">
          <article>
            <span>01</span>
            <h3>Typed relationships</h3>
            <p>
              Customers, sites, tickets, technicians, certifications, and
              assignments align.
            </p>
          </article>
          <article>
            <span>02</span>
            <h3>Deterministic scenarios</h3>
            <p>
              Edge cases remain reproducible across local runs, tests, and
              evaluations.
            </p>
          </article>
          <article>
            <span>03</span>
            <h3>Storage-neutral access</h3>
            <p>
              Repository ports isolate application behavior from local JSON and
              BigQuery.
            </p>
          </article>
        </div>
      </section>
    </div>
  );
}
