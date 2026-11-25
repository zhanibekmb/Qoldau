import { expect, test, type Page } from "@playwright/test";

const apiBase = process.env.E2E_API_URL || "http://127.0.0.1:8000";
const demoPassword = "Qoldau123!";

async function checkWidth(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize()!.width);
}

test("issued pilot account must change its password before opening a deep link", async ({ page, request }) => {
  const response = await request.post(`${apiBase}/api/v1/auth/login`, {
    data: { email: "admin@qoldau.edu.kz", password: demoPassword },
  });
  expect(response.ok()).toBeTruthy();
  const email = `pilot-browser-${Date.now()}@example.org`;
  const initial = "Pilot-browser-initial-24!";
  const replacement = "Pilot-browser-replacement-95!";
  const issued = await request.post(`${apiBase}/api/v1/admin/users`, {
    headers: { Authorization: `Bearer ${(await response.json()).access_token}` },
    data: { name: "Browser Pilot Student", email, role: "student", password: initial },
  });
  expect(issued.status()).toBe(201);
  await page.addInitScript(() => localStorage.setItem("qoldau.lang", "en"));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login?next=/requests/new");
  await expect(page.getByText(demoPassword)).toHaveCount(0);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(initial);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Set your password" })).toBeVisible();
  await checkWidth(page);
  await page.getByLabel("Temporary password").fill(initial);
  await page.getByLabel("New password", { exact: true }).fill(replacement);
  await page.getByLabel("Confirm new password").fill("Different-temporary-123!");
  await page.getByRole("button", { name: "Set your password" }).click();
  await expect(page.getByText("Passwords must match.", { exact: true })).toBeVisible();
  await page.getByLabel("Confirm new password").fill(replacement);
  await page.getByRole("button", { name: "Set your password" }).click();
  await expect(page).toHaveURL(/\/requests\/new$/);
  await expect(page.locator("#subject")).toBeVisible();
});

const copy = {
  en: { signIn: "Sign in", success: "Request submitted!", next: "Next step", view: "View request" },
  ru: { signIn: "Войти", success: "Обращение отправлено!", next: "Следующий шаг", view: "Открыть обращение" },
  kz: { signIn: "Кіру", success: "Өтініш жіберілді!", next: "Келесі қадам", view: "Өтінішті ашу" },
};

for (const [index, [lang, theme, width]] of ([
  ["en", "light", 390], ["ru", "dark", 390], ["kz", "light", 390],
  ["en", "dark", 768], ["ru", "light", 1440], ["kz", "dark", 390],
] as const).entries()) {
  test(`pilot student flow ${lang} ${theme} ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.addInitScript(({ lang, theme }) => {
      localStorage.setItem("qoldau.lang", lang);
      localStorage.setItem("qoldau.theme", theme);
    }, { lang, theme });
    const text = copy[lang];

    await page.goto("/");
    await expect(page.locator("#sla li")).toHaveCount(4);
    await checkWidth(page);
    await page.goto("/login?next=/requests/new");
    await page.locator("#email").fill(`student${index + 3}@qoldau.edu.kz`);
    await page.locator("#email").press("Tab");
    await expect(page.locator("#password")).toBeFocused();
    await page.locator("#password").fill(demoPassword);
    await page.getByRole("button", { name: text.signIn, exact: true }).click();
    await expect(page.locator("#subject")).toBeVisible();
    await expect(page.locator("html")).toHaveClass(theme === "dark" ? /\bdark\b/ : /^(?!.*\bdark\b).*$/);
    await expect(page.locator("input[type=file]")).toHaveCount(0);
    await page.getByRole("button", { name: "Submit request", exact: true }).click();
    await expect(page.locator("#category")).toBeFocused();

    await page.locator("#category").selectOption("auto");
    const subject = `Pilot ${lang} ${theme} ${Date.now()}`;
    await page.locator("#subject").fill(subject);
    await page.locator("#description").fill("My campus Wi-Fi does not connect and my university email account is locked.");
    await page.getByRole("button", { name: "Submit request", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: text.success });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/REQ-\d{4}-\d+/)).toBeVisible();
    await expect(dialog.getByText("IT Help Desk")).toBeVisible();
    await expect(dialog.getByText(text.next)).toBeVisible();
    await checkWidth(page);
    await dialog.getByRole("link", { name: text.view }).click();
    await expect(page.getByRole("heading", { name: subject })).toBeVisible();
    await expect(page.getByText(text.next, { exact: true })).toBeVisible();
    await expect(page.locator("input[type=file]")).toHaveCount(0);
    await checkWidth(page);
  });
}
