import { test, expect } from "@playwright/test"
import { loadManifest, loginAs } from "./helpers"

test.describe("Authentication", () => {
  test("register page loads", async ({ page }) => {
    await page.goto("/register")
    // Use the register form specifically (has the border class), not the nav search form
    await expect(page.locator("form.bg-white")).toBeVisible({ timeout: 10_000 })
  })

  test("register page has all expected fields", async ({ page }) => {
    await page.goto("/register")
    await page.waitForLoadState("networkidle")
    // Register form has: #username, #email, #password, #region (select), terms checkbox
    await expect(page.locator("#username")).toBeVisible()
    await expect(page.locator("#email")).toBeVisible()
    await expect(page.locator("#password")).toBeVisible()
  })

  test("login with wrong password stays on login", async ({ page }) => {
    const manifest = loadManifest()
    await page.goto("/login")
    await page.waitForLoadState("networkidle")
    // Login form uses id="username" and id="password"
    await page.locator("#username").fill(manifest.humans["alice_e2e"].username)
    await page.locator("#password").fill("wrongpassword999")
    await page.locator('button[type="submit"]').click()
    // Should stay on login or show error message
    await page.waitForTimeout(2000)
    const url = page.url()
    expect(url).toContain("login")
    // Also expect the error message in Filipino
    await expect(page.locator("text=Mali ang username o password")).toBeVisible({ timeout: 5_000 })
  })

  test("login success redirects away from login", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    // After successful login, redirected to /b
    expect(page.url()).not.toContain("/login")
  })

  test("logged-in nav shows username and logout", async ({ page }) => {
    const manifest = loadManifest()
    const alice = manifest.humans["alice_e2e"]
    await loginAs(page, alice.username, alice.password)
    // NavBar shows the logged-in user's name and a Logout button
    await expect(page.locator(`text=${alice.username}`)).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('button:has-text("Logout")')).toBeVisible()
  })
})
