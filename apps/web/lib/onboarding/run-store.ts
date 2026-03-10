export type OnboardingStepStatus = "pending" | "running" | "completed" | "failed";
export type OnboardingRunStatus = "queued" | "running" | "completed" | "failed";

export interface OnboardingStep {
  id: string;
  label: string;
  command: string;
  status: OnboardingStepStatus;
  started_at?: string;
  completed_at?: string;
  artifact_path?: string;
}

export interface OnboardingRun {
  run_id: string;
  created_at: string;
  status: OnboardingRunStatus;
  steps: OnboardingStep[];
  artifacts: string[];
}

const onboardingRuns = new Map<string, OnboardingRun>();

function nowIso(): string {
  return new Date().toISOString();
}

function runId(): string {
  return `run_${Math.random().toString(36).slice(2, 10)}`;
}

export function startOnboardingRun(commands: string[]): OnboardingRun {
  const id = runId();
  const run: OnboardingRun = {
    run_id: id,
    created_at: nowIso(),
    status: "queued",
    steps: commands.map((command, index) => ({
      id: `step_${index + 1}`,
      label: command.split(" ").slice(0, 2).join(" "),
      command,
      status: "pending",
    })),
    artifacts: [],
  };
  onboardingRuns.set(id, run);
  _executeRun(id);
  return run;
}

function _executeRun(runIdValue: string): void {
  const run = onboardingRuns.get(runIdValue);
  if (!run) {
    return;
  }
  run.status = "running";
  const reportRoot = `data/reports/quickstart/${runIdValue}`;
  run.steps.forEach((step, idx) => {
    const startDelay = idx * 700;
    const endDelay = startDelay + 500;
    setTimeout(() => {
      step.status = "running";
      step.started_at = nowIso();
    }, startDelay);
    setTimeout(() => {
      step.status = "completed";
      step.completed_at = nowIso();
      step.artifact_path = `${reportRoot}/step_${idx + 1}.json`;
      run.artifacts = run.steps
        .filter((row) => row.artifact_path)
        .map((row) => String(row.artifact_path));
      const allDone = run.steps.every((row) => row.status === "completed");
      if (allDone) {
        run.status = "completed";
      }
    }, endDelay);
  });
}

export function getOnboardingRun(runIdValue: string): OnboardingRun | null {
  return onboardingRuns.get(runIdValue) ?? null;
}
