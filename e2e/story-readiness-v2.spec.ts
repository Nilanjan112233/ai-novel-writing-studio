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


async function waitForBackend(request: APIRequestContext, apiBase: string) {
  const started = Date.now()
  while (Date.now() - started < 120000) {
    try {
      if ((await request.get(`${apiBase}/health`)).ok()) return
    } catch {
      // Frontend readiness may precede backend migrations.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Backend did not become ready')
}


async function runCycle(
  request: APIRequestContext,
  apiBase: string,
  projectId: string,
) {
  const start = await request.post(`${apiBase}/api/projects/${projectId}/cycle`)
  expect(start.ok()).toBeTruthy()
  const runId = (await start.json()).id
  const started = Date.now()
  while (Date.now() - started < 600000) {
    const response = await request.get(
      `${apiBase}/api/projects/${projectId}/runs/${runId}`,
    )
    expect(response.ok()).toBeTruthy()
    const run = await response.json()
    if (['completed', 'waiting_for_user', 'failed'].includes(run.status)) {
      expect(run.status).not.toBe('failed')
      const plan = await request.get(
        `${apiBase}/api/projects/${projectId}/orchestration/latest`,
      )
      expect(plan.ok()).toBeTruthy()
      return plan.json()
    }
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
  throw new Error('Planning cycle did not finish')
}


async function postJson(
  request: APIRequestContext,
  url: string,
  data: Record<string, unknown>,
) {
  const response = await request.post(url, { data })
  expect(response.ok()).toBeTruthy()
  return response.json()
}


test.describe('Phase 1B story readiness foundation', () => {
  test.setTimeout(900000)

  test('supports gradual Chronicles of Elysium planning with real Gemini', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const providerResponse = await request.get(`${apiBase}/api/settings/ai`)
    expect(providerResponse.ok()).toBeTruthy()
    const providerSettings = await providerResponse.json()
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

    const project = await postJson(
      request,
      `${apiBase}/api/projects`,
      {
        title: `The Chronicles of Elysium ${Date.now()}`,
        premise: 'Elara maps memories across a world waking from divine sleep.',
        idea_dump: 'The Elysian Compass reveals only the truths each arc can bear.',
        genre: 'Fantasy',
        tone: 'Mythic and intimate',
        themes: ['Memory', 'Responsibility', 'Mercy'],
      },
    )
    const projectId = project.id
    const initialPlan = await runCycle(request, apiBase, projectId)
    expect(initialPlan.selected_agents.length).toBeLessThan(initialPlan.tasks.length)

    const arc1 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 1: The Waking Map',
      purpose: 'Establish Elara, the compass, and the first memory road.',
      goal: 'Restore the first road without surrendering its memories to the court.',
      conflict: 'Elara must trust Soren while the court demands control.',
      stakes: 'The city loses its shared past if the road collapses.',
      approval_status: 'approved',
      chapter_range: [1, 10],
      order: 1,
    })
    const arc2 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 2: The Divided Archive',
      purpose: 'Investigate who benefits from fractured memory.',
      goal: 'Reach the sealed archive.',
      conflict: 'The route and antagonist remain under discussion.',
      stakes: 'Probable regional memory loss.',
      approval_status: 'discussed',
      chapter_range: [11, 20],
      order: 2,
    })
    const arc3 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 3: Beyond the Veil',
      purpose: 'Reserve future discovery without forcing detail.',
      goal: '',
      conflict: '',
      stakes: '',
      approval_status: 'draft',
      chapter_range: [21, null],
      order: 3,
    })

    for (const title of ['Protagonist', 'Arc Goal', 'Major Conflict']) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
        arc_id: arc1.arc_id,
        category: 'Arc Foundation',
        title,
        description: `${title} is approved for Arc 1.`,
        priority: 'required',
        status: 'approved',
        evidence: [`Approved Arc 1 ${title}`],
        blocking: true,
      })
    }
    await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
      arc_id: arc2.arc_id,
      category: 'Arc Foundation',
      title: 'Protagonist',
      description: 'Elara remains the protagonist.',
      priority: 'required',
      status: 'approved',
      evidence: ['Arc 1 continuity'],
      blocking: true,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
      arc_id: arc2.arc_id,
      category: 'Arc Foundation',
      title: 'Major Conflict',
      description: 'The Arc 2 opposition remains open.',
      priority: 'required',
      status: 'missing',
      evidence: [],
      blocking: true,
    })

    const readinessPlan = await runCycle(request, apiBase, projectId)
    expect(readinessPlan.selected_agents).toContain('ReadinessAgent')
    expect(readinessPlan.selected_agents.length).toBeLessThan(readinessPlan.tasks.length)

    const timelineEntries = []
    for (const entry of [
      { arc_id: arc1.arc_id, title: 'Elara finds the Waking Map', summary: 'Beginning event.', certainty: 'known', order: 1 },
      { arc_id: arc1.arc_id, title: 'The court claims the compass', summary: 'Major turning point.', certainty: 'known', order: 2 },
      { arc_id: arc1.arc_id, title: 'Elara restores the first road', summary: 'Arc climax.', certainty: 'known', order: 3 },
      { arc_id: arc2.arc_id, title: 'The archive summons Elara', summary: 'Beginning event.', certainty: 'known', order: 11 },
      { arc_id: arc2.arc_id, title: 'Unknown Arc 2 reversal', summary: '', certainty: 'unknown', order: 12 },
      { arc_id: arc2.arc_id, title: 'Unknown Arc 2 climax', summary: '', certainty: 'unknown', order: 13 },
      { arc_id: arc3.arc_id, title: 'Arc 3 placeholder', summary: '', certainty: 'unknown', order: 21 },
    ]) {
      timelineEntries.push(await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/timeline-v2`,
        {
          ...entry,
          importance: 'major',
          status: 'planned',
          dependencies: [],
          chapter_range: [],
        },
      ))
    }

    await postJson(request, `${apiBase}/api/projects/${projectId}/character-progressions`, {
      arc_id: arc1.arc_id,
      character: 'Elara',
      current_state: 'Protects memory through secrecy',
      desired_state: 'Shares truth with accountable allies',
      skills: ['Memory cartography'],
      powers: ['Echo sight'],
      beliefs: ['Truth is dangerous'],
      relationships: [{ character: 'Soren', state: 'guarded trust' }],
      maturity: 'Learns to delegate',
      trauma: ['The Archive fire'],
      goals: ['Restore the Waking Map'],
    })

    const truth = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
      arc_id: arc1.arc_id,
      title: 'The compass contains a sleeping name',
      content: 'The Elysian Compass contains the forgotten god Elys.',
      knowledge_type: 'WORLD_TRUTH',
      known_by: [],
      not_known_by: ['Elara', 'Soren'],
      learned_how: 'World truth',
      is_false: false,
      confidence: 1,
      source: 'canon',
      reveal_target: 'Arc 2',
    })
    const readerClue = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
      arc_id: arc1.arc_id,
      title: 'The compass glows near the old name',
      content: 'Readers see the compass glow while Elara looks away.',
      knowledge_type: 'READER_KNOWLEDGE',
      known_by: ['Reader'],
      not_known_by: ['Elara', 'Soren'],
      learned_how: 'Visual clue',
      is_false: false,
      confidence: 0.75,
      source: 'foreshadow',
      reveal_target: 'Arc 2',
      world_truth_entry_id: truth.entry_id,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
      arc_id: arc1.arc_id,
      title: 'Elara believes the compass is only a map',
      content: 'Elara believes the compass has no will of its own.',
      knowledge_type: 'CHARACTER_KNOWLEDGE',
      known_by: ['Elara'],
      not_known_by: ['Soren'],
      learned_how: 'Prior training',
      is_false: true,
      confidence: 0.9,
      source: 'character belief',
      reveal_target: 'Arc 2',
      world_truth_entry_id: truth.entry_id,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadowing-v2`, {
      seed: 'The compass glows and the characters ignore it.',
      chapter_planted: 3,
      arc_planted: arc1.arc_id,
      payoff_target: 'Elara learns the sleeping name.',
      payoff_arc_id: arc2.arc_id,
      status: 'seeded',
      timeline_entry_ids: [timelineEntries[1].entry_id],
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/artifacts`, {
      item: 'The Elysian Compass',
      owner: 'Elara',
      power: 'Finds memories with living witnesses',
      hidden_power: 'Houses the name of Elys',
      cost: 'Erases one private memory per use',
      limitations: ['Cannot reveal a memory without a witness'],
      history: 'Recovered from the Archive fire',
      future_relevance: 'Unlocks the Arc 3 threshold',
      status: 'active',
      arc_ids: [arc1.arc_id, arc2.arc_id, arc3.arc_id],
      character_ids: ['Elara'],
      timeline_entry_ids: [timelineEntries[0].entry_id],
      knowledge_entry_ids: [truth.entry_id, readerClue.entry_id],
    })

    const knowledgePlan = await runCycle(request, apiBase, projectId)
    expect(knowledgePlan.selected_agents).toContain('KnowledgeAgent')
    expect(knowledgePlan.selected_agents.length).toBeLessThan(knowledgePlan.tasks.length)

    const arc1Readiness = await request.get(
      `${apiBase}/api/projects/${projectId}/readiness/report`,
      { params: { arc_id: arc1.arc_id } },
    )
    const arc2Readiness = await request.get(
      `${apiBase}/api/projects/${projectId}/readiness/report`,
      { params: { arc_id: arc2.arc_id } },
    )
    const arc3Readiness = await request.get(
      `${apiBase}/api/projects/${projectId}/readiness/report`,
      { params: { arc_id: arc3.arc_id } },
    )
    const arc1Report = await arc1Readiness.json()
    const arc2Report = await arc2Readiness.json()
    const arc3Report = await arc3Readiness.json()
    expect(arc1Report.status).toBe('READY')
    expect(arc1Report.drafting_eligible).toBeTruthy()
    expect(arc2Report.status).toBe('PARTIALLY_READY')
    expect(arc3Report.status).toBe('NOT_READY')

    const memoryResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/agent-memories`,
      { params: { agent_name: 'KnowledgeAgent' } },
    )
    expect(memoryResponse.ok()).toBeTruthy()
    const memory = await memoryResponse.json()
    expect(memory.recent.length).toBeGreaterThan(0)
    expect(memory.recent.length).toBeLessThanOrEqual(12)

    await page.goto(`/project/${projectId}`)
    await page.getByTestId('section-readiness').click()
    await expect(page.getByTestId('readiness-dashboard')).toContainText('READY')
    await page.getByTestId('section-arcs').click()
    await expect(page.getByTestId('arc-board')).toContainText('Draftable')
    await page.getByTestId('section-knowledge').click()
    await expect(page.getByTestId('knowledge-view')).toContainText('Reader Knowledge')
    await expect(page.getByTestId('knowledge-view')).toContainText('Elara')
    await page.getByTestId('section-timeline').click()
    await expect(page.getByTestId('timeline-v2')).toContainText('Unknown Arc 2 reversal')
    await expect(page.getByTestId('timeline-v2')).toContainText('Details intentionally unresolved')
    await page.screenshot({
      path: testInfo.outputPath('chronicles-of-elysium-planning-foundation.png'),
      fullPage: true,
    })

    await testInfo.attach('phase-1b-results', {
      body: JSON.stringify({
        project_id: projectId,
        model,
        arc_1: 'READY',
        arc_1_drafting_eligible: true,
        arc_2: 'PARTIALLY_READY',
        arc_3: 'NOT_READY',
        unknown_timeline_entries: timelineEntries.filter((entry) => entry.certainty === 'unknown').length,
        readiness_agents: readinessPlan.selected_agents,
        knowledge_agents: knowledgePlan.selected_agents,
        knowledge_memory_recent: memory.recent.length,
      }, null, 2),
      contentType: 'application/json',
    })
  })
})
