import { APIRequestContext, expect, test } from '@playwright/test'
import { openSection } from './nav'
import { MongoClient, ObjectId } from 'mongodb'
import crypto from 'crypto'
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


test.describe('Phase 3B manuscript and canon governance', () => {
  test.setTimeout(1200000)

  test('governs The Eternal Throne with real Gemini reviews', async ({ page, request }, testInfo) => {
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
      title: `The Eternal Throne ${Date.now()}`,
      premise: 'A historian-queen discovers that her throne edits the memories of everyone who kneels before it.',
      genre: 'Fantasy',
      tone: 'Regal, intimate, and unsettling',
      themes: ['Memory', 'Authority', 'Consent'],
    })
    const projectId = project.id
    const pid = new ObjectId(projectId)
    const arcId = crypto.randomUUID()
    const chapterPlanId = crypto.randomUUID()
    const sceneId = crypto.randomUUID()
    const sceneDraftId = crypto.randomUUID()
    const chapterDraftId = crypto.randomUUID()
    const approvedText = [
      'Queen Maelin entered the archive beneath the throne.',
      'Every ledger remembered a different coronation, but each ended with the same erased name.',
      'She closed the book and refused to kneel.',
    ].join('\n\n')
    const now = new Date()

    const mongo = new MongoClient(
      process.env.MONGODB_URL || 'mongodb://localhost:27017',
    )
    await mongo.connect()
    const db = mongo.db(process.env.DATABASE_NAME || 'novelforge')
    await db.collection('story_arcs').insertOne({
      project_id: pid,
      arc_id: arcId,
      title: 'Arc 1: The Unremembered Coronation',
      approval_status: 'approved',
      development_status: 'draftable',
      focus_role: 'current',
      order: 1,
      created_at: now,
      updated_at: now,
    })
    await db.collection('chapter_plans').insertOne({
      project_id: pid,
      chapter_plan_id: chapterPlanId,
      arc_id: arcId,
      chapter_number: 1,
      title: 'The Name Beneath the Throne',
      purpose: 'Reveal the first canonical contradiction.',
      conflict: 'The throne resists being remembered accurately.',
      status: 'approved',
      created_at: now,
      updated_at: now,
    })
    await db.collection('scene_plans').insertOne({
      project_id: pid,
      scene_id: sceneId,
      chapter_plan_id: chapterPlanId,
      arc_id: arcId,
      title: 'The archive below',
      purpose: 'Find the erased coronation record.',
      conflict: 'The ledgers rewrite themselves.',
      outcome: 'Maelin refuses the throne ritual.',
      status: 'approved',
      order: 1,
      created_at: now,
      updated_at: now,
    })
    await db.collection('scene_drafts').insertOne({
      project_id: pid,
      draft_id: sceneDraftId,
      scene_id: sceneId,
      chapter_plan_id: chapterPlanId,
      arc_id: arcId,
      version_number: 1,
      status: 'approved',
      active: true,
      generated_text: approvedText,
      generated_by: 'SceneWriterAgent',
      created_at: now,
      updated_at: now,
    })
    await db.collection('chapter_drafts').insertOne({
      project_id: pid,
      draft_id: chapterDraftId,
      chapter_plan_id: chapterPlanId,
      arc_id: arcId,
      version_number: 1,
      status: 'approved',
      active: true,
      generated_text: approvedText,
      source_scene_draft_ids: [sceneDraftId],
      generated_by: 'ChapterAssemblerAgent',
      validation_result: 'PASS',
      created_at: now,
      updated_at: now,
    })
    await db.collection('editorial_scores').insertOne({
      project_id: pid,
      score_id: crypto.randomUUID(),
      subject_type: 'chapter',
      subject_id: chapterDraftId,
      score_type: 'chapter_editorial',
      score: 84,
      dimensions: { continuity: 90, pacing: 82 },
      evidence: ['Approved Phase 3A review'],
      calculated_at: now,
    })

    const manuscript = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/manuscripts`,
      { title: 'The Eternal Throne' },
    )
    const assembled = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/manuscripts/${manuscript.manuscript_id}/assemble`,
      { chapter_draft_ids: [chapterDraftId] },
    )
    expect(assembled.version.validation_result).toBe('PASS')
    expect(assembled.version.source_chapters[0].text).toBe(approvedText)

    const manuscriptReview = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/manuscripts/${manuscript.manuscript_id}/review`,
    )
    expect(manuscriptReview.generated_by).toBe('ManuscriptAgent')
    let planResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/orchestration/latest`,
    )
    let plan = await planResponse.json()
    expect(plan.selected_agents).toEqual(['ManuscriptAgent'])
    expect(plan.tasks.filter((task: any) => task.agent_name !== 'ManuscriptAgent').every(
      (task: any) => task.status === 'skipped',
    )).toBeTruthy()

    await putJson(
      request,
      `${apiBase}/api/projects/${projectId}/manuscripts/${manuscript.manuscript_id}/status`,
      { status: 'review' },
    )
    await putJson(
      request,
      `${apiBase}/api/projects/${projectId}/manuscripts/${manuscript.manuscript_id}/status`,
      { status: 'validated' },
    )
    const approved = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/manuscripts/${manuscript.manuscript_id}/approve`,
    )
    expect(approved.status).toBe('approved')

    for (const [sourceVersion, value] of [[1, 'Maelin'], [2, 'The throne']] as const) {
      await postJson(request, `${apiBase}/api/projects/${projectId}/canon/promote`, {
        canon_type: 'artifact',
        source_collection: 'chapter_plans',
        source_id: chapterPlanId,
        source_version: sourceVersion,
        subject: 'The Eternal Throne',
        field: 'owner',
        value,
        evidence: [`Chapter 1 authority version ${sourceVersion}`],
      })
    }
    const canonValidation = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/canon/validate`,
    )
    expect(canonValidation.result).toBe('FAIL')
    expect(canonValidation.conflicts.some(
      (item: any) => item.conflict_type === 'artifact_authority_conflict',
    )).toBeTruthy()
    const canonReview = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/canon/review`,
    )
    expect(canonReview.generated_by).toBe('CanonAgent')
    planResponse = await request.get(
      `${apiBase}/api/projects/${projectId}/orchestration/latest`,
    )
    plan = await planResponse.json()
    expect(plan.selected_agents).toEqual(['CanonAgent'])

    const persistedChapter = await db.collection('chapter_drafts').findOne({
      project_id: pid,
      draft_id: chapterDraftId,
    })
    expect(persistedChapter?.generated_text).toBe(approvedText)

    await page.goto(`/project/${projectId}`)
    await openSection(page, 'manuscript')
    await expect(page.getByTestId('manuscript-workspace')).toContainText('The Eternal Throne')
    await page.screenshot({
      path: testInfo.outputPath('phase-3b-manuscript-workspace.png'),
      fullPage: true,
    })
    await openSection(page, 'canon')
    await expect(page.getByTestId('canon-dashboard')).toContainText('The Eternal Throne')
    await expect(page.getByTestId('canon-conflict')).toBeVisible()
    await page.screenshot({
      path: testInfo.outputPath('phase-3b-canon-dashboard.png'),
      fullPage: true,
    })

    await mongo.close()
  })
})
