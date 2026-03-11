"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CommandPalette } from "@/components/command-palette";
import { TrustStatusBar } from "@/components/trust/trust-status-bar";
import type { TrustStatusSnapshot, UiDensityMode } from "@/lib/system/trust-status";

interface Props {
  children: React.ReactNode;
  trustSnapshot: TrustStatusSnapshot;
}

interface NavEntry {
  label: string;
  href: string;
  description: string;
  minMode?: UiDensityMode;
}

const NAV_ENTRIES: NavEntry[] = [
  { label: "Home", href: "/dashboard", description: "Command center and next action." },
  { label: "Strategy Lab", href: "/dashboard/strategy-lab", description: "Guided templates and metrics.", minMode: "guided" },
  { label: "Portfolio", href: "/dashboard/portfolio", description: "Positions, balances, and allocation." },
  { label: "Execution", href: "/dashboard/execution", description: "Live orders, fills, and tape." },
  { label: "Risk", href: "/dashboard/risk", description: "Guardrails, incidents, and controls." },
  { label: "Promotions", href: "/dashboard/promotion", description: "Stage-gate controls and evidence." },
  { label: "Benchmarks", href: "/dashboard/benchmarks", description: "Reference bundles and trust labels." },
  { label: "Alerts", href: "/dashboard/alerts", description: "Notification checks and incidents." },
  { label: "Settings", href: "/dashboard/settings", description: "Integrations and deployment context." },
  { label: "Order Truth", href: "/dashboard/order-truth", description: "Per-order lineage and explanation.", minMode: "pro" },
  { label: "Replay", href: "/dashboard/replay", description: "Deterministic replay timeline.", minMode: "pro" },
  { label: "Templates", href: "/dashboard/templates", description: "Template artifacts and diffs.", minMode: "pro" },
  { label: "Assistant", href: "/dashboard/assistant", description: "Constrained assistant workflows.", minMode: "pro" },
];

function modeRank(mode: UiDensityMode): number {
  return mode === "pro" ? 2 : 1;
}

export function DashboardShell({ children, trustSnapshot }: Props) {
  const [densityMode, setDensityMode] = useState<UiDensityMode>("guided");
  const [role, setRole] = useState<string>("viewer");

  useEffect(() => {
    const stored = window.localStorage.getItem("pqts_density_mode");
    if (stored === "pro" || stored === "guided") {
      setDensityMode(stored);
    }
    const roleStored = window.localStorage.getItem("pqts_role");
    if (roleStored) {
      setRole(roleStored);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("pqts_density_mode", densityMode);
    document.body.dataset.pqtsDensity = densityMode;
  }, [densityMode]);

  useEffect(() => {
    window.localStorage.setItem("pqts_role", role);
  }, [role]);

  const visibleNav = useMemo(
    () =>
      NAV_ENTRIES.filter((entry) => {
        const minMode = entry.minMode ?? "guided";
        return modeRank(densityMode) >= modeRank(minMode);
      }),
    [densityMode]
  );

  return (
    <main>
      <header className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div>
            <h1 style={{ margin: 0 }}>PQTS Dashboard</h1>
            <p style={{ margin: "6px 0 0", color: "var(--muted)" }}>
              Primary web surface (Studio) · role:{role}
            </p>
          </div>
          <nav style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {visibleNav.map((entry) => (
              <Link key={entry.href} href={entry.href} title={entry.description}>
                {entry.label}
              </Link>
            ))}
            <Link href="/onboarding">Onboarding</Link>
            <button
              type="button"
              className="inline-link-button"
              onClick={() => setDensityMode((current) => (current === "guided" ? "pro" : "guided"))}
              aria-label="Toggle guided/pro density mode"
            >
              mode:{densityMode}
            </button>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              role
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="viewer">viewer</option>
                <option value="operator">operator</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <CommandPalette commands={NAV_ENTRIES} densityMode={densityMode} />
            <form action="/api/auth/logout" method="post">
              <button type="submit">Sign Out</button>
            </form>
          </nav>
        </div>
      </header>
      <TrustStatusBar snapshot={trustSnapshot} densityMode={densityMode} />
      {children}
    </main>
  );
}
