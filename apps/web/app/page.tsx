import { HealthStatus } from "@/components/health-status";
import { MarkIcon, NavIcon } from "@/components/icons";

const navigation = [
  { label: "Overview", icon: "overview", active: true },
  { label: "Tickets", icon: "tickets", active: false },
  { label: "Technicians", icon: "technicians", active: false },
  { label: "Agent workspace", icon: "agent", active: false },
  { label: "Approvals", icon: "approvals", active: false },
] as const;

const foundationItems = [
  { label: "Web console", detail: "Next.js · TypeScript", ready: true },
  { label: "API gateway", detail: "FastAPI · Pydantic", ready: true },
  { label: "Operational data", detail: "Scheduled for Phase 2", ready: false },
  { label: "Dispatch agent", detail: "Scheduled for Phase 6", ready: false },
] as const;

export default function Home() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <MarkIcon />
          <div>
            <p className="brand-name">GeoOps</p>
            <p className="brand-subtitle">AI Operations</p>
          </div>
        </div>

        <nav aria-label="Primary navigation" className="primary-nav">
          <p className="nav-eyebrow">Workspace</p>
          {navigation.map((item) => (
            <span
              aria-current={item.active ? "page" : undefined}
              aria-disabled={!item.active}
              className={item.active ? "nav-item nav-item-active" : "nav-item"}
              key={item.label}
            >
              <NavIcon name={item.icon} />
              <span>{item.label}</span>
              {!item.active && (
                <span className="phase-dot" aria-label="Planned" />
              )}
            </span>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="sidebar-note-icon" aria-hidden="true">
            01
          </span>
          <div>
            <p>Foundation phase</p>
            <span>Local development mode</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand">
            <MarkIcon />
            <span>GeoOps AI</span>
          </div>
          <div className="environment-pill">
            <span className="environment-pulse" />
            Development
          </div>
        </header>

        <div className="page-content">
          <section className="hero" aria-labelledby="page-title">
            <div className="hero-copy">
              <p className="section-kicker">Operations control plane</p>
              <h1 id="page-title">
                Field intelligence starts with a reliable foundation.
              </h1>
              <p className="hero-description">
                The GeoOps console is online in local mode. This first vertical
                slice establishes the web and API boundary that future dispatch,
                routing, and knowledge workflows will build on.
              </p>
            </div>
            <div className="coordinate-card" aria-label="Platform coordinates">
              <div className="coordinate-grid" aria-hidden="true" />
              <span className="coordinate-marker" aria-hidden="true">
                <span />
              </span>
              <div className="coordinate-copy">
                <span>Local control plane</span>
                <strong>37.7749° N</strong>
                <strong>122.4194° W</strong>
              </div>
            </div>
          </section>

          <section className="status-grid" aria-label="Foundation status">
            <HealthStatus />

            <article className="panel foundation-panel">
              <div className="panel-heading">
                <div>
                  <p className="panel-kicker">Build sequence</p>
                  <h2>Platform foundation</h2>
                </div>
                <span className="phase-badge">Phase 1</span>
              </div>

              <ul className="foundation-list">
                {foundationItems.map((item) => (
                  <li key={item.label}>
                    <span
                      className={item.ready ? "check check-ready" : "check"}
                    >
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
              <p className="section-kicker">Engineering posture</p>
              <h2 id="principles-title">
                Ready to grow without pretending it already has.
              </h2>
            </div>
            <div className="principle-grid">
              <article>
                <span>01</span>
                <h3>Observable by default</h3>
                <p>
                  Every request receives a correlation ID and emits structured
                  telemetry.
                </p>
              </article>
              <article>
                <span>02</span>
                <h3>Cloud-ready, local-first</h3>
                <p>
                  The same application boundary works locally and in production
                  containers.
                </p>
              </article>
              <article>
                <span>03</span>
                <h3>Truth over theater</h3>
                <p>
                  Only live system state is shown; operational metrics arrive
                  with real data.
                </p>
              </article>
            </div>
          </section>
        </div>

        <footer className="footer">
          <span>GeoOps AI · Phase 1</span>
          <span>System time is reported by your device</span>
        </footer>
      </main>
    </div>
  );
}
