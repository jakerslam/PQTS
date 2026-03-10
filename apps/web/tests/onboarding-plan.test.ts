import { describe, expect, it } from "vitest";

import { buildOnboardingPlan } from "../lib/onboarding/plan";

describe("onboarding plan", () => {
  it("returns conservative risk profile for beginner flows", () => {
    const plan = buildOnboardingPlan({
      experience: "beginner",
      automation: "manual",
      capitalUsd: 5000,
    });
    expect(plan.riskProfile).toBe("conservative");
    expect(plan.commands).toContain("pqts paper start --risk-profile conservative");
  });

  it("returns aggressive profile only for advanced auto high-capital flow", () => {
    const plan = buildOnboardingPlan({
      experience: "advanced",
      automation: "auto",
      capitalUsd: 30000,
    });
    expect(plan.riskProfile).toBe("aggressive");
    expect(plan.commands).toContain("pqts paper start --risk-profile aggressive");
  });

  it("clamps invalid capital values before command rendering", () => {
    const plan = buildOnboardingPlan({
      experience: "intermediate",
      automation: "assisted",
      capitalUsd: Number.NaN,
    });
    expect(plan.commands).toContain(
      "pqts risk recommend --experience intermediate --capital-usd 1000 --automation assisted",
    );
  });
});
