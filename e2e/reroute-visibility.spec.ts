import { test, expect } from '@playwright/test';

const WEB = process.env.WEB_URL ?? 'http://172.17.0.1:3000';
const API = process.env.API_URL ?? 'http://172.17.0.1:8000';

test('reroute surfaces assigned dept, success flash, latest routing callout, and next-owner CTA', async ({
  page,
  request,
}) => {
  test.setTimeout(60_000);

  const listRes = await request.get(`${API}/api/v1/documents/?offset=0&limit=50`, {
    headers: { 'X-GovDoc-Role': 'reviewer' },
  });
  expect(listRes.ok()).toBeTruthy();
  const docs = await listRes.json();
  const candidate = docs.find((d: { status: string }) =>
    ['analyzed', 'routed', 'under_review'].includes(d.status),
  );
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
  expect((await assigned.textContent())?.trim()).not.toBe(before);

  const callout = page.getByTestId('latest-routing-decision');
  await expect(callout).toBeVisible();
  await expect(callout).toContainText(/Rerouted/i);
  await expect(callout).toContainText(targetName);
  await expect(callout).toContainText(/reviewer/i);

  // GET as reviewer promotes `routed` → `under_review` so the doc is in a state
  // where a Supervisor can act.
  await page.reload();
  await page.waitForLoadState('networkidle');

  // "Next owner" CTA only renders when the current role has no *forward* action.
  // Reviewers now have "Approve document" as their forward on `under_review`, so
  // view as Consultant — read-only for this queue — to surface the handoff CTA.
  await page.evaluate(() => localStorage.setItem('govdoc_role', 'Consultant'));
  await page.reload();
  await page.waitForLoadState('networkidle');

  const otherRoles = page.getByTestId('other-roles-actions');
  await expect(otherRoles).toBeVisible();
  await expect(otherRoles).toContainText('Supervisor');
  await expect(otherRoles).toContainText(/approve document/i);

  await page.getByTestId('switch-to-supervisor').click();

  const actingAs = page.getByTestId('workflow-context');
  await expect(actingAs).toContainText(/Supervisor/, { timeout: 5_000 });

  // Supervisor view promotes "Approve document" as the Recommended next step.
  const forward = page.getByTestId('workflow-forward-action');
  await expect(forward).toBeVisible();
  await expect(forward).toContainText(/Recommended next step/i);
  await expect(forward).toContainText(/Approve document/i);

  // Other-role handoff CTA is hidden once the active role has a forward action.
  await expect(page.getByTestId('other-roles-actions')).toHaveCount(0);

  // Escalate to supervisor is hidden for a supervisor (self-escalation is a no-op).
  await expect(page.getByRole('button', { name: /escalate to supervisor/i })).toHaveCount(0);

  // Role-aware hint copy no longer says "A Reviewer must …"
  await expect(actingAs).not.toContainText(/A Reviewer must/i);
});
