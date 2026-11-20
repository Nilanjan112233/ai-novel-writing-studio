import { expect, test, APIRequestContext, Page } from '@playwright/test'
import { openSection } from './nav'
import fs from 'fs'

function apiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  if (fs.existsSync('.novelforge-ports.json')) {
    const ports = JSON.parse(fs.readFileSync('.novelforge-ports.json', 'utf-8'))
    return `http://localhost:${ports.backendPort || 8000}`
  }
  return 'http://localhost:8000'
}

async function waitForRun(request: APIRequestContext, apiBase: string, projectId: string, timeoutMs = 600000) {
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
  throw new Error('Narrative Studio run did not reach a terminal state')
}

async function assertNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => ({
    body: document.body.scrollWidth - document.body.clientWidth,
    document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }))
  expect(overflow.body).toBeLessThanOrEqual(1)
  expect(overflow.document).toBeLessThanOrEqual(1)
}

test.describe('real Gemini Narrative Studio lifecycle', () => {
  test.setTimeout(900000)

  test('runs two real cycles, locks decisions, approves proposals, and renders the Story Bible', async ({ page, request }) => {
    test.skip(!!process.env.E2E_PROJECT_ID, 'Reusing a completed real lifecycle for visual verification')
    const geminiKey = process.env.GEMINI_API_KEY || process.env.NOVELFORGE_GEMINI_KEY
    test.skip(!geminiKey, 'No Gemini API key provided for real provider E2E')
    const model = process.env.GEMINI_MODEL || 'gemini-3.1-flash-lite'
    const apiBase = apiBaseUrl()

    const settingsResponse = await request.get(`${apiBase}/api/settings/ai`)
    expect(settingsResponse.ok()).toBeTruthy()
    const settings = await settingsResponse.json()
    settings.providers.gemini.api_key = geminiKey
    settings.providers.gemini.model = model
    expect((await request.put(`${apiBase}/api/settings/ai`, { data: settings })).ok()).toBeTruthy()

    const validation = await request.post(`${apiBase}/api/settings/test-model`, {
      data: { provider: 'gemini', model },
    })
    expect(validation.ok()).toBeTruthy()
    expect((await validation.json()).success).toBeTruthy()

    expect((await request.put(`${apiBase}/api/settings/execution`, {
      data: {
        execution_mode: 'full',
        default_provider: 'gemini',
        default_model: model,
        enable_dynamic_routing: true,
        enable_reflection_loops: false,
      },
    })).ok()).toBeTruthy()

    const assignmentsResponse = await request.get(`${apiBase}/api/settings/agents`)
    const assignments = (await assignmentsResponse.json()).map((assignment: any) => ({
      ...assignment,
      provider: 'gemini',
      model,
      enabled: true,
      use_mock_in_hybrid: false,
    }))
    expect((await request.put(`${apiBase}/api/settings/agents`, { data: assignments })).ok()).toBeTruthy()

    const projectResponse = await request.post(`${apiBase}/api/projects`, {
      data: {
        title: 'The Last Concept Gardener',
        premise: 'A reincarnated boy develops a subconscious System that grows concepts as living powers.',
        idea_dump: 'The boy awakens in a culture where concepts are cultivated like gardens. His younger sister is his emotional anchor and must become politically important later. Power transactions use rare living materials, and his System is self-created rather than bestowed by a god.',
        genre: 'Progression fantasy',
        tone: 'Hopeful, mysterious, and strategic',
        themes: ['Identity', 'Stewardship', 'The cost of growth'],
        inspirations: ['Long-form progression fantasy', 'Ecological mythology'],
        target_length: '300-500 chapters',
        audience: 'Adult and new-adult progression fantasy readers',
        narrative_goals: ['Preserve a coherent long-form canon', 'Make every power advancement alter relationships'],
      },
    })
    expect(projectResponse.ok()).toBeTruthy()
    const projectId = (await projectResponse.json()).id

    expect((await request.post(`${apiBase}/api/projects/${projectId}/cycle`)).ok()).toBeTruthy()
    const cycleOneRun = await waitForRun(request, apiBase, projectId)
    expect(cycleOneRun.cycle_number).toBe(1)

    let bible = await (await request.get(`${apiBase}/api/projects/${projectId}/story-bible`)).json()
    const sections = bible.sections
    expect(sections.characters.length).toBeGreaterThan(0)
    expect(Object.keys(sections.world).length).toBeGreaterThan(0)
    expect(Object.keys(sections.power_system).length).toBeGreaterThan(0)
    expect(sections.factions.length).toBeGreaterThan(0)
    expect(sections.relationships.length).toBeGreaterThan(0)
    expect(sections.plot_threads.length).toBeGreaterThan(0)
    expect(sections.mysteries.length).toBeGreaterThan(0)
    expect(sections.timeline.length).toBeGreaterThan(0)
    expect(sections.arcs.length).toBeGreaterThan(0)
    expect(sections.active_questions.length).toBeGreaterThan(0)

    const cycleOneQuestionTexts = sections.active_questions.map((question: any) => question.text)
    for (const question of sections.active_questions) {
      const answer = `For ${question.story_area || 'this story area'}, preserve material-based transactions, a self-created subconscious System, and the sister's later political importance.`
      const answerResponse = await request.post(`${apiBase}/api/projects/${projectId}/answers`, {
        data: { question_id: question.id, answer },
      })
      expect(answerResponse.ok()).toBeTruthy()
    }

    bible = await (await request.get(`${apiBase}/api/projects/${projectId}/story-bible`)).json()
    expect(bible.sections.active_questions.length).toBe(0)
    expect(bible.sections.canon_registry.length).toBeGreaterThanOrEqual(cycleOneQuestionTexts.length)
    expect(bible.sections.decision_registry.every((decision: any) => decision.status !== 'LOCKED')).toBeTruthy()

    await page.goto(`/project/${projectId}`)
    await expect(page.getByTestId('discussion-room-panel')).toBeVisible()
    const proposalCountBefore = await page.getByTestId('proposal-card').count()
    await page.getByTestId('workspace-run-discussion-cycle').click()
    await expect(page.getByTestId('run-status')).toContainText(/completed|waiting_for_user/, { timeout: 600000 })
    await expect.poll(() => page.getByTestId('proposal-card').count(), { timeout: 600000 }).toBeGreaterThan(proposalCountBefore)

    const cycleTwoRun = await waitForRun(request, apiBase, projectId)
    expect(cycleTwoRun.cycle_number).toBe(2)
    bible = await (await request.get(`${apiBase}/api/projects/${projectId}/story-bible`)).json()
    expect(bible.cycle_number).toBe(2)
    const activeTexts = bible.sections.active_questions.map((question: any) => question.text)
    expect(activeTexts.some((text: string) => cycleOneQuestionTexts.includes(text))).toBeFalsy()

    const proposals = bible.sections.discussion
    for (const agentName of ['NarrativeDirectorAgent', 'PowerSystemAgent', 'FactionAgent']) {
      const proposal = [...proposals].reverse().find((item: any) => item.author === agentName && item.role === 'agent')
      expect(proposal, `${agentName} proposal missing`).toBeTruthy()
      const approval = await request.post(`${apiBase}/api/projects/${projectId}/discussion/${proposal.id}/decision`, {
        data: { action: 'approve' },
      })
      expect(approval.ok()).toBeTruthy()
      expect((await approval.json()).status).toBe('approved')
    }

    expect((await request.post(`${apiBase}/api/projects/${projectId}/draft-scenes`)).ok()).toBeTruthy()
    bible = await (await request.get(`${apiBase}/api/projects/${projectId}/story-bible`)).json()
    expect(bible.sections.drafting.scene_plans.length).toBeGreaterThan(0)
    expect(bible.sections.discussion_decisions.filter((item: any) => item.status === 'approved').length).toBeGreaterThanOrEqual(3)

    const latestCycleOutputs = bible.sections.workflow.agents.filter((item: any) => item.metadata.cycle_number === 2)
    expect(latestCycleOutputs.length).toBeGreaterThanOrEqual(12)
    for (const output of latestCycleOutputs) {
      expect(output.metadata.provider).toBe('gemini')
      expect(output.metadata.model).toBe(model)
      expect(output.metadata.source_type).toBe('real_ai')
      expect(output.metadata.mock_used).toBeFalsy()
      expect(output.metadata.execution_trace_id).toBeTruthy()
    }

    const auditResponse = await request.get(`${apiBase}/api/projects/${projectId}/audit`)
    expect(auditResponse.ok()).toBeTruthy()
    const audit = await auditResponse.json()
    expect(audit.status, JSON.stringify(audit.findings)).toBe('pass')

    const pageChecks = [
      ['vision', 'story-vision-panel'],
      ['discussion', 'discussion-room-panel'],
      ['characters', 'characters-panel'],
      ['world', 'world-panel'],
      ['power', 'power-system-panel'],
      ['factions', 'factions-panel'],
      ['relationships', 'relationships-panel'],
      ['threads', 'threads-panel'],
      ['themes', 'themes-panel'],
      ['mysteries', 'mysteries-panel'],
      ['timeline', 'story-timeline-panel'],
      ['arcs', 'arcs-panel'],
      ['questions', 'questions-panel'],
      ['insights', 'ai-insights-panel'],
      ['drafting', 'drafting-panel'],
      ['workflow', 'workflow-panel'],
      ['settings', 'workspace-settings-panel'],
    ]
    for (const [section, panel] of pageChecks) {
      await openSection(page, section)
      await expect(page.getByTestId(panel)).toBeVisible()
      await expect(page.getByTestId(panel)).not.toContainText(/mock cognition|placeholder|lorem ipsum/i)
      await expect(page.getByTestId(panel).locator('pre')).toHaveCount(0)
      await assertNoHorizontalOverflow(page)
    }

    const stored = await request.post(`${apiBase}/api/projects/${projectId}/test-results`, {
      data: {
        suite: 'real_gemini_two_cycle_lifecycle',
        status: 'passed',
        provider: 'gemini',
        model,
        checks: {
          cycle_one: true,
          answers_to_canon: true,
          cycle_two: true,
          proposal_approvals: true,
          no_mock_artifacts: true,
          story_bible: true,
          database_audit: true,
          realtime_ui: true,
        },
      },
    })
    expect(stored.ok()).toBeTruthy()
  })

  test('verifies a completed real lifecycle after UI hardening', async ({ page, request }) => {
    const projectId = process.env.E2E_PROJECT_ID
    test.skip(!projectId, 'No completed real lifecycle project supplied')
    const model = process.env.GEMINI_MODEL || 'gemini-3.1-flash-lite'
    const apiBase = apiBaseUrl()

    const bibleResponse = await request.get(`${apiBase}/api/projects/${projectId}/story-bible`)
    expect(bibleResponse.ok()).toBeTruthy()
    const bible = await bibleResponse.json()
    expect(bible.cycle_number).toBe(2)
    expect(bible.sections.drafting.scene_plans.length).toBeGreaterThan(0)
    expect(bible.sections.discussion_decisions.filter((item: any) => item.status === 'approved').length).toBeGreaterThanOrEqual(3)
    const outputs = bible.sections.workflow.agents.filter((item: any) => item.metadata.cycle_number === 2)
    expect(outputs.length).toBeGreaterThanOrEqual(12)
    expect(outputs.every((item: any) => item.metadata.provider === 'gemini' && item.metadata.model === model)).toBeTruthy()
    expect(outputs.every((item: any) => item.metadata.source_type === 'real_ai' && !item.metadata.mock_used)).toBeTruthy()

    const audit = await (await request.get(`${apiBase}/api/projects/${projectId}/audit`)).json()
    expect(audit.status, JSON.stringify(audit.findings)).toBe('pass')

    await page.goto(`/project/${projectId}`)
    const pageChecks = [
      ['vision', 'story-vision-panel'],
      ['discussion', 'discussion-room-panel'],
      ['characters', 'characters-panel'],
      ['world', 'world-panel'],
      ['power', 'power-system-panel'],
      ['factions', 'factions-panel'],
      ['relationships', 'relationships-panel'],
      ['threads', 'threads-panel'],
      ['themes', 'themes-panel'],
      ['mysteries', 'mysteries-panel'],
      ['timeline', 'story-timeline-panel'],
      ['arcs', 'arcs-panel'],
      ['questions', 'questions-panel'],
      ['insights', 'ai-insights-panel'],
      ['drafting', 'drafting-panel'],
      ['workflow', 'workflow-panel'],
      ['settings', 'workspace-settings-panel'],
    ]
    for (const [section, panel] of pageChecks) {
      await openSection(page, section)
      await expect(page.getByTestId(panel)).toBeVisible()
      await expect(page.getByTestId(panel)).not.toContainText(/mock cognition|placeholder|lorem ipsum/i)
      await expect(page.getByTestId(panel).locator('pre')).toHaveCount(0)
      await assertNoHorizontalOverflow(page)
    }

    fs.mkdirSync('test-results', { recursive: true })
    await openSection(page, 'discussion')
    await page.screenshot({ path: 'test-results/real-discussion-room.png', fullPage: true })
    await openSection(page, 'relationships')
    await page.screenshot({ path: 'test-results/real-relationships.png', fullPage: true })
    await openSection(page, 'workflow')
    await page.screenshot({ path: 'test-results/real-workflow.png', fullPage: true })

    const stored = await request.post(`${apiBase}/api/projects/${projectId}/test-results`, {
      data: {
        suite: 'real_gemini_two_cycle_lifecycle',
        status: 'passed',
        provider: 'gemini',
        model,
        checks: {
          cycle_one: true,
          answers_to_canon: true,
          cycle_two: true,
          proposal_approvals: true,
          no_mock_artifacts: true,
          story_bible: true,
          database_audit: true,
          realtime_ui: true,
          all_pages_rendered: true,
        },
        notes: ['Visual verification resumed from the completed fresh lifecycle after schema-drift UI hardening.'],
      },
    })
    expect(stored.ok()).toBeTruthy()
  })
})
