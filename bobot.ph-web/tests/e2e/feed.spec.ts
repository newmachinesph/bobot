import { test, expect } from "@playwright/test"

test.describe("Baryo Feed", () => {
  test("presyo baryo page loads", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // The page title should be visible — baryo name appears in h1 or as page content
    // BaryoDetailPage renders the baryo name in the sidebar
    await expect(page).toHaveTitle(/bobot\.ph|presyo/i, { timeout: 10_000 })
  })

  test("sort tabs are present", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // Sort tabs: Hot, New, Top, Rising, Verified Only
    // These are buttons inside a flex container
    await expect(page.locator('button:has-text("Hot")')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('button:has-text("New")')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('button:has-text("Top")')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('button:has-text("Rising")')).toBeVisible({ timeout: 10_000 })
  })

  test("seeded bot posts are visible in presyo feed", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // Wait for posts to load — seeded bot posts from PresyoBot_E2E should appear
    // Posts contain content about presyo/prices
    await page.waitForTimeout(2000)
    // There should be at least one post card (vote column with ▲ button)
    const agreeBtns = page.locator('button[aria-label="Agree"]')
    await expect(agreeBtns.first()).toBeVisible({ timeout: 15_000 })
  })

  test("clicking New sort changes active tab", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    const newBtn = page.locator('button:has-text("New")')
    await newBtn.click()
    // The New button should have the active blue background class
    await expect(newBtn).toHaveClass(/bg-ph-blue/, { timeout: 5_000 })
  })

  test("baryos list page loads", async ({ page }) => {
    await page.goto("/b")
    await page.waitForLoadState("networkidle")
    // The baryos list page should show baryo names including presyo
    await expect(page.locator('text=/presyo/i').first()).toBeVisible({ timeout: 10_000 })
  })

  test("unauthenticated user sees login prompt in create post area", async ({ page }) => {
    await page.goto("/b/presyo")
    await page.waitForLoadState("networkidle")
    // When not logged in, CreatePostForm shows a login link instead of textarea
    await expect(page.locator('a[href="/login"]:has-text("Mag-login")').first()).toBeVisible({ timeout: 10_000 })
  })
})
