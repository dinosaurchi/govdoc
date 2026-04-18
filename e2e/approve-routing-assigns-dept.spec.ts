import { test, expect } from '@playwright/test';

const WEB = 'http://172.17.0.1:3000';
const API = 'http://172.17.0.1:8000';

async function waitForStatus(
  request: import('@playwright/test').APIRequestContext,
  id: string,
  expected: string,
  timeoutMs = 120_000,
) {
  const deadline = Date.now() + timeoutMs;
  let last = '';
  while (Date.now() < deadline) {
    const res = await request.get(`${API}/api/v1/documents/${id}`, {
      headers: { 'X-GovDoc-Role': 'intake_clerk' },
    });
    expect(res.ok()).toBeTruthy();
    const doc = await res.json();
    last = doc.status;
    if (doc.status === expected) return doc;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`stuck on ${last}, expected ${expected}`);
}

/**
 * Regression: `POST /approve-routing` used to flip status→routed without
 * copying the AI's suggested department onto `document.assigned_department_id`,
 * leaving the document owner-less and forcing supervisors into confusing
 * "Close document" recommendations.
 *
 * This test uploads a doc, waits for analysis, then hits approve-routing and
 * asserts both the document and its routing decision are fully populated.
 */
test('approve-routing persists assigned_department_id and finalizes the routing decision', async ({
  request,
}) => {
  test.setTimeout(180_000);

  const upload = await request.post(`${API}/api/v1/documents/`, {
    headers: { 'X-GovDoc-Role': 'intake_clerk' },
    multipart: {
      file: {
        name: 'approve-routing.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from(
          'This document is a tax filing that needs departmental routing.',
        ),
      },
    },
  });
  expect(upload.ok()).toBeTruthy();
  const docId = (await upload.json()).document.id as string;

  await waitForStatus(request, docId, 'analyzed');

  const before = await request.get(`${API}/api/v1/documents/${docId}`, {
    headers: { 'X-GovDoc-Role': 'reviewer' },
  });
  const beforeDoc = await before.json();
  expect(beforeDoc.assigned_department_id).toBeFalsy();
  const suggested =
    beforeDoc.routing_decisions[0]?.suggested_department_id ?? null;
  expect(suggested, 'AI analysis must produce a routing suggestion').toBeTruthy();

  const approve = await request.post(
    `${API}/api/v1/documents/${docId}/approve-routing`,
    { headers: { 'X-GovDoc-Role': 'reviewer' } },
  );
  expect(approve.ok(), `approve-routing: ${approve.status()}`).toBeTruthy();

  // Fetch with an actor that does NOT trigger the implicit routed→under_review
  // promotion (that only fires for reviewers on routed docs).
  const after = await request.get(`${API}/api/v1/documents/${docId}`, {
    headers: { 'X-GovDoc-Role': 'intake_clerk' },
  });
  const afterDoc = await after.json();
  expect(afterDoc.status).toBe('routed');
  expect(afterDoc.assigned_department_id).toBe(suggested);
  const rd = afterDoc.routing_decisions[0];
  expect(rd.final_department_id).toBe(suggested);
  expect(rd.decided_by_role).toBe('reviewer');
});

/**
 * Regression: when a document lands on `under_review` with no assigned
 * department (drifted data from the pre-fix bug above), the supervisor's
 * document page must (a) show the amber "no assigned department" banner
 * and (b) recommend "Reroute document" instead of "Close document".
 */
test('supervisor on under_review + no department sees reroute recommendation + banner', async ({
  page,
  request,
}) => {
  test.setTimeout(60_000);

  const list = await request.get(
    `${API}/api/v1/documents/?offset=0&limit=200`,
    { headers: { 'X-GovDoc-Role': 'intake_clerk' } },
  );
  expect(list.ok()).toBeTruthy();
  const docs: Array<{ id: string; status: string; assigned_department_id: string | null }> =
    await list.json();
  const drifted = docs.find(
    (d) => d.status === 'under_review' && !d.assigned_department_id,
  );
  test.skip(
    !drifted,
    'No drifted doc present in this environment; fix is covered by the unit test in workflow-actions.test.ts',
  );

  await page.goto(WEB);
  await page.evaluate(() => localStorage.setItem('govdoc_role', 'Supervisor'));
  await page.goto(`${WEB}/documents/${drifted!.id}`);
  await page.waitForLoadState('networkidle');

  await expect(page.getByTestId('no-assigned-department-warning')).toBeVisible();
  const forward = page.getByTestId('workflow-forward-action');
  await expect(forward).toBeVisible();
  await expect(forward).toContainText(/reroute document/i);
  await expect(forward).not.toContainText(/close document/i);
});
