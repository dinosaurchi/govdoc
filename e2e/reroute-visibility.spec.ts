import { test, expect } from '@playwright/test';

const WEB = process.env.WEB_URL ?? 'http://172.17.0.1:3000';
const API = process.env.API_URL ?? 'http://172.17.0.1:8000';

test('reroute surfaces assigned department and success flash', async ({ page, request }) => {
  test.setTimeout(60_000);

  const listRes = await request.get(`${API}/api/v1/documents/?offset=0&limit=50`, {
    headers: { 'X-GovDoc-Role': 'reviewer' },
  });
  expect(listRes.ok()).toBeTruthy();
  const docs = await listRes.json();
  const candidate = docs.find((d: { status: string }) => ['analyzed', 'routed', 'under_review'].includes(d.status));
  expect(candidate, 'need at least one reroutable doc').toBeTruthy();
  const docId = candidate.id;

  const deptsRes = await request.get(`${API}/api/v1/meta/departments`, {
    headers: { 'X-GovDoc-Role': 'reviewer' },
  });
  const depts: Array<{ id: string; name: string }> = await deptsRes.json();
  const currentDeptId = candidate.assigned_department_id as string | null;
  const target = depts.find((d) => d.id !== currentDeptId);
  expect(target).toBeTruthy();
  const targetName = target!.name;

  await page.goto(WEB);
  await page.evaluate(() => {
    localStorage.setItem('govdoc_role', 'Department Reviewer');
  });
  await page.goto(`${WEB}/documents/${docId}`);

  const assigned = page.getByTestId('document-assigned-department');
  await expect(assigned).toBeVisible({ timeout: 10_000 });
  const before = (await assigned.textContent())?.trim() ?? '';

  await page.getByRole('button', { name: /reroute/i }).first().click();
  await page.getByLabel(/reassign department/i).selectOption(target!.id);
  await page.getByLabel(/rationale/i).fill('Playwright QA');
  await page.getByRole('button', { name: /confirm reroute/i }).click();

  await expect(page.getByTestId('document-flash-success')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId('document-flash-success')).toContainText(targetName);

  await expect(assigned).toContainText(targetName, { timeout: 10_000 });
  const after = (await assigned.textContent())?.trim() ?? '';
  expect(after).not.toBe(before);
});
