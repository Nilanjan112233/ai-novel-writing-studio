import { expect, test } from '@playwright/test'
import { openSection } from './nav'


test('milestone pipeline, critique, canon explorer, and guide form one workspace', async ({ page, request }) => {
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
  await expect(page.getByTestId('primary-project-dashboard')).toBeVisible({ timeout: 45_000 })
  await expect(page.getByTestId('next-step-card')).toBeVisible()
  await expect(page.getByTestId('workspace-companion')).toHaveCount(0)

  await openSection(page, 'story-health')
  await expect(page.getByTestId('narrative-critique-panel')).toContainText('Improvements remain author-controlled proposals')

  await openSection(page, 'guide')
  await expect(page.getByTestId('novel-creation-guide')).toBeVisible({ timeout: 45_000 })
  await expect(page.getByTestId('novel-creation-guide')).toContainText('Story vision')
  await expect(page.getByTestId('novel-creation-guide')).toContainText('Publication readiness')
  const pipeline = page.getByTestId('narrative-production-pipeline')
  await expect(pipeline).toBeVisible({ timeout: 45_000 })
  await expect(pipeline).toContainText('Concept Complete')
  await expect(pipeline).toContainText('Publication Ready')

  await openSection(page, 'canon')
  await expect(page.getByTestId('canon-dashboard')).toBeVisible()
  await expect(page.getByLabel('Search all official canon')).toBeVisible()
  await expect(page.getByLabel('Filter canon status')).toContainText('Active and inactive')
})
