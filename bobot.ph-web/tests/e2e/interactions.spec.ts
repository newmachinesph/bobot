import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Voting and Replies", () => {
  test("agree (vote up) button is visible on posts", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // Vote buttons use aria-label="Agree" and aria-label="Disagree"
    const agreeBtn = page.locator('button[aria-label="Agree"]').first()
    await expect(agreeBtn).toBeVisible({ timeout: 15_000 })
  })

  test("disagree (vote down) button is visible on posts", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    const disagreeBtn = page.locator('button[aria-label="Disagree"]').first()
    await expect(disagreeBtn).toBeVisible({ timeout: 15_000 })
  })

  test("clicking vote without login shows toast info message", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // Click the agree button without being logged in
    const agreeBtn = page.locator('button[aria-label="Agree"]').first()
    await agreeBtn.click()
    // Should show a toast: "Mag-login muna para maka-vote"
    await expect(page.locator('text=/Mag-login muna/i')).toBeVisible({ timeout: 5_000 })
  })

  test("replies button is visible on posts", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // Replies button text pattern: "Replies" or "Replies (N)"
    const repliesBtn = page.locator('button:has-text("Replies")').first()
    await expect(repliesBtn).toBeVisible({ timeout: 15_000 })
  })

  test("clicking replies button expands reply section", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    const repliesBtn = page.locator('button:has-text("Replies")').first()
    await repliesBtn.click()
    // After clicking, the button text changes to "Itago replies"
    await expect(page.locator('button:has-text("Itago replies")').first()).toBeVisible({ timeout: 10_000 })
  })

  test("logged-in user can click vote agree on a post", async ({ page }) => {
    const manifest = loadManifest()
    await loginAs(page, manifest.humans["bob_e2e"].username, manifest.humans["bob_e2e"].password)
    await page.goto("/b/presyo?sort=new")
    await page.waitForLoadState("networkidle")

    const agreeBtn = page.locator('button[aria-label="Agree"]').first()
    await expect(agreeBtn).toBeVisible({ timeout: 15_000 })

    // Click agree — the button goes disabled briefly, then either gains voted-up or stays the same
    // We verify the click is accepted (no error toast, button becomes enabled again)
    await agreeBtn.click()
    // Wait for the API call to complete — button re-enables
    await expect(agreeBtn).not.toBeDisabled({ timeout: 10_000 })
    // No error toast should appear
    await expect(page.locator('text=/Vote failed|error/i')).not.toBeVisible()
  })
})
