import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import fs from 'fs'
import { MongoClient, ObjectId } from 'mongodb'
import AxeBuilder from '@axe-core/playwright'

const createdProjectIds = new Set<string>()


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
      if ((await request.get(`${apiBase}/health/ready`)).ok()) return
    } catch {
      // Frontend readiness can precede the database migration.
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('Backend did not become ready')
}


async function createProject(request: APIRequestContext, apiBase: string, label: string) {
  const title = `${label} ${Date.now()}`
  const response = await request.post(`${apiBase}/api/projects`, {
    data: {
      title,
      idea_dump: 'A cartographer discovers that erased roads remember their travelers.',
      genre: 'Fantasy mystery',
      tone: 'Wonder with unease',
    },
  })
  expect(response.ok(), await response.text()).toBeTruthy()
  const project = { ...(await response.json()), title }
  createdProjectIds.add(project.id)
  return project
}


async function assertNoOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)
}


test.describe('post-RC5 commercial hardening', () => {
  test.setTimeout(240_000)
  test.afterEach(async ({ request }) => {
    const apiBase = apiBaseUrl()
    for (const projectId of Array.from(createdProjectIds)) {
      const response = await request.delete(`${apiBase}/api/projects/${projectId}`)
      if (response.ok() || response.status() === 404) createdProjectIds.delete(projectId)
    }
  })

  test('project lifecycle is recoverable, explicit, and discoverable', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const project = await createProject(request, apiBase, 'Lifecycle E2E')

    await page.goto('/projects')
    await page.getByTestId('project-search').fill(project.title)
    const card = page.getByTestId('project-card').filter({ hasText: project.title })
    await expect(card).toBeVisible()
    const openActions = async () => {
      await card.locator('..').getByRole('button', { name: `More actions for ${project.title}` }).click()
    }
    await openActions()
    await card.locator('..').getByTestId('delete-project').click()
    await expect(page.getByRole('dialog')).toContainText('preserved')
    await page.getByTestId('confirm-trash-project').click()

    await page.getByTestId('projects-view-trash').click()
    await expect(page.getByText(project.title, { exact: true })).toBeVisible()
    await openActions()
    await page.getByTestId('restore-project').click()
    await page.getByTestId('projects-view-active').click()
    await expect(page.getByText(project.title, { exact: true })).toBeVisible()

    await openActions()
    await page.getByTestId('archive-project').click()
    await page.getByTestId('projects-view-archived').click()
    await expect(page.getByText(project.title, { exact: true })).toBeVisible()
    await openActions()
    await page.getByTestId('unarchive-project').click()
    await page.getByTestId('projects-view-active').click()

    await openActions()
    await page.getByTestId('duplicate-project').click()
    await expect(page.getByRole('dialog')).toContainText('setup only')
    await expect(page.getByTestId('duplicate-story-content')).toBeVisible()
    await page.getByRole('button', { name: 'Cancel' }).click()
  })

  test('deep links, browser history, command navigation, and companion docking work cleanly', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const project = await createProject(request, apiBase, 'Navigation E2E')
    const defects: string[] = []
    page.on('console', (message) => {
      if (['warning', 'error'].includes(message.type())) defects.push(`${message.type()}: ${message.text()}`)
    })
    page.on('pageerror', (error) => defects.push(`pageerror: ${error.message}`))

    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(`/project/${project.id}?section=canon-queue`)
    await expect(page.getByTestId('canon-queue-panel')).toBeVisible({ timeout: 60_000 })

    await page.keyboard.press('Control+k')
    await expect(page.getByTestId('workspace-command-search')).toBeVisible()
    await page.getByTestId('workspace-command-search').fill('Story Timeline')
    await page.getByRole('button', { name: /Story Timeline/ }).click()
    await expect(page).toHaveURL(/section=timeline/)
    await expect(page.getByTestId('story-timeline-panel')).toBeVisible()
    await page.goBack()
    await expect(page.getByTestId('canon-queue-panel')).toBeVisible()

    const companion = page.getByTestId('workspace-companion')
    const readAcknowledgement = page.waitForResponse(
      (response) => response.url().endsWith(`/api/projects/${project.id}/workspace-companion/read`)
        && response.request().method() === 'POST',
    )
    await companion.locator('button[aria-expanded]').click()
    await expect(companion).toHaveAttribute('data-dock', 'right')
    await companion.getByLabel('Dock companion on the left').click()
    await expect(companion).toHaveAttribute('data-dock', 'left')
    await assertNoOverflow(page)
    expect((await readAcknowledgement).ok()).toBeTruthy()

    await page.getByTestId('nav-assistant').click()
    await page.getByLabel('Ask the project assistant').fill('How do I publish?')
    await page.getByTestId('ask-project-assistant').click()
    const answer = page.getByTestId('assistant-message').last()
    await expect(answer).toContainText('Publication export', { timeout: 30_000 })
    await expect(answer).toContainText('DOCX')
    await answer.getByTestId('assistant-navigation-action').first().click()
    await expect(page.getByTestId('manuscript-panel')).toBeVisible()

    for (const viewport of [
      { width: 1366, height: 768 },
      { width: 1440, height: 900 },
      { width: 1920, height: 1080 },
      { width: 2560, height: 1440 },
    ]) {
      await page.setViewportSize(viewport)
      await assertNoOverflow(page)
    }
    expect(defects).toEqual([])
  })

  test('approved manuscript exports a downloadable multi-format package', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const project = await createProject(request, apiBase, 'Publication E2E')
    const manuscriptId = `manuscript-${Date.now()}`
    const versionId = `version-${Date.now()}`
    const mongo = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017')
    await mongo.connect()
    const db = mongo.db(process.env.DATABASE_NAME || 'novelforge')
    const now = new Date()
    await db.collection('manuscripts').insertOne({
      project_id: new ObjectId(project.id),
      manuscript_id: manuscriptId,
      title: 'The Remembering Roads',
      status: 'approved',
      active: true,
      version: 1,
      current_version_id: versionId,
      created_at: now,
      updated_at: now,
    })
    await db.collection('manuscript_versions').insertOne({
      project_id: new ObjectId(project.id),
      manuscript_id: manuscriptId,
      version_id: versionId,
      version_number: 1,
      validation_result: 'PASS',
      chapter_count: 2,
      created_at: now,
      source_chapters: [
        { chapter_number: 1, title: 'The Missing Road', text: 'Mara unfolded the map.' },
        { chapter_number: 2, title: 'The Road Remembers', text: 'Ink moved beneath her hand.' },
      ],
    })
    await mongo.close()

    await page.goto(`/project/${project.id}?section=manuscript`)
    await expect(page.getByTestId('publication-export')).toBeVisible({ timeout: 60_000 })
    await page.getByTestId('create-publication-export').click()
    const packageButton = page.getByRole('button', { name: 'Complete Package' })
    await expect(packageButton).toBeVisible({ timeout: 60_000 })
    const downloadPromise = page.waitForEvent('download')
    await packageButton.click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/publication-package\.zip$/)
    const saved = testInfo.outputPath(download.suggestedFilename())
    await download.saveAs(saved)
    expect(fs.statSync(saved).size).toBeGreaterThan(1000)
  })

  test('projects and primary workspace have no serious accessibility violations', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const project = await createProject(request, apiBase, 'Accessibility E2E')
    for (const destination of ['/projects', `/project/${project.id}?section=dashboard`]) {
      await page.goto(destination)
      if (destination === '/projects') {
        await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible()
      } else {
        await expect(page.getByTestId('primary-story-health-dashboard')).toBeVisible({ timeout: 60_000 })
      }
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze()
      const serious = results.violations.filter(
        (violation) => violation.impact === 'serious' || violation.impact === 'critical',
      )
      expect(serious, serious.map((item) => `${item.id}: ${item.help}`).join('\n')).toEqual([])
    }
  })
})
