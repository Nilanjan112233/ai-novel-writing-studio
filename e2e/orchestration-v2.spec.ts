import { APIRequestContext, expect, test } from '@playwright/test'
import fs from 'fs'


function apiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  if (fs.existsSync('.novelforge-ports.json')) {
    const ports = JSON.parse(fs.readFileSync('.novelforge-ports.json', 'utf-8'))
    return `http://127.0.0.1:${ports.backendPort || 8000}`
  }
  return 'http://127.0.0.1:8000'
}

async function waitForBackend(
  request: APIRequestContext,
  apiBase: string,
  timeoutMs = 120000,
) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await request.get(`${apiBase}/health`)
      if (response.ok()) return
    } catch {
      // The frontend can become ready before the backend migration completes.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Backend did not become ready')
}

async function waitForLatestRun(
  request: APIRequestContext,
  apiBase: string,
  projectId: string,
  timeoutMs = 600000,
) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const response = await request.get(`${apiBase}/api/projects/${projectId}/runs`)
    expect(response.ok()).toBeTruthy()
    const runs = await response.json()
    if (runs[0] && ['completed', 'waiting_for_user', 'failed'].includes(runs[0].status)) {
      expect(runs[0].status).not.toBe('failed')
      return runs[0]
    }
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
  throw new Error('Orchestration run did not reach a terminal state')
}

async function runCycle(
  request: APIRequestContext,
  apiBase: string,
  projectId: string,
) {
  const response = await request.post(`${apiBase}/api/projects/${projectId}/cycle`)
  expect(response.ok()).toBeTruthy()
  await waitForLatestRun(request, apiBase, projectId)
  const planResponse = await request.get(
    `${apiBase}/api/projects/${projectId}/orchestration/latest`,
  )
  expect(planResponse.ok()).toBeTruthy()
  return planResponse.json()
}

