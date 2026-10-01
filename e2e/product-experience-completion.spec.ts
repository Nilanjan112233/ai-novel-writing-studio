import { expect, test } from '@playwright/test'


test('milestone pipeline, critique, canon explorer, guide, and companion form one workspace', async ({ page, request }) => {
  const created = await request.post('http://localhost:8000/api/projects', {
    data: {
      title: `Experience Completion ${Date.now()}`,
      premise: 'A cartographer must map seven kingdoms before their borders move.',
      genre: 'Fantasy',
      tone: 'Wonder',
      themes: ['belonging'],
    },
  })
  expect(created.ok()).toBeTruthy()
  const project = await created.json()

  await page.goto(`/project/${project.id}`)
  await expect(page.getByTestId('primary-story-health-dashboard')).toBeVisible({ timeout: 45_000 })
  const pipeline = page.getByTestId('narrative-production-pipeline')
  await expect(pipeline).toBeVisible({ timeout: 45_000 })
  await expect(pipeline).toContainText('Concept Complete')
  await expect(pipeline).toContainText('World Ready')
  await expect(pipeline).toContainText('Draft Ready')
  await expect(pipeline).toContainText('Revision Ready')
  await expect(pipeline).toContainText('Publication Ready')
  await expect(page.getByTestId('narrative-critique-panel')).toContainText('Improvements remain author-controlled proposals')

  const companion = page.getByTestId('workspace-companion')
  await expect(companion).toBeVisible({ timeout: 45_000 })
  await companion.locator('button').last().click()
  await expect(companion).toContainText('Workspace Companion')
  await expect(companion).toContainText('Ask how this page works')

  await page.getByTestId('section-guide').click()
  await expect(page.getByTestId('novel-creation-guide')).toBeVisible({ timeout: 45_000 })
  await expect(page.getByTestId('novel-creation-guide')).toContainText('Story vision')
  await expect(page.getByTestId('novel-creation-guide')).toContainText('Publication readiness')

  await page.getByTestId('section-canon').click()
  await expect(page.getByTestId('canon-dashboard')).toBeVisible()
  await expect(page.getByLabel('Search all official canon')).toBeVisible()
  await expect(page.getByLabel('Filter canon status')).toContainText('Active and inactive')
})
