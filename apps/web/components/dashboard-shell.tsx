"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
  section: "trade" | "ops";
}

interface AuthMePayload {
  identity?: {
    role?: string;
  };
}

const NAV_ENTRIES: NavEntry[] = [
  { label: "Terminal", href: "/dashboard", description: "Primary quant desk with core execution displays.", section: "trade" },
  { label: "Execution", href: "/dashboard/execution", description: "Live orders, fills, and ticket workflow.", section: "trade" },
  { label: "Portfolio", href: "/dashboard/portfolio", description: "Balances, positions, and exposure.", section: "trade" },
  { label: "Risk", href: "/dashboard/risk", description: "Guardrails, incidents, and controls.", section: "trade" },
  { label: "Promotions", href: "/dashboard/promotion", description: "Stage-gate controls and evidence.", section: "trade" },
  { label: "Benchmarks", href: "/dashboard/benchmarks", description: "Reference bundles and trust labels.", section: "trade" },
  { label: "Order Truth", href: "/dashboard/order-truth", description: "Per-order lineage and explanation.", minMode: "pro", section: "ops" },
  { label: "Replay", href: "/dashboard/replay", description: "Deterministic replay timeline.", minMode: "pro", section: "ops" },
  { label: "Strategy Lab", href: "/dashboard/strategy-lab", description: "Template guidance and artifact links.", section: "ops" },
  { label: "Assistant", href: "/dashboard/assistant", description: "Constrained assistant workflows.", minMode: "pro", section: "ops" },
  { label: "Templates", href: "/dashboard/templates", description: "Template artifacts and diffs.", minMode: "pro", section: "ops" },
  { label: "Alerts", href: "/dashboard/alerts", description: "Notification checks and incidents.", section: "ops" },
  { label: "Settings", href: "/dashboard/settings", description: "Integrations and deployment context.", section: "ops" },
];

function modeRank(mode: UiDensityMode): number {
  return mode === "pro" ? 2 : 1;
}

export function DashboardShell({ children, trustSnapshot }: Props) {
  const pathname = usePathname();
  const [densityMode, setDensityMode] = useState<UiDensityMode>("guided");
  const [role, setRole] = useState<string>("viewer");
  const [clock, setClock] = useState<string>("");

  useEffect(() => {
    const stored = window.localStorage.getItem("pqts_density_mode");
    if (stored === "pro" || stored === "guided") {
      setDensityMode(stored);
    }
    const roleStored = window.localStorage.getItem("pqts_role");
    if (roleStored) {
      setRole(roleStored);
    }
    void fetch("/api/auth/me", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        const roleValue = (payload as AuthMePayload | null)?.identity?.role;
        if (roleValue && ["viewer", "operator", "admin"].includes(roleValue)) {
          setRole(roleValue);
        }
      })
      .catch(() => {
        // Keep local role fallback when auth endpoint is unavailable.
      });
  }, []);

  useEffect(() => {
    window.localStorage.setItem("pqts_density_mode", densityMode);
    document.body.dataset.pqtsDensity = densityMode;
  }, [densityMode]);

  useEffect(() => {
    window.localStorage.setItem("pqts_role", role);
  }, [role]);

  useEffect(() => {
    const update = () => setClock(new Date().toLocaleString());
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const visibleNav = useMemo(
    () =>
      NAV_ENTRIES.filter((entry) => {
        const minMode = entry.minMode ?? "guided";
        return modeRank(densityMode) >= modeRank(minMode);
      }),
    [densityMode]
  );

  const tradeNav = visibleNav.filter((entry) => entry.section === "trade");
  const opsNav = visibleNav.filter((entry) => entry.section === "ops");

  return (
    <div className="studio-shell">
      <aside className="studio-sidebar">
        <div className="studio-brand">
          <p className="studio-brand-eyebrow">PQTS</p>
          <h1>Quant Desk</h1>
          <p>Production console for research, risk, execution, and promotion gates.</p>
        </div>

        <section className="studio-nav-section">
          <h2>Trading</h2>
          <nav className="studio-nav">
            {tradeNav.map((entry) => {
              const active = entry.href === "/dashboard" ? pathname === entry.href : Boolean(pathname?.startsWith(entry.href));
              return (
                <Link
                  key={entry.href}
                  href={entry.href}
                  title={entry.description}
                  className={`studio-nav-link ${active ? "studio-nav-link-active" : ""}`}
                >
                  <span>{entry.label}</span>
                  <small>{entry.description}</small>
                </Link>
              );
            })}
          </nav>
        </section>

        <section className="studio-nav-section">
          <h2>Operations</h2>
          <nav className="studio-nav">
            {opsNav.map((entry) => {
              const active = Boolean(pathname?.startsWith(entry.href));
              return (
                <Link
                  key={entry.href}
                  href={entry.href}
                  title={entry.description}
                  className={`studio-nav-link ${active ? "studio-nav-link-active" : ""}`}
                >
                  <span>{entry.label}</span>
                  <small>{entry.description}</small>
                </Link>
              );
            })}
          </nav>
        </section>

        <section className="studio-sidebar-controls">
          <label>
            role
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="viewer">viewer</option>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <button
            type="button"
            className="inline-link-button"
            onClick={() => setDensityMode((current) => (current === "guided" ? "pro" : "guided"))}
            aria-label="Toggle guided/pro density mode"
          >
            density: {densityMode}
          </button>
          <Link href="/onboarding">Open onboarding</Link>
        </section>
      </aside>

      <div className="studio-main">
        <header className="card studio-topbar">
          <div>
            <h2 style={{ margin: 0 }}>Trading Terminal</h2>
            <p style={{ margin: "6px 0 0", color: "var(--muted)" }}>
              Live operator surface · role:{role}
            </p>
          </div>
          <div className="studio-topbar-controls">
            <p>{clock}</p>
            <CommandPalette commands={NAV_ENTRIES} densityMode={densityMode} />
            <form action="/api/auth/logout" method="post">
              <button type="submit">Sign Out</button>
            </form>
          </div>
        </header>
        <TrustStatusBar snapshot={trustSnapshot} densityMode={densityMode} />
        <section className="studio-content">{children}</section>
      </div>
    </div>
  );
}
