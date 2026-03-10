"use client";

import { useMemo, useState } from "react";
import type { OnboardingAutomation, OnboardingExperience } from "@/lib/onboarding/plan";
import { buildOnboardingPlan } from "@/lib/onboarding/plan";

const EXPERIENCE_OPTIONS: Array<{ value: OnboardingExperience; label: string }> = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const AUTOMATION_OPTIONS: Array<{ value: OnboardingAutomation; label: string }> = [
  { value: "manual", label: "Manual" },
  { value: "assisted", label: "Assisted" },
  { value: "auto", label: "Auto" },
];

export function OnboardingWizard() {
  const [experience, setExperience] = useState<OnboardingExperience>("beginner");
  const [automation, setAutomation] = useState<OnboardingAutomation>("manual");
  const [capitalUsd, setCapitalUsd] = useState<number>(5000);
  const [copyStatus, setCopyStatus] = useState<string>("");

  const plan = useMemo(
    () =>
      buildOnboardingPlan({
        experience,
        automation,
        capitalUsd,
      }),
    [automation, capitalUsd, experience]
  );

  const commandBlock = plan.commands.join("\n");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(commandBlock);
      setCopyStatus("Command block copied.");
    } catch {
      setCopyStatus("Copy failed. Select and copy commands manually.");
    }
  };

  return (
    <section className="card" style={{ display: "grid", gap: 16 }}>
      <h2 style={{ margin: 0 }}>5-Minute Onboarding Wizard</h2>
      <p style={{ margin: 0, color: "var(--muted)" }}>
        Generate a safe paper-trading plan using existing `pqts` command flows.
      </p>

      <div className="grid">
        <label style={{ display: "grid", gap: 6 }}>
          Experience
          <select
            value={experience}
            onChange={(event) => setExperience(event.target.value as OnboardingExperience)}
          >
            {EXPERIENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          Automation
          <select
            value={automation}
            onChange={(event) => setAutomation(event.target.value as OnboardingAutomation)}
          >
            {AUTOMATION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          Capital (USD)
          <input
            type="number"
            min={100}
            step={100}
            value={capitalUsd}
            onChange={(event) => setCapitalUsd(Number(event.target.value))}
          />
        </label>
      </div>

      <article className="card" style={{ background: "#f8fbff" }}>
        <p style={{ margin: 0 }}>
          Recommended risk profile: <strong>{plan.riskProfile}</strong>
        </p>
      </article>

      <pre className="pqts-code-block">
        <code>{commandBlock}</code>
      </pre>

      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" onClick={handleCopy}>
          Copy commands
        </button>
        {copyStatus ? <span style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{copyStatus}</span> : null}
      </div>

      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {plan.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
