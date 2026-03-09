import { expect, test } from "@playwright/test";

test("login and dashboard smoke flow", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();

  await page.getByLabel("Email").fill("operator@pqts.dev");
  await page.getByLabel("Session Token").fill("demo-token");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText("Tool Renderer Registry")).toBeVisible();
});

test("assistant and risk pages render", async ({ page, context }) => {
  await context.addCookies([
    {
      name: "pqts_session",
      value: "test-session",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      secure: false,
    },
  ]);

  await page.goto("/dashboard/assistant");
  await expect(page.getByRole("heading", { name: "Assistant Console" })).toBeVisible();
  await page.getByPlaceholder("Ask for a risk summary...").fill("risk summary");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Acknowledged. Summary generated for: risk summary")).toBeVisible();

  await page.goto("/dashboard/risk");
  await expect(page.getByRole("heading", { name: "Risk State" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Operator Actions" })).toBeVisible();
});
