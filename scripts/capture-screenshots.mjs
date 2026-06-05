import { chromium } from "playwright"
import { mkdir } from "fs/promises"
import path from "path"
import { fileURLToPath } from "url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const docsDir = path.join(__dirname, "..", "docs")
const baseUrl = "http://157.230.51.229"
const email = "nithish@immigraassist.com"
const password = "test1234"

await mkdir(docsDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
})
const page = await context.newPage()

async function login() {
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" })
  await page.waitForTimeout(1000)
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.getByRole("button", { name: "Sign In" }).click()
  await page.waitForURL("**/chat**", { timeout: 30000 })
  await page.waitForTimeout(2000)
}

// Login page
await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" })
await page.waitForTimeout(1000)
await page.screenshot({ path: path.join(docsDir, "login.png") })

// Chat home
await login()
await page.screenshot({ path: path.join(docsDir, "chat-home.png") })

// Submit question and wait for answer
const query = "What are the requirements for H4 EAD eligibility?"
await page.locator("textarea").first().fill(query)
await page.locator("textarea").first().press("Enter")

// Wait for loading indicator then answer
await page.waitForSelector("text=Searching policies and cases", { timeout: 15000 })
await page.waitForSelector("text=Searching policies and cases", { state: "hidden", timeout: 180000 })
await page.waitForTimeout(2500)

await page.screenshot({ path: path.join(docsDir, "chat-response.png") })
await page.screenshot({ path: path.join(docsDir, "demo.png") })

await browser.close()
console.log("Screenshots saved to docs/")
