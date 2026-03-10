import Link from "next/link";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <main>
      <header className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ margin: 0 }}>PQTS Dashboard</h1>
            <p style={{ margin: "6px 0 0", color: "var(--muted)" }}>Authenticated operator workspace</p>
          </div>
          <nav style={{ display: "flex", gap: 12 }}>
            <Link href="/dashboard">Overview</Link>
            <Link href="/onboarding">Onboarding</Link>
            <Link href="/dashboard/portfolio">Portfolio</Link>
            <Link href="/dashboard/execution">Execution</Link>
            <Link href="/dashboard/risk">Risk</Link>
            <Link href="/dashboard/assistant">Assistant</Link>
            <form action="/api/auth/logout" method="post">
              <button type="submit">Sign Out</button>
            </form>
          </nav>
        </div>
      </header>
      {children}
    </main>
  );
}
