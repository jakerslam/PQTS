export type OnboardingExperience = "beginner" | "intermediate" | "advanced";
export type OnboardingAutomation = "manual" | "assisted" | "auto";

export interface OnboardingInput {
  experience: OnboardingExperience;
  capitalUsd: number;
  automation: OnboardingAutomation;
}

export interface OnboardingPlan {
  riskProfile: "conservative" | "balanced" | "aggressive";
  commands: string[];
  notes: string[];
}

function clampCapital(capitalUsd: number): number {
  if (!Number.isFinite(capitalUsd)) {
    return 1000;
  }
  return Math.max(100, Math.round(capitalUsd));
}

function inferRiskProfile(input: OnboardingInput): "conservative" | "balanced" | "aggressive" {
  if (input.experience === "advanced" && input.automation === "auto" && input.capitalUsd >= 25000) {
    return "aggressive";
  }
  if (input.experience === "beginner") {
    return "conservative";
  }
  return "balanced";
}

export function buildOnboardingPlan(input: OnboardingInput): OnboardingPlan {
  const capitalUsd = clampCapital(input.capitalUsd);
  const normalizedInput: OnboardingInput = {
    ...input,
    capitalUsd,
  };
  const riskProfile = inferRiskProfile(normalizedInput);
  const commands = [
    "pqts doctor --fix",
    "pqts quickstart --execute",
    `pqts risk recommend --experience ${normalizedInput.experience} --capital-usd ${capitalUsd} --automation ${normalizedInput.automation}`,
    `pqts paper start --risk-profile ${riskProfile}`,
    "pqts status readiness",
    "pqts status leaderboard",
  ];
  const notes = [
    "The wizard generates CLI-first steps so every UI action stays code-visible.",
    "Run paper mode before any canary/live stage and preserve generated artifacts for promotion evidence.",
  ];
  return {
    riskProfile,
    commands,
    notes,
  };
}
