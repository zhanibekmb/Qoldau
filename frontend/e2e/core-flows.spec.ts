import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBase = process.env.E2E_API_URL || "http://127.0.0.1:8000";
const password = "Qoldau123!";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("qoldau.lang", "en"));
});

async function signIn(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
}

async function apiToken(request: APIRequestContext, email: string): Promise<string> {
  const response = await request.post(`${apiBase}/api/v1/auth/login`, { data: { email, password } });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).access_token as string;
}

test("student submits, tracks and messages on a request", async ({ page }) => {
  await signIn(page, "student@qoldau.edu.kz");
  await page.goto("/requests/new");
  const subject = `E2E student request ${Date.now()}`;
  await page.getByLabel("Category").selectOption("auto");
  await page.getByLabel("Subject").fill(subject);
  await page.getByLabel("Description").fill("My campus Wi-Fi does not connect on my laptop today. Please help me restore access.");
  await page.getByRole("button", { name: "Submit request" }).click();
  const confirmation = page.getByRole("dialog", { name: "Request submitted!" });
  await expect(confirmation).toBeVisible();
  await confirmation.getByRole("link", { name: "View request" }).click();
  await expect(page.getByRole("heading", { name: subject })).toBeVisible();
  await expect(page).toHaveURL(/\/requests\/REQ-\d{4}-\d+/);

  const message = `Student follow-up ${Date.now()}`;
  await page.getByRole("textbox", { name: "Write a message…" }).fill(message);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(message)).toBeVisible();
});

test("agent starts work and replies on a routed request", async ({ page, request }) => {
  const token = await apiToken(request, "student@qoldau.edu.kz");
  const subject = `E2E agent request ${Date.now()}`;
  const created = await request.post(`${apiBase}/api/v1/requests`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { subject, description: "The campus Wi-Fi does not connect on my laptop and my university email account is locked." },
  });
  expect(created.status()).toBe(201);
  const item = await created.json();
  expect(item.unit.name).toBe("IT Help Desk");

  await signIn(page, "agent1.it@qoldau.edu.kz");
  await page.goto(`/requests/${item.id}`);
  await expect(page.getByRole("heading", { name: subject })).toBeVisible();
  await page.getByRole("button", { name: "Start work" }).click();
  await page.getByRole("button", { name: "Confirm: In Progress" }).click();
  await expect(page.getByText("In Progress", { exact: true }).first()).toBeVisible();

  const reply = `Agent reply ${Date.now()}`;
  await page.getByRole("textbox", { name: "Write a message…" }).fill(reply);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(reply)).toBeVisible();
});

test("admin publishes a knowledge-base article", async ({ page, request }) => {
  await signIn(page, "admin@qoldau.edu.kz");
  await page.goto("/kb");
  await page.getByRole("button", { name: "New article" }).click();
  const editor = page.getByRole("dialog", { name: "New article" });
  await expect(editor).toBeVisible();
  await editor.getByRole("tab", { name: /^EN/ }).click();
  const title = `E2E FAQ ${Date.now()}`;
  await editor.getByLabel("Title").fill(title);
  await editor.getByRole("textbox", { name: "Answer" }).fill("This article explains how students can contact the IT Help Desk for campus access.");
  await editor.getByRole("button", { name: "Publish" }).click();
  await expect(editor.getByText("Published", { exact: true })).toBeVisible();

  const token = await apiToken(request, "admin@qoldau.edu.kz");
  const articles = await request.get(`${apiBase}/api/v1/admin/faq?q=${encodeURIComponent(title)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(articles.ok()).toBeTruthy();
  expect((await articles.json()).items.some((row: { title: string; status: string }) => row.title === title && row.status === "published")).toBeTruthy();
});

test("admin creates and removes a configuration keyword", async ({ page }) => {
  await signIn(page, "admin@qoldau.edu.kz");
  await page.goto("/admin");
  await page.getByRole("tab", { name: "Urgency keywords" }).click();
  await page.getByRole("button", { name: "Add" }).click();
  const editor = page.getByRole("dialog", { name: "Add: Urgency keywords" });
  const keyword = `e2e-keyword-${Date.now()}`;
  await editor.getByLabel("Keyword").fill(keyword);
  await editor.getByRole("button", { name: "Save" }).click();
  const row = page.getByRole("row").filter({ hasText: keyword });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Delete" }).click();
  await expect(row).toHaveCount(0);
});

test("admin exports analytics and downloads the report", async ({ page, request }) => {
  await signIn(page, "admin@qoldau.edu.kz");
  await page.goto("/analytics");
  await page.getByRole("button", { name: "Export" }).click();
  await page.getByRole("menuitem", { name: "Excel (.xlsx)" }).click();
  await expect(page.getByText("Export started. You will be notified when it is ready.")).toBeVisible();
  await page.goto("/reports");
  const download = page.getByRole("link", { name: /Download/ }).first();
  await expect(download).toBeVisible({ timeout: 30_000 });
  const response = await request.get((await download.getAttribute("href"))!);
  expect(response.ok()).toBeTruthy();
  expect((await response.body()).subarray(0, 2).toString()).toBe("PK");
});
