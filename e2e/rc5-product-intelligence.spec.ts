import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { openSection } from './nav'
import fs from 'fs'


function apiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  if (fs.existsSync('.novelforge-ports.json')) {
    const ports = JSON.parse(fs.readFileSync('.novelforge-ports.json', 'utf-8'))
    return `http://127.0.0.1:${ports.backendPort || 8000}`
  }
  return 'http://127.0.0.1:8000'
}


async function waitForBackend(request: APIRequestContext, apiBase: string) {
  const started = Date.now()
  while (Date.now() - started < 120_000) {
    try {
      if ((await request.get(`${apiBase}/health`)).ok()) return
    } catch {
      // The frontend can become ready before backend migrations finish.
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('Backend did not become ready')
}


async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
}


test.describe('RC5 product intelligence and author experience', () => {
  test.setTimeout(240_000)

  test('application guidance, direct navigation, timelines, and companion form a clean author workflow', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const created = await request.post(`${apiBase}/api/projects`, {
      data: {
        title: `RC5 Experience ${Date.now()}`,
        premise: 'A mapmaker must reconcile seven kingdoms before their borders begin to move.',
        genre: 'Fantasy',
        themes: ['belonging'],
      },
    })
    expect(created.ok(), await created.text()).toBeTruthy()
    const projectId = (await created.json()).id

    const browserDefects: string[] = []
    page.on('console', (message) => {
      if (message.type() === 'error' || message.type() === 'warning') browserDefects.push(`${message.type()}: ${message.text()}`)
    })
    page.on('pageerror', (error) => browserDefects.push(`pageerror: ${error.message}`))

    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(`/project/${projectId}`)
    await expect(page.getByTestId('primary-project-dashboard')).toBeVisible({ timeout: 45_000 })
    await expect(page.getByTestId('book-progress')).toBeVisible()
    await expect(page.getByTestId('next-step-card')).toBeVisible()
    await expect(page.getByTestId('next-step-action')).toBeEnabled()

    await openSection(page, 'drafting')
    await expect(page.getByTestId('drafting-panel')).toBeVisible()
    await expect(page.getByText('Mara must escape the citadel before dawn.')).toHaveCount(0)
    await expect(page.getByText('The Gate', { exact: true })).toHaveCount(0)

    await openSection(page, 'canon')
    await expect(page.getByTestId('canon-dashboard')).toBeVisible()
    await page.getByTestId('canon-dashboard').getByRole('button', { name: 'Review Canon Queue' }).click()
    await expect(page.getByTestId('canon-queue-panel')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1, name: 'Proposed changes' })).toBeVisible()

    await openSection(page, 'workflow')
    await expect(page.getByTestId('workflow-developer-details')).toHaveCount(0)
    await expect(page.getByText('Story-team calls')).toHaveCount(0)
    await page.getByTestId('workflow-panel').getByRole('button', { name: 'Developer Mode' }).click()
    await expect(page.getByTestId('workflow-developer-details')).toBeVisible()
    await openSection(page, 'settings')
    await expect(page.getByTestId('workspace-settings-panel')).not.toContainText('Cognition Events')
    await expect(page.getByTestId('workspace-settings-panel')).not.toContainText('Calls:')

    await openSection(page, 'project-timeline')
    await expect(page.getByTestId('project-timeline')).toContainText('how the NovelForge project changed')
    await openSection(page, 'explainability-timeline')
    await expect(page.getByTestId('explainability-timeline')).toContainText('what changed, why the score moved, and where to act')

    await page.getByTestId('nav-assistant').click()
    await expect(page.getByTestId('interactive-assistant-drawer')).toBeVisible()
    await page.getByLabel('Ask the project assistant').fill('What does Arc Board do?')
    await page.getByTestId('ask-project-assistant').click()
    const answer = page.getByTestId('assistant-message').last()
    await expect(answer).toContainText('Application guide', { timeout: 30_000 })
    await expect(answer).toContainText('Arc Board')
    await expect(answer).not.toContainText('Analysis ')
    await answer.getByTestId('assistant-navigation-action').first().click()
    await expect(page.getByTestId('arcs-panel')).toBeVisible()

    await expect(page.getByTestId('workspace-companion')).toHaveCount(0)
    await page.screenshot({ path: 'artifacts/rc5-workspace-desktop.png', fullPage: true })

    const feed = await (await request.get(`${apiBase}/api/projects/${projectId}/workspace-companion`)).json()
    const messageIds = (feed.messages || []).map((message: { message_id: string }) => message.message_id)
    expect(new Set(messageIds).size).toBe(messageIds.length)

    await openSection(page, 'knowledge-graph')
    await expect(page.getByTestId('knowledge-graph-panel')).toBeVisible()
    await expect(page.getByTestId('knowledge-graph-panel')).not.toContainText('node_id')
    await expect(page.getByTestId('knowledge-graph-panel')).not.toContainText('raw_payload')

    for (const viewport of [
      { width: 1366, height: 768 },
      { width: 1440, height: 900 },
      { width: 1920, height: 1080 },
      { width: 2560, height: 1440 },
    ]) {
      await page.setViewportSize(viewport)
      await expectNoHorizontalOverflow(page)
    }

    expect(browserDefects).toEqual([])
  })

  test('developer details stay opt-in on settings', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: 'AI settings' })).toBeVisible()
    await expect(page.getByTestId('execution-settings')).toHaveCount(0)
    await expect(page.getByTestId('agent-assignment-table')).toHaveCount(0)
    await page.getByRole('button', { name: 'Advanced' }).click()
    await expect(page.getByTestId('execution-settings')).toBeVisible()
    await expect(page.getByTestId('agent-assignment-table')).toBeVisible()
  })
})
