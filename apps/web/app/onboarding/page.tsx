import Link from "next/link";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";

export default function OnboardingPage() {
  return (
    <main>
      <header className="card" style={{ marginBottom: 16 }}>
        <h1 style={{ marginTop: 0 }}>PQTS Onboarding</h1>
        <p style={{ marginBottom: 0, color: "var(--muted)" }}>
          Browser-first setup that maps directly to CLI equivalents while preserving promotion safety gates.
        </p>
      </header>

      <OnboardingWizard />

      <section className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginTop: 0 }}>Next steps</h3>
        <p style={{ marginBottom: 0 }}>
          For advanced workflows, continue in{" "}
          <Link href="/dashboard">Dashboard</Link> or review{" "}
          <Link href="https://github.com/jakerslam/pqts/blob/main/docs/QUICKSTART_5_MIN.md">Quickstart docs</Link>.
        </p>
      </section>
    </main>
  );
}
