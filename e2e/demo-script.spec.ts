import { test, expect, Page } from '@playwright/test';

const WEB = process.env.WEB_URL ?? 'http://172.17.0.1:3000';
const API = process.env.API_URL ?? 'http://172.17.0.1:8000';

type DemoScenario = {
  id: string;
  category: string;
  document_id: string | null;
  name: string;
};

async function resetDemo(page: Page) {
  const res = await page.request.post(`${API}/api/v1/demo/reset`, {
    headers: { 'X-GovDoc-Role': 'supervisor' },
  });
  expect(res.ok(), `demo/reset failed: ${res.status()} ${await res.text()}`).toBeTruthy();
}

async function fetchScenarios(page: Page): Promise<Record<string, DemoScenario>> {
  const res = await page.request.get(`${API}/api/v1/demo/scenarios`);
  expect(res.ok(), `demo/scenarios failed: ${res.status()} ${await res.text()}`).toBeTruthy();
  const scenarios = (await res.json()) as DemoScenario[];
  return Object.fromEntries(scenarios.map((scenario) => [scenario.category, scenario]));
}

async function switchRole(page: Page, role: string) {
  await page.locator('header select').selectOption(role);
  await expect(page.locator('header select')).toHaveValue(role);
}

test('scripted demo flow is performable from seeded scenarios', async ({ page }) => {
  test.setTimeout(240_000);

  await resetDemo(page);
  const scenarios = await fetchScenarios(page);
  const heroId = scenarios.hero?.document_id;
  const ambiguityId = scenarios.ambiguity?.document_id;
  const scanId = scenarios.scan?.document_id;

  expect(heroId).toBeTruthy();
  expect(ambiguityId).toBeTruthy();
  expect(scanId).toBeTruthy();

  await page.goto(WEB);
  await page.waitForLoadState('networkidle');

  await expect(page.getByRole('button', { name: /reset demo data/i })).toBeVisible();
  await expect(page.getByText('Seeded demo scenarios')).toBeVisible();
  await expect(page.getByText(/Hero.*Incoming công văn/i)).toBeVisible();
  await expect(page.getByText(/Ambiguity.*multi-department/i)).toBeVisible();
  await expect(page.getByText(/Scan.*low-quality/i)).toBeVisible();

  await switchRole(page, 'Department Reviewer');
  await page.goto(`${WEB}/documents/${heroId}`);
  await page.waitForLoadState('networkidle');

  await expect(page.getByRole('heading', { name: /Hero.*Incoming công văn/i })).toBeVisible();
  await expect(page.getByTestId('document-evidence-panel')).toBeVisible();
  await expect(page.getByTestId('document-evidence-item').first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/Primary Route/i)).toBeVisible();

  await page.getByRole('button', { name: /Approve routing/i }).click();
  await expect(page.getByTestId('document-flash-success')).toContainText(/Routing approved/i);

  await page.getByRole('button', { name: /Request consultation/i }).click();
  await page.getByPlaceholder(/Describe what you need consulted on/i).fill('Please validate cross-department impact.');
  await page.getByRole('button', { name: /^Send$/ }).click();
  await expect(page.getByTestId('document-flash-success')).toContainText(/Consultation requested/i);
  await expect(page.getByTestId('consultation-thread-card')).toContainText(/Please validate cross-department impact/i);

  await switchRole(page, 'Consultant');
  await page.getByRole('button', { name: /Resolve consultation/i }).click();
  await expect(page.getByTestId('document-flash-success')).toContainText(/Consultation resolved/i);

  await switchRole(page, 'Supervisor');
  await page.goto(`${WEB}/dashboard`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { name: /System Dashboard/i })).toBeVisible();

  await page.goto(`${WEB}/response?doc=${heroId}`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { name: /Response & Closeout/i })).toBeVisible();
  await page.getByRole('button', { name: /Approve & Close/i }).click();
  await expect(page.getByRole('button', { name: /Approve & Close/i })).toHaveCount(0, {
    timeout: 20_000,
  });
  await expect(page.getByText('closed', { exact: true })).toBeVisible();
  await expect(page.getByText('CLOSED', { exact: true })).toBeVisible();

  await switchRole(page, 'Intake Clerk');
  await page.goto(`${WEB}/documents/${ambiguityId}`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByText(/Secondary/i)).toBeVisible();
  await expect(page.getByText(/Supervisor Review/i)).toBeVisible();
  await expect(page.getByText('Consultation Needed', { exact: true })).toBeVisible();

  await page.goto(`${WEB}/documents/${scanId}`);
  await page.waitForLoadState('networkidle');
  await expect(page.getByText(/render_ocr|qwen-ocr/i)).toBeVisible();
  await expect(page.getByText(/Extracted text/i)).toBeVisible();
  await expect(page.getByText('Routing Suggestion', { exact: true })).toBeVisible();
});
