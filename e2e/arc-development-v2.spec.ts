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
      // The frontend may become ready before backend migrations finish.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Backend did not become ready')
}


async function postJson(
  request: APIRequestContext,
  url: string,
  data: Record<string, unknown> = {},
) {
  const response = await request.post(url, { data })
  expect(response.ok(), await response.text()).toBeTruthy()
  return response.json()
}


async function runCycle(
  request: APIRequestContext,
  apiBase: string,
  projectId: string,
) {
  const response = await request.post(`${apiBase}/api/projects/${projectId}/cycle`)
  expect(response.ok(), await response.text()).toBeTruthy()
  const runId = (await response.json()).id
  const started = Date.now()
  while (Date.now() - started < 600000) {
    const runResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/runs/${runId}`,
    )
    expect(runResponse.ok()).toBeTruthy()
    const run = await runResponse.json()
    if (['completed', 'waiting_for_user', 'failed'].includes(run.status)) {
      expect(run.status).not.toBe('failed')
      const planResponse = await request.get(
        `${apiBase}/api/projects/${projectId}/orchestration/latest`,
      )
      expect(planResponse.ok()).toBeTruthy()
      return planResponse.json()
    }
    await new Promise((resolve) => setTimeout(resolve, 1500))
  }
  throw new Error('Arc development cycle did not finish')
}


test.describe('Phase 2A arc-centric story development', () => {
  test.setTimeout(1200000)

  test('develops The Last Kingdom of Aether without generating prose', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const providerResponse = await request.get(`${apiBase}/api/settings/ai`)
    expect(providerResponse.ok()).toBeTruthy()
    const providers = await providerResponse.json()
    const gemini = providers.providers?.gemini
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
    const assignmentResponse = await request.get(`${apiBase}/api/settings/agents`)
    expect(assignmentResponse.ok()).toBeTruthy()
    const assignments = (await assignmentResponse.json()).map((assignment: any) => ({
      ...assignment,
      provider: 'gemini',
      model,
      enabled: true,
      use_mock_in_hybrid: false,
    }))
    expect((await request.put(`${apiBase}/api/settings/agents`, {
      data: assignments,
    })).ok()).toBeTruthy()

    const project = await postJson(request, `${apiBase}/api/projects`, {
      title: `The Last Kingdom of Aether ${Date.now()}`,
      premise: "Aether's last cartographer must restore a kingdom erased from shared memory.",
      idea_dump: 'The crown, maps, and inherited power reveal different truths by arc.',
      genre: 'Fantasy',
      tone: 'Mythic and intimate',
      themes: ['Memory', 'Stewardship', 'Power'],
    })
    const projectId = project.id
    const conceptPlan = await runCycle(request, apiBase, projectId)
    expect(conceptPlan.selected_agents.length).toBeGreaterThan(0)
    expect(conceptPlan.selected_agents.length).toBeLessThan(conceptPlan.tasks.length)

    const arc1 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 1: The Aether Crown',
      purpose: 'Restore the first lost road and establish shared stewardship.',
      goal: 'Restore one lost road.',
      conflict: 'The crown demands control of the map.',
      stakes: 'A province may vanish from collective memory.',
      resolution_direction: 'The road returns under shared stewardship.',
      approval_status: 'approved',
      development_status: 'approved',
      chapter_range: [1, 6],
      mysteries: ['Who erased the kingdom?'],
      order: 1,
    })
    const arc2 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 2: The Broken Meridian',
      purpose: 'Follow the restored road toward the divided archive.',
      goal: 'Reach the broken meridian.',
      conflict: 'The archive accepts only one version of the past.',
      stakes: 'The restored province may fracture into rival memories.',
      resolution_direction: 'The archive conflict remains open but bounded.',
      approval_status: 'discussed',
      development_status: 'development',
      chapter_range: [7, 12],
      mysteries: ['Which memory of Aether is true?'],
      order: 2,
    })
    const arc3 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 3: Beyond the Last Road',
      purpose: 'Reserve future discovery without forcing detail.',
      goal: '',
      conflict: '',
      stakes: '',
      resolution_direction: '',
      approval_status: 'draft',
      development_status: 'idea',
      chapter_range: [13, null],
      mysteries: [],
      order: 3,
    })

    const activation = await request.post(
      `${apiBase}/api/projects/${projectId}/arcs/${arc1.arc_id}/activate`,
    )
    expect(activation.ok(), await activation.text()).toBeTruthy()
    await postJson(request, `${apiBase}/api/projects/${projectId}/arc-dependencies`, {
      arc_id: arc2.arc_id,
      dependency_type: 'follows_arc',
      target_id: arc1.arc_id,
      required_state: 'completed',
      blocking: true,
    })

    for (const title of ['Protagonist', 'Arc Goal', 'Major Conflict']) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
        arc_id: arc1.arc_id,
        category: 'Arc Foundation',
        title,
        description: `${title} is approved for Arc 1.`,
        priority: 'required',
        status: 'approved',
        evidence: ['Author approved'],
        blocking: true,
      })
    }
    const checklistResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/arc-checklists`,
      { params: { arc_id: arc1.arc_id } },
    )
    expect(checklistResponse.ok()).toBeTruthy()
    const checklist = await checklistResponse.json()
    for (const item of checklist) {
      const update = await request.put(
        `${apiBase}/api/projects/${projectId}/arc-checklists/${item.item_id}`,
        { data: { status: 'approved', evidence: ['Author approved'] } },
      )
      expect(update.ok(), await update.text()).toBeTruthy()
    }

    const timelineEntries = []
    for (const [index, title] of [
      'The map wakes at the erased border',
      'The crown seizes the restored road',
      'Mara chooses shared stewardship',
    ].entries()) {
      timelineEntries.push(await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/timeline-v2`,
        {
          arc_id: arc1.arc_id,
          title,
          summary: title,
          importance: 'major',
          status: 'approved',
          certainty: 'known',
          dependencies: [],
          chapter_range: [index * 2 + 1, index * 2 + 2],
          order: index + 1,
        },
      ))
    }
    await postJson(request, `${apiBase}/api/projects/${projectId}/timeline-v2`, {
      arc_id: arc2.arc_id,
      title: 'The divided archive calls',
      summary: 'Arc 2 beginning anchor.',
      importance: 'major',
      status: 'planned',
      certainty: 'known',
      dependencies: [],
      chapter_range: [7, 8],
      order: 7,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/timeline-v2`, {
      arc_id: arc2.arc_id,
      title: 'Unknown Arc 2 reversal',
      summary: '',
      importance: 'major',
      status: 'planned',
      certainty: 'unknown',
      dependencies: [],
      chapter_range: [],
      order: 9,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/timeline-v2`, {
      arc_id: arc3.arc_id,
      title: 'Arc 3 placeholder',
      summary: '',
      importance: 'major',
      status: 'planned',
      certainty: 'unknown',
      dependencies: [],
      chapter_range: [],
      order: 13,
    })

    await postJson(request, `${apiBase}/api/projects/${projectId}/character-progressions`, {
      arc_id: arc1.arc_id,
      character: 'Mara',
      current_state: 'Guards the map alone',
      desired_state: 'Shares stewardship',
      arc_start_state: 'Guards the map alone',
      arc_midpoint_state: 'Trusts one witness',
      arc_end_state: 'Shares stewardship',
      emotional_growth: 'Fear becomes accountable trust',
      maturity_growth: 'Accepts limits',
      power_growth: ['Reads one restored road'],
      relationship_growth: ['Accepts Cael as a witness'],
      belief_changes: ['Control is not safety'],
      goal_changes: ['Restore the road for everyone'],
      skills: [],
      powers: [],
      beliefs: [],
      relationships: [],
      maturity: '',
      trauma: [],
      goals: [],
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/power-progressions`, {
      arc_id: arc1.arc_id,
      character: 'Mara',
      starting_power: 'Sees erased borders',
      ending_power: 'Restores one witnessed road',
      new_abilities: ['Witness-bound restoration'],
      mastered_abilities: [],
      limitations: ['Requires a living witness'],
      costs: ['Loses one private route'],
      future_evolution: 'Restore a network, not a kingdom',
    })

    const knowledge = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
      arc_id: arc1.arc_id,
      title: 'The crown erased Aether',
      content: 'The crown erased the kingdom to monopolize its roads.',
      knowledge_type: 'WORLD_TRUTH',
      known_by: [],
      not_known_by: ['Mara'],
      learned_how: 'Climax evidence',
      is_false: false,
      confidence: 1,
      source: 'canon',
      reveal_target: 'Arc 1 climax',
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge-evolutions`, {
      arc_id: arc1.arc_id,
      knowledge_entry_id: knowledge.entry_id,
      event_type: 'reveal',
      summary: 'Mara learns who erased Aether.',
      order: 3,
      evidence: ['Climax reveal'],
    })

    const foreshadow = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/foreshadowing-v2`,
      {
        arc_planted: arc1.arc_id,
        seed: "The crown's map has one deliberate blank.",
        payoff_target: 'The blank names Aether.',
        payoff_arc_id: arc1.arc_id,
        status: 'seeded',
        timeline_entry_ids: [timelineEntries[0].entry_id],
      },
    )
    for (const [index, eventType] of ['seed', 'development', 'reinforcement', 'payoff'].entries()) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadow-chains`, {
        arc_id: arc1.arc_id,
        foreshadow_id: foreshadow.entry_id,
        event_type: eventType,
        summary: `${eventType} the deliberate blank`,
        order: index + 1,
        evidence: [eventType],
      })
    }

    const artifact = await postJson(request, `${apiBase}/api/projects/${projectId}/artifacts`, {
      item: 'The Aether Crown',
      owner: 'Mara',
      power: 'Stores erased roads',
      hidden_power: 'Can return one road',
      cost: 'A private memory',
      limitations: ['Requires a witness'],
      history: 'Made before the erasure',
      future_relevance: 'Connects Arc 2',
      status: 'active',
      arc_ids: [arc1.arc_id],
      character_ids: ['Mara'],
      timeline_entry_ids: [timelineEntries[0].entry_id],
      knowledge_entry_ids: [knowledge.entry_id],
    })
    for (const [index, eventType] of ['discovery', 'usage', 'awakening'].entries()) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/artifact-evolutions`, {
        arc_id: arc1.arc_id,
        artifact_id: artifact.artifact_id,
        event_type: eventType,
        summary: `${eventType} of the Aether Crown`,
        from_state: index === 0 ? 'Hidden' : 'Dormant',
        to_state: eventType === 'awakening' ? 'Witness-bound' : 'Known',
        order: index + 1,
        evidence: [eventType],
      })
    }

    const chapterPlans = []
    for (const [index, title] of [
      'The Blank Road',
      'The Crown Takes the Map',
      'The Witnessed Kingdom',
    ].entries()) {
      const chapter = await postJson(request, `${apiBase}/api/projects/${projectId}/chapter-plans`, {
        arc_id: arc1.arc_id,
        chapter_number: index * 2 + 1,
        title,
        purpose: `Advance ${title}.`,
        conflict: 'Mara and the crown contest who may define the road.',
        character_focus: ['Mara'],
        knowledge_changes: [knowledge.entry_id],
        artifact_ids: [artifact.artifact_id],
        foreshadow_ids: [foreshadow.entry_id],
        timeline_entry_ids: [timelineEntries[index].entry_id],
        status: 'approved',
      })
      chapterPlans.push(chapter)
      await postJson(request, `${apiBase}/api/projects/${projectId}/scene-plans-v2`, {
        arc_id: arc1.arc_id,
        chapter_plan_id: chapter.chapter_plan_id,
        title: `${title} planning scene`,
        purpose: `Stage the turning point for ${title}.`,
        conflict: 'Mara cannot prove the road belongs to its witnesses.',
        outcome: 'The arc advances without resolving future arcs.',
        character_focus: ['Mara'],
        character_change: 'Isolation yields to accountable trust.',
        knowledge_changes: [knowledge.entry_id],
        foreshadow_links: [foreshadow.entry_id],
        artifact_interactions: [artifact.artifact_id],
        timeline_impacts: [timelineEntries[index].entry_id],
        status: 'approved',
        order: index + 1,
      })
    }

    const proseAttempt = await request.post(
      `${apiBase}/api/projects/${projectId}/chapter-plans`,
      {
        data: {
          arc_id: arc1.arc_id,
          chapter_number: 6,
          purpose: 'Contract guard',
          chapter_text: 'This prose must be rejected.',
        },
      },
    )
    expect(proseAttempt.status()).toBe(400)

    const developmentPlan = await runCycle(request, apiBase, projectId)
    expect(developmentPlan.selected_agents).toContain('StoryDevelopmentAgent')
    expect(developmentPlan.selected_agents.length).toBeLessThan(developmentPlan.tasks.length)

    const arc1Report = await (
      await request.get(`${apiBase}/api/projects/${projectId}/arcs/${arc1.arc_id}/development`)
    ).json()
    const arc2Report = await (
      await request.get(`${apiBase}/api/projects/${projectId}/arcs/${arc2.arc_id}/development`)
    ).json()
    const arc3Report = await (
      await request.get(`${apiBase}/api/projects/${projectId}/arcs/${arc3.arc_id}/development`)
    ).json()
    expect(arc1Report.maturity_score).toBeGreaterThan(85)
    expect(arc1Report.draftable).toBeTruthy()
    expect(arc1Report.development_status).toBe('draftable')
    expect(arc2Report.maturity_score).toBeGreaterThanOrEqual(30)
    expect(arc2Report.maturity_score).toBeLessThanOrEqual(70)
    expect(arc2Report.draftable).toBeFalsy()
    expect(arc3Report.maturity_score).toBeLessThan(30)
    expect(arc3Report.draftable).toBeFalsy()

    const arcsResponse = await request.get(`${apiBase}/api/projects/${projectId}/arcs`)
    const arcs = await arcsResponse.json()
    expect(arcs.filter((arc: any) => arc.focus_role === 'current')).toHaveLength(1)
    expect(arcs.filter((arc: any) => arc.drafting_eligible)).toHaveLength(1)

    expect((await request.put(`${apiBase}/api/projects/${projectId}`, {
      data: { world_notes: 'Aether floats above a storm sea divided by memory tides.' },
    })).ok()).toBeTruthy()
    const worldPlan = await runCycle(request, apiBase, projectId)
    expect(worldPlan.selected_agents).not.toContain('StoryDevelopmentAgent')
    expect(worldPlan.skipped_agents).toContain('StoryDevelopmentAgent')

    const storyRoomResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/story-room`,
    )
    expect(storyRoomResponse.ok()).toBeTruthy()
    const storyRoom = await storyRoomResponse.json()
    expect(storyRoom.current_arc.arc_id).toBe(arc1.arc_id)
    expect(storyRoom.agent_proposals.length).toBeGreaterThan(0)

    const tracesResponse = await request.get(
      `${apiBase}/api/settings/execution-traces?limit=300`,
    )
    expect(tracesResponse.ok()).toBeTruthy()
    const traces = (await tracesResponse.json()).filter(
      (trace: any) => trace.project_id === projectId,
    )
    expect(traces.some((trace: any) => trace.agent_name === 'StoryDevelopmentAgent')).toBeTruthy()
    expect(traces.every(
      (trace: any) => Number(trace.metadata?.rate_limit_per_minute) === 5,
    )).toBeTruthy()

    await page.goto(`/project/${projectId}`)
    await page.getByTestId('section-arc-development').click()
    await expect(page.getByTestId('arc-development-workspace')).toContainText('DRAFTABLE')
    await expect(page.getByTestId('arc-development-workspace')).toContainText('The Blank Road')
    await expect(page.getByTestId('arc-development-workspace')).toContainText('planning scene')
    await page.getByTestId('section-story-room').click()
    await expect(page.getByTestId('story-room')).toContainText('Arc 1: The Aether Crown')
    await page.screenshot({
      path: testInfo.outputPath('last-kingdom-of-aether-story-room.png'),
      fullPage: true,
    })

    await testInfo.attach('phase-2a-results', {
      body: JSON.stringify({
        project_id: projectId,
        provider: 'gemini',
        model,
        arc_1_maturity: arc1Report.maturity_score,
        arc_1_status: arc1Report.development_status,
        arc_2_maturity: arc2Report.maturity_score,
        arc_3_maturity: arc3Report.maturity_score,
        chapter_plans: chapterPlans.length,
        scene_plans: chapterPlans.length,
        development_agents: developmentPlan.selected_agents,
        world_agents: worldPlan.selected_agents,
        provider_traces: traces.length,
        prose_guard_status: proseAttempt.status(),
      }, null, 2),
      contentType: 'application/json',
    })
  })
})
