import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API = 'http://172.17.0.1:8000/api/v1';
const FIXTURE = '/workspace/projects/hackathon/2026-qwen-ai-build-day/govdoc/api/tests/fixtures/sample_cong_van.txt';

/** Reset demo data via API */
async function resetDemo(page: Page) {
  await page.request.post(`${API}/demo/reset`, {
    headers: { 'X-GovDoc-Role': 'supervisor' },
  });
}

/** Switch role via the header <select> */
async function switchRole(page: Page, role: string) {
  await page.locator('header select').selectOption(role);
  await page.waitForTimeout(500);
}

/** Wait until network is idle */
async function idle(page: Page) {
  await page.waitForLoadState('networkidle');
}

/** Navigate to the review queue and click the first document row.
 *  Returns the document ID extracted from the URL. */
async function openFirstDocument(page: Page): Promise<string> {
  await page.locator('nav').getByText('Review', { exact: true }).click();
  await expect(page).toHaveURL(/\/review$/);
  await page.waitForTimeout(2000);
  const row = page.locator('table tbody tr').first();
  await row.waitFor({ state: 'visible' });
  await row.click();
  await expect(page).toHaveURL(/\/documents\/[^/]+$/);
  await idle(page);
  await page.waitForTimeout(1000);
  const id = page.url().split('/').pop()!;
  return id;
}

