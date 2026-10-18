import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Messages", () => {
  test("unauthenticated user sees login prompt on messages page", async ({ page }) => {
    await page.goto("/messages")
    await page.waitForLoadState("networkidle")
    // MessagesPage shows: h1 "Messages" + "Login to view your messages." + Login button link
    // when session is null
    await expect(page.locator('h1:has-text("Messages")')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('text=Login to view your messages.')).toBeVisible({ timeout: 5_000 })
    // The login link in the main content area (not nav) — scoped to main
    await expect(page.locator('main a[href="/login"], [role="main"] a[href="/login"]').first()).toBeVisible({ timeout: 5_000 })
  })

  test("messages page loads for logged-in user", async ({ page }) => {
    const manifest = loadManifest()
    await loginAs(page, manifest.humans["alice_e2e"].username, manifest.humans["alice_e2e"].password)

    await page.goto("/messages")
    await page.waitForLoadState("networkidle")

    // Page should show "Messages" heading and tabs (Inbox, Requests, New Message)
    await expect(page.locator('h1:has-text("Messages")')).toBeVisible({ timeout: 10_000 })
  })

  test("messages page shows inbox, requests, and new message tabs", async ({ page }) => {
    const manifest = loadManifest()
    await loginAs(page, manifest.humans["alice_e2e"].username, manifest.humans["alice_e2e"].password)

    await page.goto("/messages")
    await page.waitForLoadState("networkidle")

    // The 3 tabs: Inbox, Requests, New Message
    await expect(page.locator('button:has-text("Inbox")')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('button:has-text("Requests")')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('button:has-text("New Message")')).toBeVisible({ timeout: 10_000 })
  })

  test("switching to New Message tab shows compose form", async ({ page }) => {
    const manifest = loadManifest()
    await loginAs(page, manifest.humans["alice_e2e"].username, manifest.humans["alice_e2e"].password)

    await page.goto("/messages")
    await page.waitForLoadState("networkidle")

    // Click New Message tab
    await page.locator('button:has-text("New Message")').click()
    // Should show a form to send a message request
    await expect(page.locator('input[placeholder]').first()).toBeVisible({ timeout: 5_000 })
  })
})
