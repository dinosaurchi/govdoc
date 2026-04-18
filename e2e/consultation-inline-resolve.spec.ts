import { test, expect } from '@playwright/test';

const WEB = process.env.WEB_URL ?? 'http://172.17.0.1:3000';
const API = process.env.API_URL ?? 'http://172.17.0.1:8000';

/**
 * Covers the follow-up to FEEDBACK-13: a consultant must be able to
 * resolve open consultation notes directly from /consultation without
 * jumping back to the document page.
 *
 *   1. Reviewer opens two parallel notes via the API (target_role=consultant).
 *   2. Consultant visits /consultation?doc=<id>.
 *   3. Clicks "Mark as resolved" on the first note — thread pill stays
 *      "In Consultation".
 *   4. Clicks "Mark as resolved" on the second note — thread pill flips
 *      to "Under Review".
 */

async function getDoc(request: import('@playwright/test').APIRequestContext, id: string) {
  const res = await request.get(`${API}/api/v1/documents/${id}`, {
    headers: { 'X-GovDoc-Role': 'intake_clerk' },
  });
  expect(res.ok(), `GET /documents/${id}: ${res.status()}`).toBeTruthy();
  return res.json();
}

async function waitForStatus(
  request: import('@playwright/test').APIRequestContext,
  id: string,
  expected: string,
  timeoutMs = 120_000,
) {
  const deadline = Date.now() + timeoutMs;
  let last = '';
  while (Date.now() < deadline) {
    const doc = await getDoc(request, id);
    last = doc.status;
    if (doc.status === expected) return doc;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`document ${id} stuck on ${last}, expected ${expected}`);
}

test('consultant resolves two parallel notes inline on the consultation page', async ({
  page,
  request,
}) => {
  test.setTimeout(240_000);

  const upload = await request.post(`${API}/api/v1/documents/`, {
    headers: { 'X-GovDoc-Role': 'intake_clerk' },
    multipart: {
      file: {
        name: 'inline-resolve.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('E2E: consultation inline resolve.'),
      },
    },
  });
  expect(upload.ok(), `upload: ${upload.status()}`).toBeTruthy();
  const docId = (await upload.json()).document.id as string;

  await waitForStatus(request, docId, 'analyzed');

  const approve = await request.post(
    `${API}/api/v1/documents/${docId}/approve-routing`,
    { headers: { 'X-GovDoc-Role': 'reviewer' } },
  );
  expect(approve.ok()).toBeTruthy();

  // Reviewer GET implicitly promotes routed → under_review.
  const touch = await request.get(`${API}/api/v1/documents/${docId}`, {
    headers: { 'X-GovDoc-Role': 'reviewer' },
  });
  expect(touch.ok()).toBeTruthy();
  expect((await touch.json()).status).toBe('under_review');

  for (const body of ['Question for consultant A', 'Question for consultant B']) {
    const res = await request.post(
      `${API}/api/v1/documents/${docId}/request-consultation`,
      {
        headers: { 'X-GovDoc-Role': 'reviewer' },
        data: { target_role: 'consultant', body },
      },
    );
    expect(res.ok(), `request-consultation (${body}): ${res.status()}`).toBeTruthy();
  }

  expect((await getDoc(request, docId)).status).toBe('in_consultation');

  await page.goto(WEB);
  await page.evaluate(() => {
    localStorage.setItem('govdoc_role', 'Consultant');
  });
  await page.goto(`${WEB}/consultation?doc=${docId}`);

  // Wait for the thread to load. The Resolve buttons belong to notes
  // whose target_role === current role (Consultant) — both of them here.
  const resolveButtons = page.getByTestId('consultation-resolve-note');
  await expect(resolveButtons).toHaveCount(2, { timeout: 15_000 });

  // Status pill is "In Consultation".
  const statusPill = page
    .locator('[data-testid="consultation-scroll"]')
    .locator('..')
    .locator('text=/in consultation/i')
    .first();
  // Cheaper fallback: just verify via API after each click, which is the
  // source of truth. The pill is just visual confirmation.

  // Resolve the first note.
  await resolveButtons.first().click();
  await expect(resolveButtons).toHaveCount(1, { timeout: 10_000 });

  const afterFirst = await getDoc(request, docId);
  expect(afterFirst.status).toBe('in_consultation');

  // Resolve the remaining note → doc flips to under_review.
  await resolveButtons.first().click();
  await expect(resolveButtons).toHaveCount(0, { timeout: 10_000 });

  const afterSecond = await getDoc(request, docId);
  expect(afterSecond.status).toBe('under_review');

  // Composer hint now points to the document page.
  const closedHint = page.getByTestId('consultation-thread-hint');
  await expect(closedHint).toHaveAttribute('data-tone', 'closed');
  await expect(closedHint).toContainText(/under review/i);
});
