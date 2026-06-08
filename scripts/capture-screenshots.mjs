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

// Landing page
await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" })
await page.waitForTimeout(1000)
await shot("landing")

// Login
await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" })
await page.waitForTimeout(800)
await shot("login")

await login()
await shot("chat-home")

const query = "What are the requirements for H4 EAD eligibility?"
await page.locator("textarea").first().fill(query)
await page.locator("textarea").first().press("Enter")
await page.waitForSelector("text=Searching policies and cases", { timeout: 20000 }).catch(() => {})
await page.waitForSelector("text=Searching policies and cases", { state: "hidden", timeout: 180000 }).catch(() => {})
await page.waitForTimeout(2000)
await shot("chat-response")
await shot("demo")

await page.goto(`${baseUrl}/matters`, { waitUntil: "networkidle" })
await page.waitForTimeout(1500)
await shot("matters")

await page.goto(`${baseUrl}/research`, { waitUntil: "networkidle" })
await page.waitForTimeout(1500)
await shot("research-hubs")

await page.goto(`${baseUrl}/eval`, { waitUntil: "networkidle" })
await page.waitForTimeout(2500)
await shot("eval-dashboard")

await page.goto(`${baseUrl}/reviews`, { waitUntil: "networkidle" })
await page.waitForTimeout(1500)
await shot("review-queue")

await page.goto(`${baseUrl}/alerts`, { waitUntil: "networkidle" })
await page.waitForTimeout(1500)
await shot("policy-alerts")

await browser.close()
console.log(`\nScreenshots saved to ${docsDir}/`)