/** Upload the fixture file and wait for success toast */
async function uploadFixture(page: Page) {
  await page.locator('input[type="file"]').setInputFiles(FIXTURE);
  // Upload runs classification + routing + summary + escalation AI calls synchronously,
  // so upstream model latency can make 20s too tight.
  await expect(
    page.getByText('File uploaded, text extracted, and AI analysis completed'),
  ).toBeVisible({ timeout: 60000 });
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

test.describe('GovDoc E2E — Full document workflow', () => {
  const consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));
    await resetDemo(page);
    consoleErrors.length = 0;
  });

  test.afterEach(async () => {
    if (consoleErrors.length > 0) {
      console.log('[Console Errors]', consoleErrors);
    }
  });

  // =========================================================================
  // Step 1 — Landing page renders
  // =========================================================================
  test('Step 1: Landing page (/) renders correctly', async ({ page }) => {
    await page.goto('/');
    await idle(page);

    await expect(page.getByRole('heading', { name: /GovDoc.*SecureFlow/i })).toBeVisible();
    await expect(page.locator('text=Document Intake').first()).toBeVisible();
    await expect(page.locator('text=Workflow Review').first()).toBeVisible();
    await expect(page.locator('header select')).toBeVisible();
    await expect(page.locator('header select')).toHaveValue('Intake Clerk');

    // BUG-001 check: No TypeError in console
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 2 — Role switcher works
  // =========================================================================
  test('Step 2: Role switcher works', async ({ page }) => {
    await page.goto('/');
    await idle(page);

    const select = page.locator('header select');
    await expect(select).toHaveValue('Intake Clerk');

    // Switch through all roles
    for (const role of ['Department Reviewer', 'Consultant', 'Supervisor', 'Intake Clerk']) {
      await select.selectOption(role);
      await expect(select).toHaveValue(role);
    }

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 3 — Intake upload works
  // =========================================================================
  test('Step 3: Intake upload works', async ({ page }) => {
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Intake Clerk');
    await page.locator('nav').getByText('Intake', { exact: true }).click();
    await expect(page).toHaveURL(/\/intake$/);
    await idle(page);

    await expect(page.getByRole('heading', { name: /Document Intake/i })).toBeVisible();
    await uploadFixture(page);

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 3a — Intake shows processing steps + link to review case (FEEDBACK-02)
  // =========================================================================
  test('Step 3a: Intake shows processing steps + CTA link (FEEDBACK-02)', async ({ page }) => {
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Intake Clerk');
    await page.locator('nav').getByText('Intake', { exact: true }).click();
    await expect(page).toHaveURL(/\/intake$/);
    await idle(page);

    await page.locator('input[type="file"]').setInputFiles(FIXTURE);

    // The stepper should appear during upload
    await expect(page.locator('[data-testid="intake-stepper"]')).toBeVisible({ timeout: 5000 });
    // All step rows should be present
    for (const id of ['upload', 'validate', 'extract', 'analyze']) {
      await expect(page.locator(`[data-testid="intake-step-${id}"]`)).toBeVisible();
    }

    // Wait for success state
    await expect(page.locator('[data-testid="intake-success"]')).toBeVisible({ timeout: 30000 });

    // After success every step must be done
    for (const id of ['upload', 'validate', 'extract', 'analyze']) {
      await expect(page.locator(`[data-testid="intake-step-${id}"]`)).toHaveAttribute('data-status', 'done');
    }

    // CTA link to open the review case for this specific document
    const cta = page.locator('[data-testid="intake-open-case"]');
    await expect(cta).toBeVisible();
    const href = await cta.getAttribute('href');
    expect(href).toMatch(/^\/documents\/[0-9a-f-]+$/);

    await cta.click();
    await expect(page).toHaveURL(/\/documents\/[^/]+$/);

    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 3b — Review queue rows are clickable (FEEDBACK-01)
  // =========================================================================
  test('Step 3b: Review queue rows are clickable (FEEDBACK-01)', async ({ page }) => {
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Department Reviewer');
    await page.locator('nav').getByText('Review', { exact: true }).click();
    await expect(page).toHaveURL(/\/review$/);
    await page.waitForTimeout(2000);

    const row = page.locator('table tbody tr[data-testid="review-row"]').first();
    await expect(row).toBeVisible({ timeout: 10000 });

    // Clicking anywhere on the row (not on a link) should navigate to the detail page
    const titleCell = row.locator('td').first();
    await titleCell.click();
    await expect(page).toHaveURL(/\/documents\/[^/]+$/);

    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 3c — File metadata size is human readable (FEEDBACK-04)
  // =========================================================================
  test('Step 3c: File metadata shows human-readable size (FEEDBACK-04)', async ({ page }) => {
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Department Reviewer');
    await page.locator('nav').getByText('Review', { exact: true }).click();
    await expect(page).toHaveURL(/\/review$/);
    await page.waitForTimeout(2000);

    const row = page.locator('table tbody tr').first();
    await row.waitFor({ state: 'visible' });
    await row.click();
    await expect(page).toHaveURL(/\/documents\/[^/]+$/);
    await idle(page);

    const size = page.locator('[data-testid="file-size"]');
    await expect(size).toBeVisible({ timeout: 5000 });
    const text = (await size.textContent()) ?? '';
    // Must contain one of the human-readable units (not just raw "bytes")
    expect(text).toMatch(/\b(?:B|KB|MB|GB|TB)\b/);
    // And must also keep the exact byte count for clarity
    expect(text).toMatch(/\d[\d,]*\s*bytes/);

    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 4 — Review queue shows documents
  // =========================================================================
  test('Step 4: Review queue shows documents', async ({ page }) => {
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Department Reviewer');
    await page.locator('nav').getByText('Review', { exact: true }).click();
    await expect(page).toHaveURL(/\/review$/);
    await idle(page);

    await expect(page.getByRole('heading', { name: /Review Queue/i })).toBeVisible();
    await page.waitForTimeout(2000);
    const rows = page.locator('table tbody tr');
    await expect(rows).not.toHaveCount(0, { timeout: 10000 });

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 5 — Approve routing works
  // =========================================================================
  test('Step 5: Approve routing works', async ({ page }) => {
    // Upload a new doc first (creates analyzed doc)
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Intake Clerk');
    await page.locator('nav').getByText('Intake', { exact: true }).click();
    await expect(page).toHaveURL(/\/intake$/);
    await idle(page);
    await uploadFixture(page);

    // Find the most recently created analyzed document via API
    const docsResp = await page.request.get(`${API}/documents/`, {
      headers: { 'X-GovDoc-Role': 'reviewer' },
    });
    const docs = await docsResp.json();
    const analyzedDocs = docs
      .filter((d: any) => d.status === 'analyzed')
      .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    expect(analyzedDocs.length).toBeGreaterThan(0);
    const docId = analyzedDocs[0].id;

    // Navigate directly to the analyzed document as reviewer
    await switchRole(page, 'Department Reviewer');
    await page.goto(`/documents/${docId}`);
    await idle(page);
    await page.waitForTimeout(1000);

    // The doc should be analyzed. Approve routing transitions analyzed→routed.
    const approveBtn = page.getByRole('button', { name: /Approve routing/i });
    await expect(approveBtn).toBeVisible({ timeout: 5000 });

    // Verify the button is NOT disabled (doc must be in analyzed state)
    const isDisabled = await approveBtn.isDisabled();
    expect(isDisabled).toBe(false);

    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/approve-routing') && r.request().method() === 'POST'),
      approveBtn.click(),
    ]);
    expect([200, 204]).toContain(resp.status());

    await page.waitForTimeout(2000);

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 6 — Request consultation with custom body (BUG-006 fix)
  // =========================================================================
  test('Step 6: Request consultation with custom body "Xin y kien" (BUG-006)', async ({ page }) => {
    // Upload a new doc, approve routing to get it to routed/under_review state,
    // then request consultation.
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Intake Clerk');
    await page.locator('nav').getByText('Intake', { exact: true }).click();
    await expect(page).toHaveURL(/\/intake$/);
    await idle(page);
    await uploadFixture(page);

    // Find the most recently created analyzed document via API
    const docsResp = await page.request.get(`${API}/documents/`, {
      headers: { 'X-GovDoc-Role': 'reviewer' },
    });
    const docs = await docsResp.json();
    const analyzedDocs = docs
      .filter((d: any) => d.status === 'analyzed')
      .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    expect(analyzedDocs.length).toBeGreaterThan(0);
    const docId = analyzedDocs[0].id;

    // Switch to reviewer and navigate directly to the analyzed document
    await switchRole(page, 'Department Reviewer');
    await page.goto(`/documents/${docId}`);
    await idle(page);
    await page.waitForTimeout(1000);

    // Approve routing first (analyzed → routed)
    const approveBtn = page.getByRole('button', { name: /Approve routing/i });
    if (await approveBtn.isVisible() && !(await approveBtn.isDisabled())) {
      await approveBtn.click();
      await page.waitForTimeout(2000);
    }

    // Now request consultation — button should be visible for routed/under_review docs
    // Click "Request consultation" to reveal the textarea
    const consultBtn = page.getByRole('button', { name: /Request consultation/i });
    await expect(consultBtn).toBeVisible({ timeout: 5000 });
    await consultBtn.click();

    // Fill in custom body (BUG-006: textarea should be visible and editable)
    const textarea = page.locator('textarea[placeholder*="consulted"]');
    await expect(textarea).toBeVisible({ timeout: 5000 });
    await textarea.fill('Xin y kien');

    // Click Send
    const sendBtn = page.getByRole('button', { name: 'Send' });
    await expect(sendBtn).toBeEnabled({ timeout: 3000 });

    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/request-consultation') && r.request().method() === 'POST'),
      sendBtn.click(),
    ]);
    expect([200, 204]).toContain(resp.status());

    // Wait for the doc to reload and show the consultation note
    await page.waitForTimeout(3000);

    // Verify the custom body "Xin y kien" appears in the consultation thread
    await expect(page.getByText('Xin y kien')).toBeVisible({ timeout: 5000 });

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 7 — Resolve consultation works (BUG-005 fix)
  // =========================================================================
  test('Step 7: Resolve consultation works (BUG-005)', async ({ page }) => {
    // Create a doc, approve routing, request consultation, then resolve
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Intake Clerk');
    await page.locator('nav').getByText('Intake', { exact: true }).click();
    await expect(page).toHaveURL(/\/intake$/);
    await idle(page);
    await uploadFixture(page);

    // Find the most recently created analyzed document via API
    const docsResp = await page.request.get(`${API}/documents/`, {
      headers: { 'X-GovDoc-Role': 'reviewer' },
    });
    const docs = await docsResp.json();
    const analyzedDocs = docs
      .filter((d: any) => d.status === 'analyzed')
      .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    expect(analyzedDocs.length).toBeGreaterThan(0);
    const docId = analyzedDocs[0].id;

    // Switch to reviewer and navigate directly to the analyzed document
    await switchRole(page, 'Department Reviewer');
    await page.goto(`/documents/${docId}`);
    await idle(page);
    await page.waitForTimeout(1000);

    // Approve routing first
    const approveBtn = page.getByRole('button', { name: /Approve routing/i });
    if (await approveBtn.isVisible() && !(await approveBtn.isDisabled())) {
      await approveBtn.click();
      await page.waitForTimeout(2000);
    }

    // Request consultation
    const consultBtn = page.getByRole('button', { name: /Request consultation/i });
    await expect(consultBtn).toBeVisible({ timeout: 5000 });
    await consultBtn.click();
    const textarea = page.locator('textarea[placeholder*="consulted"]');
    await expect(textarea).toBeVisible({ timeout: 5000 });
    await textarea.fill('Please review this document');
    const sendBtn = page.getByRole('button', { name: 'Send' });
    await expect(sendBtn).toBeEnabled({ timeout: 3000 });
    await sendBtn.click();
    await page.waitForTimeout(3000);

    // Now the doc should be in_consultation. Verify "Resolve consultation" button is visible.
    const resolveBtn = page.getByRole('button', { name: /Resolve consultation/i });
    await expect(resolveBtn).toBeVisible({ timeout: 5000 });

    // Click resolve
    const [resolveResp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/resolve-consultation') && r.request().method() === 'POST'),
      resolveBtn.click(),
    ]);
    expect([200, 204]).toContain(resolveResp.status());

    await page.waitForTimeout(2000);

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 8 — Close document works
  // =========================================================================
  test('Step 8: Close document works', async ({ page }) => {
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Supervisor');

    // Navigate to review queue and open first doc
    const docId = await openFirstDocument(page);
    await page.waitForTimeout(1000);

    // Close document button is active for Supervisor
    const closeBtn = page.getByRole('button', { name: /Close document/i });
    await expect(closeBtn).toBeVisible({ timeout: 5000 });

    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/close') && r.request().method() === 'POST'),
      closeBtn.click(),
    ]);
    expect([200, 204]).toContain(resp.status());

    await page.waitForTimeout(2000);
    await expect(page.getByRole('heading').first()).toBeVisible();

    // BUG-001 check
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 9 — No TypeError on consultation page (BUG-001 fix)
  // =========================================================================
  test('Step 9: No TypeError on consultation page (BUG-001)', async ({ page }) => {
    await page.goto('/consultation');
    await idle(page);

    // Page should load without JS errors
    const bodyText = await page.textContent('body');
    expect(bodyText?.length).toBeGreaterThan(0);

    // Specifically check for TypeError — BUG-001 was a crash on consultation page
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);

    // The page should show "Internal Consultation" heading
    await expect(page.getByRole('heading', { name: /Internal Consultation/i })).toBeVisible({ timeout: 5000 });
  });

  // =========================================================================
  // Step 9b — Consultation chat: own messages align right, others left,
  // sorted chronologically, consultant can reply (FEEDBACK-05)
  // =========================================================================
  test('Step 9b: Consultation chat bubbles align by role and sort chronologically (FEEDBACK-05)', async ({ page }) => {
    // Start as reviewer and open the seed doc that is already in_consultation
    await page.goto('/consultation');
    await idle(page);
    await switchRole(page, 'Department Reviewer');
    await page.waitForTimeout(1500);

    // Pick the first card whose status is `in consultation` (closed threads are
    // terminal and would reject new messages).
    const inConsultation = page
      .locator('div[role="button"]')
      .filter({ hasText: /in consultation/i })
      .first();
    await expect(inConsultation).toBeVisible({ timeout: 10000 });
    await inConsultation.click();
    await page.waitForTimeout(500);

    const composer = page.locator('[data-testid="consultation-composer"]');
    await expect(composer).toBeVisible();

    // Reviewer sends a message — should appear on the right (own)
    const input = page.locator('[data-testid="consultation-input"]');
    await input.fill('Reviewer ping');
    const [reviewerResp] = await Promise.all([
      page.waitForResponse(r => /\/consultation\/.+\/notes|\/request-consultation/.test(r.url()) && r.request().method() === 'POST'),
      page.locator('[data-testid="consultation-send"]').click(),
    ]);
    expect([200, 204]).toContain(reviewerResp.status());
    await page.waitForTimeout(1500);

    const reviewerBubble = page.locator('[data-testid="consultation-message"]').filter({ hasText: 'Reviewer ping' });
    await expect(reviewerBubble).toHaveAttribute('data-own', 'true');
    await expect(reviewerBubble).toHaveAttribute('data-author-role', 'reviewer');

    // Switch to Consultant and post a reply — should appear on the right (own)
    // while the reviewer's earlier message is now rendered on the left (other).
    await switchRole(page, 'Consultant');
    await page.waitForTimeout(1500);
    // The same thread should remain selected since we preserve selection.
    const consultantComposer = page.locator('[data-testid="consultation-composer"]');
    await expect(consultantComposer).toBeVisible({ timeout: 5000 });
    await page.locator('[data-testid="consultation-input"]').fill('Consultant reply');
    const [consultantResp] = await Promise.all([
      page.waitForResponse(r => /\/consultation\/.+\/notes/.test(r.url()) && r.request().method() === 'POST'),
      page.locator('[data-testid="consultation-send"]').click(),
    ]);
    expect([200, 204]).toContain(consultantResp.status());
    await page.waitForTimeout(1500);

    // Reviewer's message is now an "other" bubble (left)
    const reviewerBubbleAsOther = page.locator('[data-testid="consultation-message"]').filter({ hasText: 'Reviewer ping' });
    await expect(reviewerBubbleAsOther).toHaveAttribute('data-own', 'false');
    await expect(reviewerBubbleAsOther).toHaveAttribute('data-author-role', 'reviewer');

    // Consultant's new message is on the right (own)
    const consultantBubble = page.locator('[data-testid="consultation-message"]').filter({ hasText: 'Consultant reply' });
    await expect(consultantBubble).toHaveAttribute('data-own', 'true');
    await expect(consultantBubble).toHaveAttribute('data-author-role', 'consultant');

    // Chronological order: Reviewer ping comes before Consultant reply
    const bubbleTexts = await page.locator('[data-testid="consultation-message"]').allTextContents();
    const idxReviewer = bubbleTexts.findIndex(t => t.includes('Reviewer ping'));
    const idxConsultant = bubbleTexts.findIndex(t => t.includes('Consultant reply'));
    expect(idxReviewer).toBeGreaterThanOrEqual(0);
    expect(idxConsultant).toBeGreaterThan(idxReviewer);

    // Intake Clerk can view but cannot reply
    await switchRole(page, 'Intake Clerk');
    await page.waitForTimeout(1000);
    await expect(page.locator('[data-testid="consultation-composer"]')).toHaveCount(0);

    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 9d — Consultation + Response sidebars are polished (FEEDBACK-07)
  // =========================================================================
  test('Step 9d: Consultation sidebar, composer, and Response sidebar are polished (FEEDBACK-07)', async ({ page }) => {
    // ---- Consultation page ---------------------------------------------
    await page.goto('/consultation');
    await idle(page);
    await switchRole(page, 'Department Reviewer');
    await page.waitForTimeout(1000);

    // Sidebar structure
    const sidebar = page.locator('[data-testid="consultation-sidebar"]');
    await expect(sidebar).toBeVisible();
    await expect(page.locator('[data-testid="consultation-search"]')).toBeVisible();
    await expect(page.locator('[data-testid="consultation-list"]')).toBeVisible();

    // Each card shows a status pill + title + meta (note count)
    const cards = page.locator('[data-testid="consultation-thread-card"]');
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);

    // Search narrows the list
    await page.locator('[data-testid="consultation-search"]').fill('zzz_no_match_zzz');
    await page.waitForTimeout(200);
    await expect(page.locator('[data-testid="consultation-thread-card"]')).toHaveCount(0);
    await page.locator('[data-testid="consultation-search"]').fill('');
    await page.waitForTimeout(200);

    // Pick an in_consultation thread and verify the composer is a textarea that
    // accepts newlines (Shift+Enter) without submitting.
    const activeCard = page
      .locator('[data-testid="consultation-thread-card"]')
      .filter({ hasText: /in consultation/i })
      .first();
    await expect(activeCard).toBeVisible({ timeout: 10000 });
    await activeCard.click();
    await page.waitForTimeout(500);

    const composer = page.locator('[data-testid="consultation-composer"]');
    await expect(composer).toBeVisible();
    const input = page.locator('[data-testid="consultation-input"]');
    await expect(input).toHaveAttribute('placeholder', /Enter to send.*Shift\+Enter/i);

    // A long message should wrap inside the bubble (break-words) — post one and
    // verify the rendered bubble width is <= 80% of the thread width.
    const longText = 'The quick brown fox ' + 'jumps over the lazy dog. '.repeat(20);
    await input.fill(longText);
    const [postResp] = await Promise.all([
      page.waitForResponse(r => /\/consultation\/.+\/notes|\/request-consultation/.test(r.url()) && r.request().method() === 'POST'),
      page.locator('[data-testid="consultation-send"]').click(),
    ]);
    expect([200, 204]).toContain(postResp.status());
    await page.waitForTimeout(1500);

    const ownBubble = page
      .locator('[data-testid="consultation-message"][data-own="true"]')
      .filter({ hasText: 'jumps over the lazy dog' })
      .first();
    await expect(ownBubble).toBeVisible();

    // The rendered bubble (the inner flex column that holds the pill + text)
    // should respect the 75% cap. The outer `[data-testid="consultation-message"]`
    // is the justify-end row, so we measure its first child column.
    const scroller = page.locator('[data-testid="consultation-scroll"]');
    const scrollerBox = await scroller.boundingBox();
    const bubbleColumnBox = await ownBubble.locator('> div').first().boundingBox();
    expect(scrollerBox && bubbleColumnBox).toBeTruthy();
    if (scrollerBox && bubbleColumnBox) {
      expect(bubbleColumnBox.width).toBeLessThanOrEqual(scrollerBox.width * 0.8);
      // Auto-scroll: the newest bubble must be within the visible viewport of
      // the scroll area.
      expect(bubbleColumnBox.y + bubbleColumnBox.height).toBeLessThanOrEqual(
        scrollerBox.y + scrollerBox.height + 4,
      );
    }

    // ---- Response page -------------------------------------------------
    await page.goto('/response');
    await idle(page);
    await switchRole(page, 'Supervisor');
    await page.waitForTimeout(1000);

    await expect(page.locator('[data-testid="response-sidebar"]')).toBeVisible();
    await expect(page.locator('[data-testid="response-search"]')).toBeVisible();
    const respCards = page.locator('[data-testid="response-card"]');
    expect(await respCards.count()).toBeGreaterThan(0);
    // Search filters the list
    await page.locator('[data-testid="response-search"]').fill('zzz_no_match_zzz');
    await page.waitForTimeout(200);
    await expect(page.locator('[data-testid="response-card"]')).toHaveCount(0);

    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 9c — Workflow actions panel is role-aware and informative (FEEDBACK-06)
  // =========================================================================
  test('Step 9c: Workflow panel explains role, stage, and waiting-on state (FEEDBACK-06)', async ({ page }) => {
    // Pick a document whose status is one of the canonical pipeline stages
    // (earlier tests may have closed the first row, and seeded data includes
    // terminal/error states like `analysis_failed` that don't have a live
    // pipeline indicator).
    const docs = await page.request.get(`${API}/documents`, {
      headers: { 'X-GovDoc-Role': 'supervisor' },
    }).then((r) => r.json());
    const pipelineStatuses = new Set([
      'received',
      'extracted',
      'analyzed',
      'routed',
      'under_review',
      'in_consultation',
    ]);
    const openDoc = (docs as Array<{ id: string; status: string }>).find((d) =>
      pipelineStatuses.has(d.status),
    );
    expect(openDoc, 'expected at least one non-terminal pipeline document').toBeTruthy();
    const docId = openDoc!.id;

    // --- Reviewer on a routed/under_review doc: sees Next steps + active stage ---
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Department Reviewer');
    await page.goto(`/documents/${docId}`);
    await idle(page);
    await page.waitForTimeout(500);

    // Pipeline visible
    const pipeline = page.locator('[data-testid="workflow-pipeline"]');
    await expect(pipeline).toBeVisible();

    // At least one pipeline stage should be active
    const activeStages = pipeline.locator('[data-status="active"]');
    await expect(activeStages.first()).toBeVisible();

    // Role context shows "Acting as Department Reviewer"
    const context = page.locator('[data-testid="workflow-context"]');
    await expect(context).toBeVisible();
    await expect(context).toContainText('Acting as Department Reviewer');
    await expect(context).toContainText(/Status:/);

    // There should be at least one action in "Next steps for you" for reviewer on this doc
    const available = page.locator('[data-testid="workflow-available-actions"]');
    if (await available.count() > 0) {
      await expect(available).toContainText(/Next steps for you/i);
    }

    // --- Intake Clerk on the same doc: sees "waiting on" or "no actions" message ---
    await switchRole(page, 'Intake Clerk');
    await page.goto(`/documents/${docId}`);
    await idle(page);
    await page.waitForTimeout(500);

    // Either waiting-on or empty state is visible
    const waitingOn = page.locator('[data-testid="workflow-waiting-on"]');
    const empty = page.locator('[data-testid="workflow-empty"]');
    const hasGuidance = (await waitingOn.count()) > 0 || (await empty.count()) > 0;
    expect(hasGuidance).toBe(true);

    // Context still shows the new active role
    await expect(page.locator('[data-testid="workflow-context"]')).toContainText('Acting as Intake Clerk');

    // --- Disabled-actions disclosure: supervisor may see some disabled actions ---
    await switchRole(page, 'Supervisor');
    await page.goto(`/documents/${docId}`);
    await idle(page);
    await page.waitForTimeout(500);

    const toggle = page.locator('[data-testid="workflow-disabled-toggle"]');
    if (await toggle.count() > 0) {
      await toggle.click();
      await expect(page.locator('[data-testid="workflow-disabled-list"]')).toBeVisible();
    }

    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);
  });

  // =========================================================================
  // Step 10 — Consultant role works (BUG-004 fix)
  // =========================================================================
  test('Step 10: Consultant role works (BUG-004)', async ({ page }) => {
    // Switch to Consultant role
    await page.goto('/');
    await idle(page);
    await switchRole(page, 'Consultant');

    // Navigate to consultation page
    await page.locator('nav').getByText('Consultation', { exact: true }).click();
    await expect(page).toHaveURL(/\/consultation$/);
    await idle(page);

    // Page should load without errors (BUG-004: consultant role caused crash)
    await expect(page.getByRole('heading', { name: /Internal Consultation/i })).toBeVisible({ timeout: 5000 });

    // The demo seed has doc3 in in_consultation state — it should appear
    await page.waitForTimeout(2000);
    const docCards = page.locator('[role="button"]');
    const count = await docCards.count();

    // Either there are consultation docs or an empty state message
    if (count > 0) {
      // Click the first consultation doc to verify thread loads
      await docCards.first().click();
      await page.waitForTimeout(1000);
      // The thread panel should be visible
      await expect(page.locator('[data-testid="consultation-thread"]')).toBeVisible({
        timeout: 5000,
      });
    }

    // BUG-001 check — no TypeError
    expect(consoleErrors.filter(e => e.includes('TypeError'))).toHaveLength(0);

    // BUG-004 check — no errors at all for consultant role
    expect(consoleErrors).toHaveLength(0);
  });
});
