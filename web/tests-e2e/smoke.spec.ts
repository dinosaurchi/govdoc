import { test, expect } from '@playwright/test';

const BASE_URL = 'http://172.17.0.1:3000';

test.describe('GovDoc SecureFlow — Smoke Tests', () => {

  test('1. App loads — homepage renders without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // Page should have a non-empty body
    const bodyText = await page.textContent('body');
    expect(bodyText?.length).toBeGreaterThan(0);
    console.log(`Page content length: ${bodyText?.length} chars`);

    // No JS errors during load
    expect(errors).toHaveLength(0);

    // Screenshot for visual verification
    await page.screenshot({ path: '/tmp/govdoc-home.png', fullPage: true });
    console.log('Screenshot saved: /tmp/govdoc-home.png');
  });

  test('2. Role selector is visible and functional', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // The header contains the role selector
    const roleSelect = page.locator('header select');
    await expect(roleSelect).toBeVisible({ timeout: 5000 });

    // Verify all four role options exist
    const options = roleSelect.locator('option');
    await expect(options).toHaveCount(4);

    const optionTexts = await options.allTextContents();
    expect(optionTexts).toEqual([
      'Intake Clerk',
      'Department Reviewer',
      'Consultant',
      'Supervisor',
    ]);
    console.log('Role options:', optionTexts.join(', '));

    // Verify default is Intake Clerk
    await expect(roleSelect).toHaveValue('Intake Clerk');

    // Switch role to Supervisor
    await roleSelect.selectOption('Supervisor');
    await expect(roleSelect).toHaveValue('Supervisor');

    await page.screenshot({ path: '/tmp/govdoc-role-supervisor.png', fullPage: true });
  });

  test('3. Dashboard accessible with metrics', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // Navigate to dashboard
    await page.getByRole('link', { name: 'Dashboard' }).click();
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/dashboard');

    // Verify heading
    await expect(page.getByRole('heading', { name: 'System Dashboard' })).toBeVisible({ timeout: 5000 });

    // Verify stat cards are present (4 metric cards)
    const statLabels = ['Total Received', 'Pending Review', 'Consultations', 'Closed Today'];
    for (const label of statLabels) {
      await expect(page.getByText(label, { exact: false })).toBeVisible({ timeout: 5000 });
    }

    // Wait for API data to load — values should not be '...' after loading
    await page.waitForTimeout(2000);
    const pageText = await page.textContent('body');
    // The API returns numbers, so at least one stat should show a digit
    expect(pageText).toMatch(/\d/);
    console.log('Dashboard loaded with metrics');

    await page.screenshot({ path: '/tmp/govdoc-dashboard.png', fullPage: true });
  });

  test('4. Intake page shows upload form', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // Ensure role is Intake Clerk (default)
    const roleSelect = page.locator('header select');
    await roleSelect.selectOption('Intake Clerk');

    // Navigate to intake page (use header nav link — the exact match)
    await page.getByRole('link', { name: 'Intake', exact: true }).click();
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/intake');

    // Verify heading
    await expect(page.getByRole('heading', { name: 'Document Intake' })).toBeVisible({ timeout: 5000 });

    // Verify upload button is visible (the big dashed-border upload area)
    await expect(page.getByText('Choose file to upload')).toBeVisible({ timeout: 5000 });

    // Verify intake guidelines card is present
    await expect(page.getByText('Intake Guidelines')).toBeVisible();

    // Verify file input exists (hidden)
    const fileInput = page.locator('input[type="file"]');
    expect(await fileInput.count()).toBe(1);

    // No restricted access warning should be shown for Intake Clerk
    await expect(page.getByText('Restricted Access')).not.toBeVisible();

    await page.screenshot({ path: '/tmp/govdoc-intake.png', fullPage: true });
  });

  test('4b. Intake page shows restricted access for non-clerk role', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // Switch to Consultant (should not have intake access)
    const roleSelect = page.locator('header select');
    await roleSelect.selectOption('Consultant');

    // Navigate to intake page (use header nav link — the exact match)
    await page.getByRole('link', { name: 'Intake', exact: true }).click();
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/intake');

    // Verify restricted access warning
    await expect(page.getByText('Restricted Access')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/does not have permission/)).toBeVisible();

    await page.screenshot({ path: '/tmp/govdoc-intake-restricted.png', fullPage: true });
  });

  test('5. Document list (Review Queue) is accessible', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // Navigate to review page (use header nav link — the exact match)
    await page.getByRole('link', { name: 'Review', exact: true }).click();
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/review');

    // Verify heading
    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 5000 });

    // Wait for documents to load (or empty state)
    await page.waitForTimeout(3000);

    // Either documents are listed or "No documents" message is shown
    const hasDocuments = await page.locator('table tbody tr').count() > 0;
    const hasEmptyState = await page.getByText('No documents in queue').isVisible().catch(() => false);

    expect(hasDocuments || hasEmptyState).toBeTruthy();
    console.log(`Documents in queue: ${hasDocuments ? 'yes' : 'no (empty state shown)'}`);

    // If there are documents, verify the table headers
    if (hasDocuments) {
      await expect(page.getByText('Title')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
      await expect(page.getByText('Urgency')).toBeVisible();
    }

    await page.screenshot({ path: '/tmp/govdoc-review.png', fullPage: true });
  });

  test('6. Navigation header links are all functional', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    const navLinks = ['Dashboard', 'Intake', 'Review', 'Consultation', 'Response'];

    for (const linkText of navLinks) {
      await page.getByRole('link', { name: linkText }).first().click();
      await page.waitForLoadState('networkidle');
      // Verify navigation happened (URL should change from just /)
      const url = page.url();
      expect(url).not.toBe(BASE_URL + '/');
      console.log(`  ✓ Navigated to "${linkText}" → ${url}`);

      // Go back to home for next iteration
      await page.goto(BASE_URL + '/');
      await page.waitForLoadState('networkidle');
    }

    await page.screenshot({ path: '/tmp/govdoc-nav-test.png', fullPage: true });
  });

  test('7. Consultation and Response pages load', async ({ page }) => {
    // Consultation page
    await page.goto(BASE_URL + '/consultation');
    await page.waitForLoadState('networkidle');
    const consultationText = await page.textContent('body');
    expect(consultationText?.length).toBeGreaterThan(0);
    await page.screenshot({ path: '/tmp/govdoc-consultation.png', fullPage: true });
    console.log('Consultation page loaded');

    // Response page
    await page.goto(BASE_URL + '/response');
    await page.waitForLoadState('networkidle');
    const responseText = await page.textContent('body');
    expect(responseText?.length).toBeGreaterThan(0);
    await page.screenshot({ path: '/tmp/govdoc-response.png', fullPage: true });
    console.log('Response page loaded');
  });

  test('8. Brand header and SecureFlow branding', async ({ page }) => {
    await page.goto(BASE_URL + '/');
    await page.waitForLoadState('networkidle');

    // Verify brand name
    await expect(page.getByRole('link', { name: 'SecureFlow' })).toBeVisible({ timeout: 5000 });

    // Verify header has the Active Role label
    await expect(page.getByText('Active Role', { exact: false })).toBeVisible();

    // Homepage hero heading
    await expect(page.getByText('GovDoc', { exact: false })).toBeVisible();
    // "SecureFlow" appears twice (header + hero), use .first()
    await expect(page.getByText('SecureFlow', { exact: false }).first()).toBeVisible();

    await page.screenshot({ path: '/tmp/govdoc-branding.png', fullPage: true });
  });
});
