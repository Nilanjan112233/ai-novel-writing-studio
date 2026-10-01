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
      // Frontend readiness can precede backend migrations.
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
  const response = await request.post(url, { data, timeout: 600000 })
  expect(response.ok(), await response.text()).toBeTruthy()
  return response.json()
}


async function putJson(
  request: APIRequestContext,
  url: string,
  data: Record<string, unknown>,
) {
  const response = await request.put(url, { data, timeout: 600000 })
  expect(response.ok(), await response.text()).toBeTruthy()
  return response.json()
}


test.describe('Phase 2B controlled drafting', () => {
  test.setTimeout(1200000)

  test('drafts The Crown of Emberfall through real Gemini authority gates', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const providersResponse = await request.get(`${apiBase}/api/settings/ai`)
    expect(providersResponse.ok()).toBeTruthy()
    const providers = await providersResponse.json()
    const gemini = providers.providers?.gemini
    test.skip(!gemini?.configured, 'Gemini is not configured in NovelForge settings')
    const model = gemini.model || 'gemini-3.1-flash-lite'

    await putJson(request, `${apiBase}/api/settings/execution`, {
      execution_mode: 'full',
      default_provider: 'gemini',
      default_model: model,
      enable_dynamic_routing: true,
      enable_reflection_loops: false,
      max_cycle_cost_usd: 2,
      max_agent_calls_per_cycle: 10,
      max_orchestration_depth: 5,
      provider_requests_per_minute: 5,
    })
    const assignmentsResponse = await request.get(`${apiBase}/api/settings/agents`)
    expect(assignmentsResponse.ok()).toBeTruthy()
    const assignments = (await assignmentsResponse.json()).map((assignment: any) => ({
      ...assignment,
      provider: 'gemini',
      model,
      enabled: true,
      use_mock_in_hybrid: false,
    }))
    await putJson(request, `${apiBase}/api/settings/agents`, assignments)

    const project = await postJson(request, `${apiBase}/api/projects`, {
      title: `The Crown of Emberfall ${Date.now()}`,
      premise: 'An ember-crowned heir must restore a city whose fires remember betrayal.',
      genre: 'Fantasy',
      tone: 'Intimate and mythic',
      themes: ['Memory', 'Stewardship'],
    })
    const projectId = project.id
    const arc1 = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 1: The Remembering Flame',
      purpose: "Restore Emberfall's first civic flame.",
      goal: 'Relight the witness flame.',
      conflict: 'The regent wants the flame to remember only royal history.',
      stakes: 'The city loses its shared past.',
      resolution_direction: 'The flame becomes a public trust.',
      approval_status: 'approved',
      development_status: 'approved',
      chapter_range: [1, 3],
      mysteries: ["Who changed the flame's memory?"],
      order: 1,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/arcs/${arc1.arc_id}/activate`)
    for (const title of ['Protagonist', 'Arc Goal', 'Major Conflict']) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
        arc_id: arc1.arc_id,
        category: 'Arc Foundation',
        title,
        priority: 'required',
        status: 'approved',
        evidence: ['Approved for drafting'],
        blocking: true,
      })
    }
    const checklistResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/arc-checklists?arc_id=${arc1.arc_id}`,
    )
    expect(checklistResponse.ok()).toBeTruthy()
    for (const item of await checklistResponse.json()) {
      await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/arc-checklists/${item.item_id}`,
        { status: 'approved', evidence: ['Approved for drafting'] },
      )
    }

    const timeline = []
    for (const [index, title] of [
      'The ash gate opens',
      'The regent claims the flame',
      'The city witnesses together',
    ].entries()) {
      timeline.push(await postJson(request, `${apiBase}/api/projects/${projectId}/timeline-v2`, {
        arc_id: arc1.arc_id,
        title,
        summary: title,
        importance: 'major',
        status: 'approved',
        certainty: 'known',
        dependencies: [],
        chapter_range: [index + 1, index + 1],
        order: index + 1,
      }))
    }
    await postJson(request, `${apiBase}/api/projects/${projectId}/character-progressions`, {
      arc_id: arc1.arc_id,
      character: 'Ilyra',
      current_state: 'Guards memory alone',
      desired_state: 'Shares public stewardship',
      arc_start_state: 'Guards memory alone',
      arc_midpoint_state: 'Trusts one witness',
      arc_end_state: 'Shares public stewardship',
      emotional_growth: 'Control becomes trust',
      maturity_growth: 'Accepts limits',
      power_growth: ['Reads the witness flame'],
      relationship_growth: ['Trusts Rowan'],
      belief_changes: ['Truth survives participation'],
      goal_changes: ['Restore the flame for everyone'],
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
      character: 'Ilyra',
      starting_power: 'Sees ember memories',
      ending_power: 'Shares one witnessed memory',
      new_abilities: ['Witness sharing'],
      mastered_abilities: [],
      limitations: ['Requires consent'],
      costs: ['Loses warmth'],
      future_evolution: 'A civic memory network',
    })
    const knowledge = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
      arc_id: arc1.arc_id,
      title: 'The regent altered the flame',
      content: 'The regent removed the rebellion from public memory.',
      knowledge_type: 'WORLD_TRUTH',
      known_by: [],
      not_known_by: ['Ilyra'],
      confidence: 1,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge-evolutions`, {
      arc_id: arc1.arc_id,
      knowledge_entry_id: knowledge.entry_id,
      event_type: 'reveal',
      summary: 'Ilyra confirms the alteration.',
      order: 3,
      evidence: ['Flame memory'],
    })
    const foreshadow = await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadowing-v2`, {
      arc_planted: arc1.arc_id,
      seed: 'One ember burns cold.',
      payoff_target: 'The cold ember holds the erased rebellion.',
      payoff_arc_id: arc1.arc_id,
      status: 'seeded',
      timeline_entry_ids: [timeline[0].entry_id],
    })
    for (const [index, eventType] of ['seed', 'payoff'].entries()) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadow-chains`, {
        arc_id: arc1.arc_id,
        foreshadow_id: foreshadow.entry_id,
        event_type: eventType,
        summary: eventType,
        order: index + 1,
        evidence: [eventType],
      })
    }
    const artifact = await postJson(request, `${apiBase}/api/projects/${projectId}/artifacts`, {
      item: 'The Ember Crown',
      owner: 'Ilyra',
      power: 'Reads civic flame memories',
      hidden_power: 'Shares a memory with witnesses',
      cost: 'Warmth',
      limitations: ['Requires consent'],
      history: "Forged at the city's founding",
      future_relevance: 'Arc 2',
      status: 'active',
      arc_ids: [arc1.arc_id],
      character_ids: ['Ilyra'],
      timeline_entry_ids: [timeline[0].entry_id],
      knowledge_entry_ids: [knowledge.entry_id],
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/artifact-evolutions`, {
      arc_id: arc1.arc_id,
      artifact_id: artifact.artifact_id,
      event_type: 'awakening',
      summary: 'The crown shares its first memory.',
      from_state: 'Private',
      to_state: 'Witness-bound',
      order: 3,
      evidence: ['Climax'],
    })

    const development = await (
      await request.get(`${apiBase}/api/projects/${projectId}/arcs/${arc1.arc_id}/development`)
    ).json()
    expect(development.draftable).toBeTruthy()
    expect(development.maturity_score).toBeGreaterThan(85)

    const chapters = []
    const scenes = []
    for (let chapterNumber = 1; chapterNumber <= 3; chapterNumber += 1) {
      const chapter = await postJson(request, `${apiBase}/api/projects/${projectId}/chapter-plans`, {
        arc_id: arc1.arc_id,
        chapter_number: chapterNumber,
        title: `Emberfall Chapter ${chapterNumber}`,
        purpose: `Advance the approved movement ${chapterNumber}.`,
        conflict: 'The regent contests the public memory.',
        character_focus: ['Ilyra'],
        knowledge_changes: [knowledge.entry_id],
        artifact_ids: [artifact.artifact_id],
        foreshadow_ids: [foreshadow.entry_id],
        timeline_entry_ids: [timeline[chapterNumber - 1].entry_id],
        status: 'approved',
      })
      chapters.push(chapter)
      for (let order = 1; order <= 2; order += 1) {
        scenes.push(await postJson(request, `${apiBase}/api/projects/${projectId}/scene-plans-v2`, {
          arc_id: arc1.arc_id,
          chapter_plan_id: chapter.chapter_plan_id,
          title: `Chapter ${chapterNumber} Scene ${order}`,
          purpose: 'Execute one approved beat without changing planning truth.',
          conflict: 'The public record and royal record disagree.',
          outcome: 'Ilyra preserves the planned evidence.',
          character_focus: ['Ilyra'],
          character_change: 'Control becomes shared stewardship.',
          knowledge_changes: [knowledge.entry_id],
          foreshadow_links: [foreshadow.entry_id],
          artifact_interactions: [artifact.artifact_id],
          timeline_impacts: [timeline[chapterNumber - 1].entry_id],
          status: 'approved',
          order,
        }))
      }
    }

    const sceneDrafts = []
    for (const scene of scenes) {
      const generated = await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/scene-plans/${scene.scene_id}/generate-draft`,
      )
      expect(generated.continuity_report.result).toBe('PASS')
      expect(generated.draft.status).toBe('draft')
      expect(generated.draft.generated_text.length).toBeGreaterThan(40)
      await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/scene-drafts/${generated.draft.draft_id}/status`,
        { status: 'review' },
      )
      const approved = await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/scene-drafts/${generated.draft.draft_id}/status`,
        { status: 'approved' },
      )
      expect(approved.continuity_report.result).toBe('PASS')
      sceneDrafts.push(approved.draft)
    }

    const chapterDrafts = []
    for (const chapter of chapters) {
      const generated = await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/chapter-plans/${chapter.chapter_plan_id}/generate-draft`,
      )
      expect(generated.continuity_report.result).toBe('PASS')
      expect(generated.draft.source_scene_draft_ids).toHaveLength(2)
      await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/chapter-drafts/${generated.draft.draft_id}/status`,
        { status: 'review' },
      )
      const approved = await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/chapter-drafts/${generated.draft.draft_id}/status`,
        { status: 'approved' },
      )
      expect(approved.continuity_report.result).toBe('PASS')
      chapterDrafts.push(approved.draft)
    }

    for (const [order, developmentStatus] of [[2, 'development'], [3, 'idea']] as const) {
      const arc = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
        title: `Arc ${order}: Future Ember`,
        purpose: 'Remain intentionally incomplete.',
        goal: 'Unknown',
        conflict: 'Unknown',
        stakes: 'Unknown',
        approval_status: 'draft',
        development_status: developmentStatus,
        chapter_range: [order * 3 + 1, order * 3 + 3],
        order,
      })
      const chapter = await postJson(request, `${apiBase}/api/projects/${projectId}/chapter-plans`, {
        arc_id: arc.arc_id,
        chapter_number: order * 3 + 1,
        title: 'Blocked Future Chapter',
        purpose: 'Placeholder',
        conflict: 'Unknown',
        character_focus: ['Ilyra'],
        knowledge_changes: [],
        artifact_ids: [],
        foreshadow_ids: [],
        timeline_entry_ids: [],
        status: 'approved',
      })
      const scene = await postJson(request, `${apiBase}/api/projects/${projectId}/scene-plans-v2`, {
        arc_id: arc.arc_id,
        chapter_plan_id: chapter.chapter_plan_id,
        title: 'Blocked Future Scene',
        purpose: 'Placeholder',
        conflict: 'Unknown',
        outcome: 'Unknown',
        character_focus: ['Ilyra'],
        knowledge_changes: [],
        foreshadow_links: [],
        artifact_interactions: [],
        timeline_impacts: [],
        status: 'approved',
        order: 1,
      })
      const denied = await request.post(
        `${apiBase}/api/projects/${projectId}/scene-plans/${scene.scene_id}/generate-draft`,
        { data: {}, timeout: 600000 },
      )
      expect(denied.status()).toBe(409)
    }

    const reviewQueue = await (
      await request.get(`${apiBase}/api/projects/${projectId}/draft-review-queue`)
    ).json()
    expect(reviewQueue.generation_history.scene_versions).toBe(6)
    expect(reviewQueue.generation_history.chapter_versions).toBe(3)
    expect(reviewQueue.continuity_warnings).toHaveLength(0)

    const tracesResponse = await request.get(
      `${apiBase}/api/settings/execution-traces?limit=500`,
    )
    expect(tracesResponse.ok()).toBeTruthy()
    const traces = (await tracesResponse.json()).filter(
      (trace: any) => trace.project_id === projectId
        && ['SceneWriterAgent', 'ChapterAssemblerAgent'].includes(trace.agent_name),
    )
    // Six scene generations and three chapter assemblies are the minimum.
    // Schema-correction retries are valid provider calls and intentionally
    // produce additional traces, so a real model run is not fixed at nine.
    expect(traces.length).toBeGreaterThanOrEqual(9)
    expect(traces.filter((trace: any) => trace.agent_name === 'SceneWriterAgent').length).toBeGreaterThanOrEqual(6)
    expect(traces.filter((trace: any) => trace.agent_name === 'ChapterAssemblerAgent').length).toBeGreaterThanOrEqual(3)
    expect(traces.every((trace: any) => trace.provider === 'gemini' && trace.model === model)).toBeTruthy()
    expect(traces.every((trace: any) => Number(trace.metadata?.rate_limit_per_minute) === 5)).toBeTruthy()
    const admissions = traces
      .map((trace: any) => Date.parse(trace.metadata?.rate_limit_acquired_at || ''))
      .sort((left: number, right: number) => left - right)
    expect(admissions.every((value: number) => Number.isFinite(value))).toBeTruthy()
    const maxAdmissionsInWindow = admissions.reduce((maximum: number, start: number) => (
      Math.max(
        maximum,
        admissions.filter((value: number) => value >= start && value < start + 60000).length,
      )
    ), 0)
    expect(maxAdmissionsInWindow).toBeLessThanOrEqual(5)

    await page.goto(`/project/${projectId}`)
    await page.getByTestId('section-drafting').click()
    await expect(page.getByTestId('drafting-workspace')).toContainText('Drafting gates satisfied')
    await expect(page.getByTestId('drafting-workspace')).toContainText('Chapter 1 Scene 1')
    await expect(page.getByTestId('drafting-workspace')).toContainText('Emberfall Chapter 3')
    await expect(page.getByTestId('drafting-workspace')).toContainText('APPROVED')
    await page.screenshot({
      path: testInfo.outputPath('crown-of-emberfall-drafting.png'),
      fullPage: true,
    })

    await testInfo.attach('phase-2b-results', {
      body: JSON.stringify({
        project_id: projectId,
        provider: 'gemini',
        model,
        maturity_score: development.maturity_score,
        scene_drafts: sceneDrafts.length,
        chapter_drafts: chapterDrafts.length,
        continuity_warnings: reviewQueue.continuity_warnings.length,
        provider_traces: traces.length,
        tokens: traces.reduce((sum: number, trace: any) => sum + Number(trace.total_tokens || 0), 0),
        cost_usd: traces.reduce((sum: number, trace: any) => sum + Number(trace.cost_usd || 0), 0),
        limiter_wait_ms: traces.reduce(
          (sum: number, trace: any) => sum + Number(trace.metadata?.rate_limit_wait_ms || 0),
          0,
        ),
        max_admissions_in_any_60s_window: maxAdmissionsInWindow,
      }, null, 2),
      contentType: 'application/json',
    })
  })
})
