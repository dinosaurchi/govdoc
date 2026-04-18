import { test, expect } from '@playwright/test';

const API = process.env.API_URL ?? 'http://172.17.0.1:8000';

/**
 * Covers FEEDBACK-13 backend fix via the live API:
 *   1. Resolving ONE of several open consultation notes must keep the
 *      document on `in_consultation`.
 *   2. Resolving the LAST open note flips it to `under_review`.
 *
 * The frontend "orphaned-consultation-warning" banner (rendered when a
 * document drifted to a non-`in_consultation` state while still having
 * open notes) is covered by a component-level unit test, since
 * reproducing that drifted state via the API requires direct DB writes.
 */

async function getDoc(request: import('@playwright/test').APIRequestContext, id: string) {
  const res = await request.get(`${API}/api/v1/documents/${id}`, {
    // Use intake_clerk: it can read documents but does NOT trigger the
    // implicit routed→under_review transition that reviewer/supervisor do.
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

test('resolving one of two open consultation notes keeps the doc on in_consultation', async ({
  request,
}) => {
  test.setTimeout(240_000);

  const upload = await request.post(`${API}/api/v1/documents/`, {
    headers: { 'X-GovDoc-Role': 'intake_clerk' },
    multipart: {
      file: {
        name: 'parallel-consultation.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from(
          'Document for parallel-consultation E2E test. ' +
            'Testing that resolving one open note keeps the doc on in_consultation.',
        ),
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
  expect(approve.ok(), `approve-routing: ${approve.status()} ${await approve.text()}`).toBeTruthy();

  // Reviewer GET implicitly transitions routed → under_review.
  const touch = await request.get(`${API}/api/v1/documents/${docId}`, {
    headers: { 'X-GovDoc-Role': 'reviewer' },
  });
  expect(touch.ok()).toBeTruthy();
  expect((await touch.json()).status).toBe('under_review');

  const noteA = await request.post(
    `${API}/api/v1/documents/${docId}/request-consultation`,
    {
      headers: { 'X-GovDoc-Role': 'reviewer' },
      data: { target_role: 'consultant', body: 'Note A (parallel test)' },
    },
  );
  expect(noteA.ok(), `note A: ${noteA.status()} ${await noteA.text()}`).toBeTruthy();
  const noteAId = (await noteA.json()).consultation_note.id as string;

  expect((await getDoc(request, docId)).status).toBe('in_consultation');

  const noteB = await request.post(
    `${API}/api/v1/documents/${docId}/request-consultation`,
    {
      headers: { 'X-GovDoc-Role': 'reviewer' },
      data: { target_role: 'consultant', body: 'Note B (parallel test)' },
    },
  );
  expect(noteB.ok(), `note B: ${noteB.status()} ${await noteB.text()}`).toBeTruthy();
  const noteBId = (await noteB.json()).consultation_note.id as string;

  const resolveA = await request.post(
    `${API}/api/v1/documents/${docId}/resolve-consultation/${noteAId}`,
    { headers: { 'X-GovDoc-Role': 'consultant' } },
  );
  expect(resolveA.ok(), `resolve A: ${resolveA.status()} ${await resolveA.text()}`).toBeTruthy();

  // Doc must remain `in_consultation` while note B is still open.
  const afterA = await getDoc(request, docId);
  expect(afterA.status).toBe('in_consultation');
  const openAfterA = afterA.consultation_notes.filter(
    (n: { resolved_at: string | null }) => !n.resolved_at,
  );
  expect(openAfterA).toHaveLength(1);

  // Resolve note B → doc flips to under_review.
  const resolveB = await request.post(
    `${API}/api/v1/documents/${docId}/resolve-consultation/${noteBId}`,
    { headers: { 'X-GovDoc-Role': 'consultant' } },
  );
  expect(resolveB.ok(), `resolve B: ${resolveB.status()} ${await resolveB.text()}`).toBeTruthy();

  const afterB = await getDoc(request, docId);
  expect(afterB.status).toBe('under_review');
  const openAfterB = afterB.consultation_notes.filter(
    (n: { resolved_at: string | null }) => !n.resolved_at,
  );
  expect(openAfterB).toHaveLength(0);
});
