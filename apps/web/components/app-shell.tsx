"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { MarkIcon, NavIcon } from "@/components/icons";

const navigation = [
  { label: "Overview", icon: "overview", href: "/", enabled: true },
  { label: "Tickets", icon: "tickets", href: "/tickets", enabled: true },
  {
    label: "Technicians",
    icon: "technicians",
    href: "/technicians",
    enabled: true,
  },
  { label: "Dispatch", icon: "dispatch", href: "/dispatch", enabled: true },
  { label: "Agent workspace", icon: "agent", href: "/agent", enabled: false },
  { label: "Approvals", icon: "approvals", href: "/approvals", enabled: false },
] as const;

function isActivePath(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand-lockup" href="/" aria-label="GeoOps AI overview">
          <MarkIcon />
          <div>
            <p className="brand-name">GeoOps</p>
            <p className="brand-subtitle">AI Operations</p>
          </div>
        </Link>

        <nav aria-label="Primary navigation" className="primary-nav">
          <p className="nav-eyebrow">Workspace</p>
          {navigation.map((item) => {
            const className = isActivePath(pathname, item.href)
              ? "nav-item nav-item-active"
              : "nav-item";
            return item.enabled ? (
              <Link
                aria-current={
                  isActivePath(pathname, item.href) ? "page" : undefined
                }
                className={className}
                href={item.href}
                key={item.label}
              >
                <NavIcon name={item.icon} />
                <span>{item.label}</span>
              </Link>
            ) : (
              <span aria-disabled="true" className={className} key={item.label}>
                <NavIcon name={item.icon} />
                <span>{item.label}</span>
                <span className="phase-dot" aria-label="Planned" />
              </span>
            );
          })}
        </nav>

        <div className="sidebar-note">
          <span className="sidebar-note-icon" aria-hidden="true">
            04
          </span>
          <div>
            <p>Maps routing</p>
            <span>Mock provider active</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <Link className="mobile-brand" href="/">
            <MarkIcon />
            <span>GeoOps AI</span>
          </Link>
          <nav className="mobile-nav" aria-label="Mobile navigation">
            <Link aria-current={pathname === "/" ? "page" : undefined} href="/">
              Overview
            </Link>
            <Link
              aria-current={
                pathname.startsWith("/tickets") ? "page" : undefined
              }
              href="/tickets"
            >
              Tickets
            </Link>
            <Link
              aria-current={
                pathname.startsWith("/technicians") ? "page" : undefined
              }
              href="/technicians"
            >
              Techs
            </Link>
            <Link
              aria-current={
                pathname.startsWith("/dispatch") ? "page" : undefined
              }
              href="/dispatch"
            >
              Dispatch
            </Link>
          </nav>
          <div className="environment-pill">
            <span className="environment-pulse" />
            Local dataset
          </div>
        </header>
        {children}
        <footer className="footer">
          <span>GeoOps AI · Phase 4</span>
          <span>Operational data is synthetic and deterministic</span>
        </footer>
      </main>
    </div>
  );
}
