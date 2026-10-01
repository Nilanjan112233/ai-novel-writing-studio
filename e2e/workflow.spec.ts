import { expect, test } from '@playwright/test'

test('new project opens a real workspace without generated fallback content', async ({ page }) => {
  await page.goto('/projects')
  const title = `Workspace Shell ${Date.now()}`
  await page.getByTestId('create-project-toggle').click()
  await page.fill('input#title', title)
  await page.fill('textarea#idea_dump', 'A city archives dreams as legal evidence.')
  await page.fill('input#genre', 'Speculative mystery')
  await page.fill('input#tone', 'Investigative')
  await page.getByTestId('create-project').click()

  await expect(page).toHaveURL(/\/project\//)
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  await page.getByTestId('section-vision').click()
  await expect(page.getByTestId('story-vision-panel')).toContainText('A city archives dreams as legal evidence.')
  await page.getByTestId('section-workflow').click()
  await expect(page.getByTestId('workflow-panel')).toContainText('Project activity will appear here after the story team completes its first task.')
  await expect(page.getByTestId('workflow-graph')).toHaveCount(0)
  await expect(page.locator('pre')).toHaveCount(0)
})
