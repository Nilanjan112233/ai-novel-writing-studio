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
      // The frontend can become ready before backend migrations finish.
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


test.describe('Phase 3A editorial intelligence', () => {
  test.setTimeout(1200000)

  test('reviews The Kingdom of Ash and Stars through real Gemini without replacing approved prose', async ({ page, request }, testInfo) => {
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
      title: `The Kingdom of Ash and Stars ${Date.now()}`,
      premise: 'A disgraced royal astronomer must prove the stars remember a kingdom erased from every history.',
      genre: 'Fantasy',
      tone: 'Intimate, tense, and luminous',
      themes: ['Memory', 'Authority', 'Belonging'],
    })
    const projectId = project.id
    const arc = await postJson(request, `${apiBase}/api/projects/${projectId}/arcs`, {
      title: 'Arc 1: The Cinder Constellation',
      purpose: 'Restore the first celestial record and expose the court archive.',
      goal: 'Decode the cinder constellation.',
      conflict: 'The royal archivist destroys every corroborating record.',
      stakes: 'The erased kingdom and its surviving people will lose their legal identity.',
      resolution_direction: 'The constellation becomes public evidence.',
      approval_status: 'approved',
      development_status: 'approved',
      chapter_range: [1, 2],
      mysteries: ['Why do the stars preserve the forbidden border?'],
      order: 1,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/arcs/${arc.arc_id}/activate`)

    for (const title of ['Protagonist', 'Arc Goal', 'Major Conflict']) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
        arc_id: arc.arc_id,
        category: 'Arc Foundation',
        title,
        priority: 'required',
        status: 'approved',
        evidence: ['Approved editorial scenario foundation'],
        blocking: true,
      })
    }
    const checklistResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/arc-checklists?arc_id=${arc.arc_id}`,
    )
    expect(checklistResponse.ok()).toBeTruthy()
    for (const item of await checklistResponse.json()) {
      await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/arc-checklists/${item.item_id}`,
        { status: 'approved', evidence: ['Approved editorial scenario coverage'] },
      )
    }

    const timeline = []
    for (const [index, title] of [
      'Sera sees the forbidden constellation',
      'The court archive burns',
      'The erased border appears in starlight',
    ].entries()) {
      timeline.push(await postJson(request, `${apiBase}/api/projects/${projectId}/timeline-v2`, {
        arc_id: arc.arc_id,
        title,
        summary: title,
        importance: 'major',
        status: 'approved',
        certainty: 'known',
        dependencies: [],
        chapter_range: [Math.min(index + 1, 2), Math.min(index + 1, 2)],
        order: index + 1,
      }))
    }
    await postJson(request, `${apiBase}/api/projects/${projectId}/character-progressions`, {
      arc_id: arc.arc_id,
      character: 'Sera Vale',
      current_state: 'Hides what she knows',
      desired_state: 'Makes the evidence public',
      arc_start_state: 'Hides what she knows',
      arc_midpoint_state: 'Trusts one witness',
      arc_end_state: 'Makes the evidence public',
      emotional_growth: 'Shame becomes resolve',
      maturity_growth: 'Accepts shared ownership of truth',
      power_growth: ['Reads the cinder constellation'],
      relationship_growth: ['Trusts Captain Orin'],
      belief_changes: ['Truth requires witnesses'],
      goal_changes: ['Restore legal identity to the erased people'],
      skills: [],
      powers: [],
      beliefs: [],
      relationships: [],
      maturity: '',
      trauma: [],
      goals: [],
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/power-progressions`, {
      arc_id: arc.arc_id,
      character: 'Sera Vale',
      starting_power: 'Reads one ash-star',
      ending_power: 'Maps a complete cinder constellation',
      new_abilities: ['Connects ash-stars into a remembered border'],
      mastered_abilities: [],
      limitations: ['Requires an unobstructed night sky'],
      costs: ['Temporarily loses ordinary color vision'],
      future_evolution: 'Reads changes in historical borders',
    })
    const knowledge = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
      arc_id: arc.arc_id,
      title: 'The erased kingdom survived',
      content: 'Families from the erased kingdom live under false provincial names.',
      knowledge_type: 'WORLD_TRUTH',
      known_by: [],
      not_known_by: ['Sera Vale'],
      confidence: 1,
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge-evolutions`, {
      arc_id: arc.arc_id,
      knowledge_entry_id: knowledge.entry_id,
      event_type: 'reveal',
      summary: 'Sera confirms that the survivors still exist.',
      order: 3,
      evidence: ['The completed constellation'],
    })
    const foreshadow = await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadowing-v2`, {
      arc_planted: arc.arc_id,
      seed: 'One star burns below the horizon.',
      payoff_target: 'The hidden star marks the erased capital.',
      payoff_arc_id: arc.arc_id,
      status: 'seeded',
      timeline_entry_ids: [timeline[0].entry_id],
    })
    for (const [index, eventType] of ['seed', 'payoff'].entries()) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadow-chains`, {
        arc_id: arc.arc_id,
        foreshadow_id: foreshadow.entry_id,
        event_type: eventType,
        summary: eventType,
        order: index + 1,
        evidence: [eventType],
      })
    }
    const artifact = await postJson(request, `${apiBase}/api/projects/${projectId}/artifacts`, {
      item: 'The Ash Astrolabe',
      owner: 'Sera Vale',
      power: 'Aligns visible stars with suppressed records',
      hidden_power: 'Projects the erased border',
      cost: 'Color vision',
      limitations: ['Only works beneath open sky'],
      history: 'Built by the last astronomer of the erased kingdom',
      future_relevance: 'Arc 2',
      status: 'active',
      arc_ids: [arc.arc_id],
      character_ids: ['Sera Vale'],
      timeline_entry_ids: [timeline[0].entry_id],
      knowledge_entry_ids: [knowledge.entry_id],
    })
    await postJson(request, `${apiBase}/api/projects/${projectId}/artifact-evolutions`, {
      arc_id: arc.arc_id,
      artifact_id: artifact.artifact_id,
      event_type: 'awakening',
      summary: 'The astrolabe projects the erased border.',
      from_state: 'Dormant instrument',
      to_state: 'Public witness',
      order: 3,
      evidence: ['Arc climax'],
    })

    const developmentResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/arcs/${arc.arc_id}/development`,
    )
    expect(developmentResponse.ok()).toBeTruthy()
    const development = await developmentResponse.json()
    expect(development.draftable).toBeTruthy()
    expect(development.maturity_score).toBeGreaterThan(85)

    const sceneDrafts = []
    const chapterDrafts = []
    for (let chapterNumber = 1; chapterNumber <= 2; chapterNumber += 1) {
      const chapter = await postJson(request, `${apiBase}/api/projects/${projectId}/chapter-plans`, {
        arc_id: arc.arc_id,
        chapter_number: chapterNumber,
        title: chapterNumber === 1 ? 'The Star Below' : 'The Burning Archive',
        purpose: chapterNumber === 1 ? 'Establish the forbidden evidence.' : 'Make the evidence public.',
        conflict: 'The royal archivist suppresses the celestial record.',
        character_focus: ['Sera Vale'],
        knowledge_changes: [knowledge.entry_id],
        artifact_ids: [artifact.artifact_id],
        foreshadow_ids: [foreshadow.entry_id],
        timeline_entry_ids: [timeline[chapterNumber - 1].entry_id],
        status: 'approved',
      })
      const scene = await postJson(request, `${apiBase}/api/projects/${projectId}/scene-plans-v2`, {
        arc_id: arc.arc_id,
        chapter_plan_id: chapter.chapter_plan_id,
        title: chapterNumber === 1 ? 'On the observatory roof' : 'Inside the burning archive',
        purpose: chapterNumber === 1 ? 'Reveal the impossible star.' : 'Complete the public proof.',
        conflict: 'Sera must act before the record is destroyed.',
        outcome: chapterNumber === 1 ? 'Sera keeps the astrolabe.' : 'The border appears above the court.',
        character_focus: ['Sera Vale'],
        character_change: 'Secrecy becomes witnessed resolve.',
        knowledge_changes: [knowledge.entry_id],
        foreshadow_links: [foreshadow.entry_id],
        artifact_interactions: [artifact.artifact_id],
        timeline_impacts: [timeline[chapterNumber - 1].entry_id],
        status: 'approved',
        order: 1,
      })
      const generatedScene = await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/scene-plans/${scene.scene_id}/generate-draft`,
      )
      expect(generatedScene.continuity_report.result).toBe('PASS')
      await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/scene-drafts/${generatedScene.draft.draft_id}/status`,
        { status: 'review' },
      )
      const approvedScene = await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/scene-drafts/${generatedScene.draft.draft_id}/status`,
        { status: 'approved' },
      )
      sceneDrafts.push(approvedScene.draft)

      const generatedChapter = await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/chapter-plans/${chapter.chapter_plan_id}/generate-draft`,
      )
      expect(generatedChapter.continuity_report.result).toBe('PASS')
      await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/chapter-drafts/${generatedChapter.draft.draft_id}/status`,
        { status: 'review' },
      )
      const approvedChapter = await putJson(
        request,
        `${apiBase}/api/projects/${projectId}/chapter-drafts/${generatedChapter.draft.draft_id}/status`,
        { status: 'approved' },
      )
      chapterDrafts.push(approvedChapter.draft)
    }

    const approvedSourceText = sceneDrafts[0].generated_text
    for (const scene of sceneDrafts) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/editorial/review/scene/${scene.draft_id}`)
      const plan = await (await request.get(
        `${apiBase}/api/projects/${projectId}/orchestration/latest`,
      )).json()
      expect(plan.selected_agents).toEqual(['EditorAgent'])
      expect(plan.tasks.filter((task: any) => task.agent_name !== 'EditorAgent').every(
        (task: any) => task.status === 'skipped',
      )).toBeTruthy()
      await postJson(request, `${apiBase}/api/projects/${projectId}/editorial/dialogue/scene/${scene.draft_id}`)
    }
    for (const chapter of chapterDrafts) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/editorial/review/chapter/${chapter.draft_id}`)
    }
    await postJson(request, `${apiBase}/api/projects/${projectId}/editorial/review/arc/${arc.arc_id}`)

    const branch = await postJson(request, `${apiBase}/api/projects/${projectId}/revision-branches`, {
      source_draft_type: 'scene',
      source_draft_id: sceneDrafts[0].draft_id,
      title: 'Clarify Sera voice and slow the reveal',
    })
    const revision = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/revision-branches/${branch.branch_id}/generate`,
      { change_reason: 'Clarify Sera voice, reduce exposition, and preserve every planned event.' },
    )
    expect(revision.version_number).toBe(1)
    await putJson(
      request,
      `${apiBase}/api/projects/${projectId}/revision-branches/${branch.branch_id}/status`,
      { status: 'review' },
    )

    const lineage = await (
      await request.get(`${apiBase}/api/projects/${projectId}/revision-branches/${branch.branch_id}/lineage`)
    ).json()
    const comparison = await (
      await request.get(`${apiBase}/api/projects/${projectId}/revision-branches/${branch.branch_id}/compare`)
    ).json()
    expect(lineage.lineage[0].versions).toHaveLength(1)
    expect(comparison.source_text).toBe(approvedSourceText)
    expect(comparison.revision_text.length).toBeGreaterThan(40)

    const persistedScenes = await (
      await request.get(`${apiBase}/api/projects/${projectId}/scene-drafts`)
    ).json()
    expect(persistedScenes.find((draft: any) => draft.draft_id === sceneDrafts[0].draft_id).generated_text)
      .toBe(approvedSourceText)

    const dashboard = await (
      await request.get(`${apiBase}/api/projects/${projectId}/editorial/dashboard`)
    ).json()
    expect(dashboard.reports).toHaveLength(7)
    expect(dashboard.scores.some((score: any) => score.score_type === 'arc_editorial')).toBeTruthy()
    expect(dashboard.revision_queue.some((item: any) => item.branch_id === branch.branch_id)).toBeTruthy()

    const tracesResponse = await request.get(`${apiBase}/api/settings/execution-traces?limit=500`)
    expect(tracesResponse.ok()).toBeTruthy()
    const traces = (await tracesResponse.json()).filter(
      (trace: any) => trace.project_id === projectId
        && ['EditorAgent', 'DialogueAgent', 'RevisionAgent'].includes(trace.agent_name),
    )
    expect(traces).toHaveLength(8)
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
    await page.getByTestId('section-editorial').click()
    await expect(page.getByTestId('editorial-workspace')).toContainText('Approved drafts remain authoritative')
    await expect(page.getByTestId('editorial-workspace')).toContainText('Clarify Sera voice')
    await expect(page.getByTestId('editorial-workspace')).toContainText('arc editorial')
    await page.screenshot({
      path: testInfo.outputPath('kingdom-of-ash-and-stars-editorial.png'),
      fullPage: true,
    })

    await testInfo.attach('phase-3a-results', {
      body: JSON.stringify({
        project_id: projectId,
        provider: 'gemini',
        model,
        maturity_score: development.maturity_score,
        approved_scene_drafts: sceneDrafts.length,
        approved_chapter_drafts: chapterDrafts.length,
        editorial_reports: dashboard.reports.length,
        editorial_scores: dashboard.scores.length,
        revision_versions: lineage.lineage[0].versions.length,
        approved_source_unchanged: comparison.source_text === approvedSourceText,
        provider_traces: traces.length,
        tokens: traces.reduce((sum: number, trace: any) => sum + Number(trace.total_tokens || 0), 0),
        cost_usd: traces.reduce((sum: number, trace: any) => sum + Number(trace.cost_usd || 0), 0),
        max_admissions_in_any_60s_window: maxAdmissionsInWindow,
      }, null, 2),
      contentType: 'application/json',
    })
  })
})
