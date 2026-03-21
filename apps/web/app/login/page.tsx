import Link from "next/link";

interface LoginPageProps {
  searchParams: Promise<{ next?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const resolved = await searchParams;
  const nextPath = resolved?.next && resolved.next.startsWith("/") ? resolved.next : "/dashboard";

  return (
    <main style={{ maxWidth: 520 }}>
      <section className="card">
        <h1>Sign In</h1>
        <p>Authenticate into the primary PQTS web surface. Use operator or admin tokens for trade and promotion writes.</p>
        <p style={{ color: "var(--muted)", marginTop: 0 }}>
          Dev tokens: <code>pqts-dev-viewer-token</code>, <code>pqts-dev-operator-token</code>, <code>pqts-dev-admin-token</code>
        </p>
        <form action="/api/auth/login" method="post" style={{ display: "grid", gap: 12 }}>
          <input type="hidden" name="next" value={nextPath} />
          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" required placeholder="operator@pqts.dev" />
          <label htmlFor="token">Session Token</label>
          <input id="token" name="token" type="password" required placeholder="paste temp token" />
          <button type="submit">Continue</button>
        </form>
        <p style={{ marginTop: 12, color: "var(--muted)" }}>
          Return to <Link href="/">home</Link>
        </p>
      </section>
    </main>
  );
}
