import { expect, test } from '@playwright/test'
import { openSection } from './nav'

test('new project opens a real workspace without generated fallback content', async ({ page }) => {
  await page.goto('/projects')
  const title = `Workspace Shell ${Date.now()}`
  await page.getByTestId('create-project-toggle').click()
  await page.fill('input#project-name', title)
  await page.fill('textarea#idea_dump', 'A city archives dreams as legal evidence.')
  await page.fill('input#genre', 'Speculative mystery')
  await page.fill('input#tone', 'Investigative')
  await page.getByTestId('create-project').click()

  await expect(page).toHaveURL(/\/project\//)
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  await openSection(page, 'vision')
  await expect(page.getByTestId('story-vision-panel')).toContainText('A city archives dreams as legal evidence.')
  await openSection(page, 'workflow')
  await expect(page.getByTestId('workflow-panel')).toContainText('Project activity will appear here after the story team completes its first task.')
  await expect(page.getByTestId('workflow-graph')).toHaveCount(0)
  await expect(page.locator('pre')).toHaveCount(0)
})
