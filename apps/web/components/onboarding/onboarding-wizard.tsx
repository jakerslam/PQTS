"use client";

import { useMemo, useState } from "react";
import type { OnboardingAutomation, OnboardingExperience } from "@/lib/onboarding/plan";
import { buildOnboardingPlan } from "@/lib/onboarding/plan";
import type { OnboardingRun } from "@/lib/onboarding/run-store";

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
  const [run, setRun] = useState<OnboardingRun | null>(null);
  const [runError, setRunError] = useState<string>("");
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

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

  const executePlan = async () => {
    if (isExecuting) {
      return;
    }
    setRunError("");
    setIsExecuting(true);
    setRun(null);
    try {
      const response = await fetch("/api/onboarding/execute", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          experience,
          automation,
          capitalUsd,
        }),
      });
      if (!response.ok) {
        setRunError("Failed to start onboarding run.");
        setIsExecuting(false);
        return;
      }
      const payload = (await response.json()) as { run: OnboardingRun };
      setRun(payload.run);
      const runId = payload.run.run_id;
      const poll = window.setInterval(async () => {
        try {
          const runResponse = await fetch(`/api/onboarding/runs/${runId}`, { method: "GET" });
          if (!runResponse.ok) {
            window.clearInterval(poll);
            setIsExecuting(false);
            return;
          }
          const runPayload = (await runResponse.json()) as { run: OnboardingRun };
          const latest = runPayload.run;
          setRun(latest);
          if (latest.status === "completed" || latest.status === "failed") {
            window.clearInterval(poll);
            setIsExecuting(false);
          }
        } catch {
          window.clearInterval(poll);
          setIsExecuting(false);
        }
      }, 1000);
    } catch {
      setRunError("Failed to start onboarding run.");
      setIsExecuting(false);
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

      <article className="card" style={{ background: "#f8fbff", display: "grid", gap: 8 }}>
        <h3 style={{ margin: 0 }}>Generated Config (UI → Code)</h3>
        <pre className="pqts-code-block" style={{ margin: 0 }}>
          <code>{JSON.stringify(plan.generatedConfig, null, 2)}</code>
        </pre>
        <p style={{ margin: 0, color: "var(--muted)" }}>
          Diff from prior default profile:
        </p>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {plan.uiToCliDiff.map((line) => (
            <li key={line}>
              <code>{line}</code>
            </li>
          ))}
        </ul>
      </article>

      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" onClick={handleCopy}>
          Copy commands
        </button>
        <button type="button" disabled={isExecuting} onClick={executePlan}>
          {isExecuting ? "Executing..." : "Run first success"}
        </button>
        {copyStatus ? <span style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{copyStatus}</span> : null}
      </div>
      {runError ? (
        <p style={{ margin: 0, color: "#c1121f" }}>{runError}</p>
      ) : null}

      {run ? (
        <article className="card" style={{ display: "grid", gap: 8 }}>
          <h3 style={{ margin: 0 }}>Run Progress: {run.run_id}</h3>
          <p style={{ margin: 0, color: "var(--muted)" }}>Status: {run.status}</p>
          {typeof run.first_meaningful_result_seconds === "number" ? (
            <p style={{ margin: 0, color: "var(--muted)" }}>
              Time to first meaningful result: {run.first_meaningful_result_seconds}s ·{" "}
              {run.meets_under_5_minute_goal ? "within 5-minute goal" : "outside 5-minute goal"}
            </p>
          ) : null}
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {run.steps.map((step) => (
              <li key={step.id}>
                <strong>{step.status.toUpperCase()}</strong> - <code>{step.command}</code>
                {step.artifact_path ? (
                  <span style={{ color: "var(--muted)" }}>{" -> "}{step.artifact_path}</span>
                ) : null}
              </li>
            ))}
          </ul>
          {run.artifacts.length > 0 ? (
            <p style={{ margin: 0, color: "var(--muted)" }}>
              Artifacts: {run.artifacts.join(", ")}
            </p>
          ) : null}
        </article>
      ) : null}

      <ul style={{ margin: 0, paddingLeft: 18 }}>
        {plan.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
