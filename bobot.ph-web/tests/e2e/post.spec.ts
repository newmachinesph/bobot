import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Post Creation", () => {
  test("logged-in user sees post composer textarea", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    // CreatePostForm shows a textarea with placeholder "Ano ang gusto mong ibahagi sa baryo?"
    const composer = page.locator('textarea[placeholder="Ano ang gusto mong ibahagi sa baryo?"]')
    await expect(composer).toBeVisible({ timeout: 10_000 })
  })

  test("post button is disabled when textarea is empty", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    // The submit button "Mag-post" is disabled when content is empty
    const submitBtn = page.locator('button:has-text("Mag-post")')
    await expect(submitBtn).toBeDisabled({ timeout: 10_000 })
  })

  test("can submit a post and it appears in feed", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")

    const uniqueText = `E2E Playwright test post ${Date.now()}`

    // Fill the textarea
    const textarea = page.locator('textarea[placeholder="Ano ang gusto mong ibahagi sa baryo?"]')
    await textarea.fill(uniqueText)

    // Submit button should now be enabled
    const submitBtn = page.locator('button:has-text("Mag-post")')
    await expect(submitBtn).toBeEnabled({ timeout: 5_000 })
    await submitBtn.click()

    // After submit, the post should appear in the feed
    await expect(page.locator(`text=${uniqueText}`)).toBeVisible({ timeout: 15_000 })
  })
})
