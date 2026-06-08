import { chromium } from "playwright"
import { mkdir } from "fs/promises"
import path from "path"
import { fileURLToPath } from "url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const docsDir = path.join(__dirname, "..", "docs")
const baseUrl = process.env.SCREENSHOT_BASE_URL || "http://157.230.51.229"
const email = process.env.SCREENSHOT_EMAIL || "nithish@immigraassist.com"
const password = process.env.SCREENSHOT_PASSWORD || "test1234"

await mkdir(docsDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
})
const page = await context.newPage()

async function login() {
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" })
  await page.waitForTimeout(800)
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.getByRole("button", { name: "Sign In" }).click()
  await page.waitForURL("**/chat**", { timeout: 30000 })
  await page.waitForTimeout(1500)
}

async function shot(name) {
  await page.screenshot({ path: path.join(docsDir, `${name}.png`) })
  console.log(`  ✓ ${name}.png`)
}

async function gotoApp(pathname) {
  await page.goto(`${baseUrl}${pathname}`, { waitUntil: "networkidle" })
  await page.waitForTimeout(2000)
}

console.log("Capturing screenshots from", baseUrl)

// ── Public pages ──
await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" })
await page.waitForTimeout(1200)
await shot("landing")

await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" })
await page.waitForTimeout(800)
await shot("login")

// ── Authenticated ──
await login()

await shot("chat-home")

const query = "What are the requirements for H4 EAD eligibility?"
await page.locator("textarea").first().fill(query)
await page.locator("textarea").first().press("Enter")
await page.waitForSelector("text=Searching policies and cases", { timeout: 20000 }).catch(() => {})
await page.waitForSelector("text=Searching policies and cases", { state: "hidden", timeout: 180000 }).catch(() => {})
await page.waitForTimeout(2500)
await shot("chat-response")

// Save to matter banner (no matter selected)
const saveBanner = page.getByRole("button", { name: /Save to matter/i }).first()
if (await saveBanner.isVisible().catch(() => false)) {
  await shot("chat-save-to-matter")
}

// ── Matters ──
await gotoApp("/matters")
await shot("matters")

const matterLink = page.locator('a[href^="/matters/"]').first()
if (await matterLink.count() > 0) {
  await matterLink.click()
  await page.waitForURL("**/matters/**", { timeout: 15000 })
  await page.waitForTimeout(2000)
  await shot("matter-detail")
}

// ── Research ──
await gotoApp("/research")
await shot("research-hubs")

await gotoApp("/research/h1b")
await shot("research-visa-h1b")

// ── Admin pages ──
await gotoApp("/eval")
await page.waitForSelector("text=Evaluation Dashboard", { timeout: 15000 }).catch(() => {})
await page.waitForTimeout(3000)
await shot("eval-dashboard")

await gotoApp("/reviews")
await shot("review-queue")

await gotoApp("/alerts")
await shot("policy-alerts")

await gotoApp("/documents")
await shot("documents")

await gotoApp("/admin")
await shot("admin-dashboard")

await gotoApp("/users")
await shot("team-users")

await gotoApp("/audit")
await shot("audit-logs")

await browser.close()
console.log(`\nDone — ${docsDir}/`)
