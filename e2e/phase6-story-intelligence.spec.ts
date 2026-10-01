import { APIRequestContext, expect, test } from '@playwright/test'
import fs from 'fs'
import path from 'path'


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
  while (Date.now() - started < 120000) {
    try {
      if ((await request.get(`${apiBase}/health`)).ok()) return
    } catch {
      // The frontend can be ready before backend migrations finish.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Backend did not become ready')
}


test.describe('Phase 6 unified Story Intelligence platform', () => {
  test.setTimeout(180000)

  test('uses one cached graph for the primary health dashboard and domain evidence', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const created = await request.post(`${apiBase}/api/projects`, {
      data: {
        title: `Phase 6 Browser Proof ${Date.now()}`,
        premise: 'A cartographer discovers that one city exists on two incompatible calendars.',
        genre: 'Fantasy mystery',
        tone: 'Investigative',
      },
    })
    expect(created.ok(), await created.text()).toBeTruthy()
    const projectId = (await created.json()).id

    const first = await request.post(`${apiBase}/api/projects/${projectId}/narrative-analysis`, { data: {} })
    expect(first.ok(), await first.text()).toBeTruthy()
    const firstData = await first.json()
    expect(firstData.snapshot.scores.overall).toBe(100)
    expect(firstData.snapshot.stats.incremental).toBeTruthy()

    const cached = await request.post(`${apiBase}/api/projects/${projectId}/narrative-analysis`, { data: {} })
    expect(cached.ok(), await cached.text()).toBeTruthy()
    const cachedData = await cached.json()
    expect(cachedData.snapshot.analysis_id).toBe(firstData.snapshot.analysis_id)
    expect(cachedData.snapshot.stats.recomputed_nodes).toBe(0)
    expect(cachedData.snapshot.stats.cache_hit).toBeTruthy()

    for (const domain of ['character', 'canon', 'timeline', 'plot', 'pacing', 'continuity', 'balance']) {
      const response = await request.get(`${apiBase}/api/projects/${projectId}/narrative-intelligence/${domain}`)
      expect(response.ok(), await response.text()).toBeTruthy()
      expect((await response.json()).score).toBe(100)
    }

    await page.setViewportSize({ width: 1440, height: 1000 })
    const desktopBootstrapResponse = page.waitForResponse(
      (response) => response.url().endsWith(`/api/projects/${projectId}/workspace-bootstrap`) && response.ok(),
    )
    await page.goto(`/project/${projectId}`)
    expect((await (await desktopBootstrapResponse).json()).story_health.story_health_score).toBe(100)
    await expect(page.getByText('Narrative Intelligence Platform')).toBeVisible()
    await expect(page.getByTestId('primary-story-health-dashboard')).toBeVisible()
    await expect(page.getByTestId('narrative-intelligence-platform')).toBeVisible()
    await expect(page.getByTestId('story-health-score')).toHaveText('100', { timeout: 15000 })
    await expect(page.getByTestId('analysis-cache-stats')).toHaveCount(0)
    await expect(page.getByTestId('health-character')).toContainText('100')
    const artifactDir = path.resolve('artifacts')
    fs.mkdirSync(artifactDir, { recursive: true })
    await page.screenshot({ path: path.join(artifactDir, 'phase6-story-health-desktop.png'), fullPage: true })
    await page.getByRole('tab', { name: 'Timeline' }).click()
    await expect(page.getByTestId('narrative-findings')).toContainText('No active findings')

    await page.getByTestId('section-canon').click()
    await expect(page.getByTestId('canon-panel')).toBeVisible()
    await page.getByTestId('section-timeline').click()
    await expect(page.getByTestId('story-timeline-panel')).toBeVisible()
    await page.getByTestId('section-characters').click()
    await expect(page.getByTestId('characters-panel')).toBeVisible()
    await page.getByTestId('section-threads').click()
    await expect(page.getByTestId('threads-panel')).toBeVisible()

    await page.setViewportSize({ width: 390, height: 844 })
    const mobileBootstrapResponse = page.waitForResponse(
      (response) => response.url().endsWith(`/api/projects/${projectId}/workspace-bootstrap`) && response.ok(),
    )
    await page.goto(`/project/${projectId}`)
    expect((await (await mobileBootstrapResponse).json()).story_health.story_health_score).toBe(100)
    await expect(page.getByTestId('primary-story-health-dashboard')).toBeVisible()
    await expect(page.getByTestId('story-health-score')).toHaveText('100', { timeout: 15000 })
    await expect(page.getByTestId('health-character')).toContainText('100')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy()
    const timelineTab = page.getByRole('tab', { name: 'Timeline' })
    await timelineTab.focus()
    await expect(timelineTab).toBeFocused()
    await page.screenshot({ path: path.join(artifactDir, 'phase6-story-health-mobile.png'), fullPage: true })
  })
})
