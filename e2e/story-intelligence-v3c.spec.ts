import { APIRequestContext, expect, test } from '@playwright/test'
import { openSection } from './nav'
import { MongoClient } from 'mongodb'
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
      // Frontend readiness can precede backend migrations.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Backend did not become ready')
}


async function validationProjectId() {
  const mongo = new MongoClient(
    process.env.MONGODB_URL || 'mongodb://localhost:27017',
  )
  await mongo.connect()
  const project = await mongo
    .db(process.env.DATABASE_NAME || 'novelforge')
    .collection('projects')
    .findOne(
      { title: 'Phase 3C Validation: The Bell Beneath Winter' },
      { sort: { created_at: -1 } },
    )
  await mongo.close()
  if (!project) throw new Error('Run backend/scripts/run_phase_3c_validation.py first')
  return project._id.toString()
}


test.describe('Phase 3C story intelligence and author experience', () => {
  test.setTimeout(600000)

  test('renders long-run health and captures production workspaces', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const projectId = await validationProjectId()

    const audit = await request.post(`${apiBase}/api/projects/${projectId}/story-audit`, {
      data: { include_agent: false },
    })
    expect(audit.ok(), await audit.text()).toBeTruthy()
    const health = await request.get(`${apiBase}/api/projects/${projectId}/story-health`)
    expect(health.ok(), await health.text()).toBeTruthy()
    const healthData = await health.json()
    expect(healthData.metrics.total_chapters).toBe(50)
    expect(healthData.metrics.total_words).toBeGreaterThanOrEqual(70000)
    expect(healthData.metrics.total_words).toBeLessThanOrEqual(100000)

    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`/project/${projectId}`)
    await expect(page.getByTestId('book-progress')).toBeVisible()
    await expect(
      page.getByTestId('primary-project-dashboard').getByRole('heading', {
        name: 'Phase 3C Validation: The Bell Beneath Winter',
        exact: true,
      }),
    ).toBeVisible()

    const artifactDir = path.resolve('artifacts')
    fs.mkdirSync(artifactDir, { recursive: true })
    const captures = [
      ['story-health', 'story-health-panel', 'phase-3c-story-health.png'],
      ['story-room', 'story-room-panel', 'phase-3c-story-room.png'],
      ['arc-development', 'arc-development-panel', 'phase-3c-arc-workspace.png'],
      ['editorial', 'editorial-panel', 'phase-3c-editorial-workspace.png'],
      ['manuscript', 'manuscript-panel', 'phase-3c-manuscript-workspace.png'],
      ['canon', 'canon-panel', 'phase-3c-canon-dashboard.png'],
    ]
    for (const [section, panel, filename] of captures) {
      await openSection(page, section)
      await expect(page.getByTestId(panel)).toBeVisible()
      if (section === 'story-health') {
        await expect(page.getByTestId('story-health-score')).not.toHaveText('--')
        await expect(page.getByTestId(panel)).toContainText('89,063')
      }
      if (section === 'story-room') {
        await expect(page.getByTestId(panel)).not.toContainText('synchronizing')
        await expect(page.getByTestId(panel)).toContainText('Current Arc')
      }
      await page.screenshot({
        path: path.join(artifactDir, filename),
        fullPage: true,
      })
    }

    await openSection(page, 'story-health')
    await expect(page.getByTestId('story-health-score')).not.toHaveText('--')
    await page.getByLabel('Change target').fill('Mara Venn')
    await page.getByTestId('preview-change-impact').click()
    await expect(page.getByTestId('change-impact-preview')).toBeVisible()
    await expect(page.getByTestId('change-impact-preview')).toContainText(
      'affected records',
    )
  })

  test('keeps the author workspace usable at a mobile viewport', async ({ page }) => {
    const projectId = await validationProjectId()
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`/project/${projectId}`)
    // Story Health is the default surface and the toolbox is intentionally
    // collapsed on mobile, so no hidden navigation control should be clicked.
    await expect(page.getByTestId('primary-project-dashboard')).toBeVisible()
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow).toBeLessThanOrEqual(1)
  })

  test('runs one read-only StoryAuditorAgent call with configured Gemini', async ({ request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const projectId = await validationProjectId()
    const providersResponse = await request.get(`${apiBase}/api/settings/ai`)
    expect(providersResponse.ok()).toBeTruthy()
    const providers = await providersResponse.json()
    const gemini = providers.providers?.gemini
    test.skip(!gemini?.configured, 'Gemini is not configured in NovelForge settings')
    const model = gemini.model || 'gemini-3.1-flash-lite'

    const execution = await request.put(`${apiBase}/api/settings/execution`, {
      data: {
        execution_mode: 'full',
        default_provider: 'gemini',
        default_model: model,
        enable_dynamic_routing: true,
        enable_reflection_loops: false,
        max_cycle_cost_usd: 2,
        max_agent_calls_per_cycle: 10,
        max_orchestration_depth: 5,
        provider_requests_per_minute: 5,
      },
    })
    expect(execution.ok(), await execution.text()).toBeTruthy()
    const assignmentsResponse = await request.get(`${apiBase}/api/settings/agents`)
    const assignments = (await assignmentsResponse.json()).map((assignment: any) => ({
      ...assignment,
      provider: 'gemini',
      model,
      enabled: true,
      use_mock_in_hybrid: false,
    }))
    expect((await request.put(`${apiBase}/api/settings/agents`, {
      data: assignments,
    })).ok()).toBeTruthy()

    const audit = await request.post(`${apiBase}/api/projects/${projectId}/story-audit`, {
      data: { include_agent: true },
      timeout: 600000,
    })
    expect(audit.ok(), await audit.text()).toBeTruthy()
    const report = await audit.json()
    expect(report.generated_by).toContain('StoryAuditorAgent')
    expect(report.generation_metadata.orchestration_plan_id).toBeTruthy()
  })
})
