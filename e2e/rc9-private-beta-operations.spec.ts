import { expect, test } from '@playwright/test'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

test('author can back up, modify, restore a verified copy, and keep the original', async ({ page, request }) => {
  test.setTimeout(180_000)
  const sourcePremise = 'A mapmaker must return a stolen season before her village forgets spring.'
  const created = await request.post(`${apiBase}/api/projects`, { data: {
    title: `RC9 Recovery Journey ${Date.now()}`,
    premise: sourcePremise,
    genre: 'Fantasy Mystery',
    tone: 'Hopeful and tense',
  } })
  expect(created.ok(), await created.text()).toBeTruthy()
  const project = await created.json()

  await page.goto(`/project/${project.id}?section=settings`)
  const panel = page.getByTestId('project-backups')
  await expect(panel).toBeVisible({ timeout: 60_000 })

  const downloadPromise = page.waitForEvent('download')
  await panel.getByRole('button', { name: 'Back up and download' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/\.novelforge-backup$/)
  await expect(panel.getByRole('status')).toContainText('editable project state')
  await expect(panel).toContainText('records')

  const changedPremise = 'The mapmaker now intends to keep winter forever.'
  const changed = await request.put(`${apiBase}/api/projects/${project.id}`, { data: {
    premise: changedPremise,
  } })
  expect(changed.ok(), await changed.text()).toBeTruthy()

  await panel.getByRole('button', { name: 'Check for restore' }).click()
  const preview = panel.getByTestId('restore-preview')
  await expect(preview).toBeVisible()
  await expect(preview).toContainText('current project and approved prose will remain unchanged')
  await preview.getByLabel('Restored project name').fill('Spring Archive Restored')
  await preview.getByRole('button', { name: 'Restore as new project' }).click()
  await expect(panel.getByRole('status')).toContainText('original project was not changed')

  const restoredLink = panel.getByRole('link', { name: 'Open Spring Archive Restored' })
  const restoredPath = await restoredLink.getAttribute('href')
  expect(restoredPath).toMatch(/^\/project\/[a-f0-9]{24}$/)
  const restoredId = restoredPath!.split('/').pop()!

  const original = await request.get(`${apiBase}/api/projects/${project.id}`)
  const restored = await request.get(`${apiBase}/api/projects/${restoredId}`)
  expect((await original.json()).premise).toBe(changedPremise)
  expect((await restored.json()).premise).toBe(sourcePremise)
  await expect(preview).toHaveCount(0)
})

test('first-run operations explain privacy, diagnostics, and categorized feedback', async ({ page }) => {
  test.setTimeout(120_000)
  await page.goto('/settings')
  // Privacy, diagnostics and feedback live under Advanced in the redesigned settings page.
  await page.getByRole('button', { name: 'Advanced' }).click()
  const readiness = page.getByTestId('operational-readiness')
  await expect(readiness).toBeVisible({ timeout: 60_000 })
  await expect(readiness).toContainText('AI outages never hide existing projects')
  await expect(readiness).toContainText('Hosted multi-tenant use is not supported')
  await expect(readiness).toContainText('Project backups:')

  const supportDownload = page.waitForEvent('download')
  await readiness.getByRole('button', { name: 'Download safe diagnostics' }).click()
  await supportDownload
  await expect(readiness.getByRole('status')).toContainText('Story content and credentials were not included')

  await readiness.getByLabel('Feedback type').selectOption('confusing-ux')
  await readiness.getByLabel('Private beta feedback').fill('I expected the backup location to be easier to find.')
  await readiness.getByRole('checkbox', { name: 'Include sanitized diagnostics' }).check()
  await readiness.getByRole('button', { name: 'Save feedback locally' }).click()
  await expect(readiness.getByRole('status')).toContainText('saved in this local NovelForge installation')
})