test.describe('Phase 1A production orchestrator', () => {
  test.setTimeout(900000)

  test('runs the Ashes of Valeria demand-driven production simulation', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const settingsResponse = await request.get(`${apiBase}/api/settings/ai`)
    expect(settingsResponse.ok()).toBeTruthy()
    const providerSettings = await settingsResponse.json()
    const gemini = providerSettings.providers?.gemini
    test.skip(!gemini?.configured, 'Gemini is not configured in NovelForge settings')
    const model = gemini.model || 'gemini-3.1-flash-lite'

    expect((await request.put(`${apiBase}/api/settings/execution`, {
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
    })).ok()).toBeTruthy()

    const assignmentsResponse = await request.get(`${apiBase}/api/settings/agents`)
    expect(assignmentsResponse.ok()).toBeTruthy()
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

    const projectResponse = await request.post(`${apiBase}/api/projects`, {
      data: {
        title: `The Ashes of Valeria ${Date.now()}`,
        premise: 'A dispossessed heir tends sacred ash that preserves the memories of a fallen empire.',
        idea_dump: 'Valeria must choose whether inherited memory should restore the empire or free its survivors.',
        genre: 'Fantasy',
        tone: 'Mythic and intimate',
        themes: ['Memory', 'Mercy', 'Power'],
      },
    })
    expect(projectResponse.ok()).toBeTruthy()
    const project = await projectResponse.json()
    const projectId = project.id

    const premisePlan = await runCycle(request, apiBase, projectId)
    expect(premisePlan.selected_agents.length).toBeLessThan(12)
    expect(premisePlan.selected_agents.length).toBeGreaterThan(0)

    expect((await request.put(`${apiBase}/api/projects/${projectId}`, {
      data: {
        character_notes: 'Valeria is proud, grief-stricken, and terrified that mercy will be mistaken for weakness.',
      },
    })).ok()).toBeTruthy()
    const characterPlan = await runCycle(request, apiBase, projectId)
    expect(characterPlan.selected_agents).toContain('CharacterJourneyAgent')
    expect(characterPlan.selected_agents).toContain('RelationshipAgent')
    expect(characterPlan.skipped_agents).toContain('PowerSystemAgent')
    expect(characterPlan.skipped_agents).toContain('WorldAgent')
    expect(characterPlan.skipped_agents).toContain('FactionAgent')

    const worldNotes = 'Ash gardens preserve public memory, and rival courts control who may enter them.'
    expect((await request.put(`${apiBase}/api/projects/${projectId}`, {
      data: { world_notes: worldNotes },
    })).ok()).toBeTruthy()
    const worldPlan = await runCycle(request, apiBase, projectId)
    expect(worldPlan.selected_agents).toContain('WorldAgent')
    expect(worldPlan.selected_agents).toContain('FactionAgent')
    expect(worldPlan.skipped_agents).toContain('CharacterJourneyAgent')

    expect((await request.put(`${apiBase}/api/projects/${projectId}`, {
      data: { world_notes: worldNotes },
    })).ok()).toBeTruthy()
    const noOpPlan = await runCycle(request, apiBase, projectId)
    expect(noOpPlan.selected_agents).toEqual([])
    expect(noOpPlan.actual_agent_calls).toBe(0)
    expect(noOpPlan.stop_reason).toContain('NO_CHANGE_TERMINATION')

    const historyResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/orchestration/history`,
    )
    expect(historyResponse.ok()).toBeTruthy()
    const history = await historyResponse.json()
    const plans = history.slice(0, 4)
    const totalCalls = plans.reduce(
      (sum: number, plan: any) => sum + Number(plan.actual_agent_calls || 0),
      0,
    )
    const averageAgentsPerCycle = totalCalls / plans.length
    const skipped = plans.reduce(
      (sum: number, plan: any) => sum + (plan.skipped_agents || []).length,
      0,
    )
    const planningAgentCount = plans[0]?.tasks?.length || 14
    const skipPercentage = skipped / (plans.length * planningAgentCount) * 100
    const staticBaseline = plans.length * planningAgentCount
    const reductionPercentage = (staticBaseline - totalCalls) / staticBaseline * 100
    const budgetUsage = plans.reduce(
      (sum: number, plan: any) => sum + Number(plan.actual_cost_usd || 0),
      0,
    )
    expect(averageAgentsPerCycle).toBeLessThan(5)
    expect(reductionPercentage).toBeGreaterThanOrEqual(50)
    expect(skipPercentage).toBeGreaterThanOrEqual(50)
    for (const plan of plans) {
      expect(Number(plan.actual_cost_usd || 0)).toBeLessThanOrEqual(
        Number(plan.limits.max_cycle_cost_usd),
      )
      expect(plan.tasks).toHaveLength(planningAgentCount)
      expect(plan.tasks.every((task: any) => task.reason)).toBeTruthy()
    }

    const tracesResponse = await request.get(
      `${apiBase}/api/settings/execution-traces?limit=200`,
    )
    expect(tracesResponse.ok()).toBeTruthy()
    const projectTraces = (await tracesResponse.json()).filter(
      (trace: any) => trace.project_id === projectId,
    )
    expect(projectTraces.length).toBe(totalCalls)
    expect(projectTraces.every(
      (trace: any) => Number(trace.metadata?.rate_limit_per_minute) === 5,
    )).toBeTruthy()

    await page.goto(`/project/${projectId}`)
    await expect(page.getByTestId('run-status')).not.toContainText('running')
    await page.getByTestId('section-workflow').click()
    await page.getByTestId('workflow-panel').getByRole('button', { name: 'Developer Mode' }).click()
    await expect(page.getByTestId('orchestration-inspector')).toBeVisible()
    await expect(page.getByTestId('orchestration-stop-reason')).toContainText(
      'NO_CHANGE_TERMINATION',
    )
    const screenshotPath = testInfo.outputPath('orchestration-inspector.png')
    await page.screenshot({ path: screenshotPath, fullPage: true })

    const metrics = {
      project_id: projectId,
      total_cycles: plans.length,
      total_agent_calls: totalCalls,
      average_agents_per_cycle: averageAgentsPerCycle,
      skip_percentage: skipPercentage,
      reduction_percentage: reductionPercentage,
      budget_usage_usd: budgetUsage,
      rate_limit_per_minute: 5,
      provider_trace_count: projectTraces.length,
      selected_agents_by_cycle: plans
        .slice()
        .reverse()
        .map((plan: any) => plan.selected_agents),
    }
    await testInfo.attach('phase-1a-metrics', {
      body: JSON.stringify(metrics, null, 2),
      contentType: 'application/json',
    })
  })
})
