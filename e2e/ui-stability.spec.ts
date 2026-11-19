import { test, expect } from '@playwright/test'

async function expectNoHorizontalOverflow(page: any) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)
  expect(overflow).toBeFalsy()
}

async function createWorkspace(page: any) {
  await page.goto('/projects')
  const title = `Visual Stability ${Date.now()}`
  await page.getByTestId('create-project-toggle').click()
  await page.fill('input#project-name', title)
  await page.fill('textarea#idea_dump', 'A prince hears dead gods beneath a divided kingdom.')
  await page.click('[data-testid="create-project"]')
  await expect(page).toHaveURL(/\/project\//, { timeout: 15000 })
}

const desktopViewports = [
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
]

test('Writing remains usable at 1280x720 with Toolbox and Companion open', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await createWorkspace(page)
  await page.getByTestId('section-drafting').click()
  const companion = page.getByTestId('workspace-companion')
  await companion.locator('button[aria-expanded]').click()
  await expect(companion).toHaveAttribute('data-constrained', 'true')
  const usableWidth = await page.getByTestId('workspace-main-viewport').evaluate((element) => {
    const styles = window.getComputedStyle(element)
    return element.clientWidth - parseFloat(styles.paddingLeft) - parseFloat(styles.paddingRight)
  })
  expect(usableWidth).toBeGreaterThanOrEqual(520)
  await expectNoHorizontalOverflow(page)
})

for (const viewport of desktopViewports) {
  test(`Projects page is stable at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.goto('/projects')
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test(`Workspace page is stable at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await createWorkspace(page)
    for (const section of [
      'discussion', 'vision', 'story-room', 'story-health', 'characters',
      'world', 'power', 'factions', 'relationships', 'threads', 'themes',
      'mysteries', 'readiness', 'knowledge', 'timeline', 'arcs',
      'arc-development', 'questions', 'insights', 'drafting', 'editorial',
      'manuscript', 'canon', 'canon-queue', 'project-timeline',
      'explainability-timeline', 'knowledge-graph', 'workflow', 'settings',
    ]) {
      await page.getByTestId(`section-${section}`).click()
      await expectNoHorizontalOverflow(page)
    }
  })
}

for (const viewport of desktopViewports) {
  test(`AI settings layout remains stable at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: 'AI Connections & Settings' })).toBeVisible()
    await expect(page.getByTestId('provider-card-gemini')).toBeVisible()
    await expect(page.getByTestId('provider-card-openrouter')).toBeVisible()
    await expect(page.getByTestId('agent-assignment-table')).toHaveCount(0)
    await page.getByRole('button', { name: 'Developer Mode' }).click()
    await expect(page.getByTestId('agent-assignment-table')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
}
