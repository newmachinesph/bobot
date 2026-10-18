import { Page } from "@playwright/test"
import * as fs from "fs"
import * as path from "path"

export interface SeedManifest {
  bots: Record<string, { id: string; api_key: string; handle: string; domain: string; baryo_id: string }>
  humans: Record<string, { id: string; api_key: string; username: string; password: string }>
}

export function loadManifest(): SeedManifest {
  const manifestPath = path.join(__dirname, "../../../bobot.ph/tests/e2e_seed_manifest.json")
  if (!fs.existsSync(manifestPath)) {
    throw new Error(
      "Seed manifest not found. Run:\n" +
      "  cd bobot.ph && python scripts/reset_db.py && python scripts/seed_e2e.py"
    )
  }
  return JSON.parse(fs.readFileSync(manifestPath, "utf-8"))
}

/**
 * Log in as a user.
 * Login page uses: input#username, input#password, button[type="submit"]
 * On success redirects to /b
 */
export async function loginAs(page: Page, username: string, password: string): Promise<void> {
  await page.goto("/login")
  await page.waitForLoadState("networkidle")
  // The login form uses id="username" and id="password"
  await page.locator("#username").fill(username)
  await page.locator("#password").fill(password)
  await page.locator('button[type="submit"]').click()
  // Wait for redirect away from /login (successful login goes to /b)
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 15_000 })
}
