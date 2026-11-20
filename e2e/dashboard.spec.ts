import { test, expect } from '@playwright/test'
import { openSection } from './nav'

test.describe('Projects workspace', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects')
  })

  test('shows project library controls', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Your novels' })).toBeVisible()
    await expect(page.getByTestId('project-search')).toBeVisible()
    await expect(page.getByTestId('create-project-toggle')).toBeVisible()
  })

  test('creates a project and opens the workspace', async ({ page }) => {
    const title = `Studio ${Date.now()}`
    await page.getByTestId('create-project-toggle').click()
    await page.fill('input#project-name', title)
    await page.fill('textarea#idea_dump', 'A sister becomes important after the first arc.')
    await page.fill('input#genre', 'Progression Fantasy')
    await page.fill('input#tone', 'Mythic')
    await page.getByTestId('create-project').click()
    await expect(page).toHaveURL(/\/project\//, { timeout: 15000 })
    await expect(page.getByTestId('next-step-card')).toBeVisible()
    await expect(page.getByTestId('book-progress')).toBeVisible()
    await expect(page.getByTestId('primary-project-dashboard')).toBeVisible()
    await openSection(page, 'discussion')
    await expect(page.getByTestId('workspace-run-discussion-cycle')).toBeVisible()
  })
})
