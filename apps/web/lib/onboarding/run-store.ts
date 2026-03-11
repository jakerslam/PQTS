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
  started_at?: string;
  completed_at?: string;
  status: OnboardingRunStatus;
  steps: OnboardingStep[];
  artifacts: string[];
  first_meaningful_result_seconds?: number;
  meets_under_5_minute_goal?: boolean;
}

