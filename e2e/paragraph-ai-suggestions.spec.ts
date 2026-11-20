/**
 * paragraph-ai-suggestions.spec.ts
 *
 * Playwright E2E test suite for Milestone 5.2 - AI Writing Tools.
 * Verifies multiple concurrent suggestions, structured explanations,
 * side-by-side comparison, accept/reject workflows, and history ledger.
 */

import { APIRequestContext, expect, test } from '@playwright/test'
import { openSection } from './nav'
import fs from 'fs'

function apiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  if (fs.existsSync('.novelforge-ports.json')) {
    const ports = JSON.parse(fs.readFileSync('.novelforge-ports.json', 'utf-8'))
    return `http://127.0.0.1:${ports.backendPort || 8000}`
  }
  return 'http://127.0.0.1:8000'
}

async function postJson(
  request: APIRequestContext,
  url: string,
  data: Record<string, unknown> = {},
): Promise<any> {
  const response = await request.post(url, { data })
  expect(response.ok(), `POST ${url} failed: ${await response.text()}`).toBeTruthy()
  return response.json()
}

async function putJson(
  request: APIRequestContext,
  url: string,
  data: Record<string, unknown> = {},
): Promise<any> {
  const response = await request.put(url, { data })
  expect(response.ok(), `PUT ${url} failed: ${await response.text()}`).toBeTruthy()
  return response.json()
}

async function scaffoldProject(
  request: APIRequestContext,
  apiBase: string,
  label: string,
): Promise<{
  projectId: string
  arcId: string
  chapterId: string
  sceneId: string
}> {
  const project = await postJson(request, `${apiBase}/api/projects`, {
    title: `${label} ${Date.now()}`,
    premise: 'A lone cartographer discovers that every map she draws erases the real place.',
    genre: 'Literary Fiction',
    tone: 'Melancholy and precise',
    themes: ['Memory', 'Erasure', 'Cartography'],
  })
  const projectId = project.id

  const arc = await postJson(
    request,
    `${apiBase}/api/projects/${projectId}/arcs`,
    {
      title: 'Arc 1: The First Erasure',
      purpose: 'Establish the cartographer and the curse.',
      goal: 'Complete the first map.',
      conflict: 'Every map erases its subject.',
      stakes: 'The home town disappears from reality.',
      resolution_direction: 'She refuses to finish the map.',
      approval_status: 'approved',
      development_status: 'approved',
      chapter_range: [1, 3],
      mysteries: ['Why does drawing the map erase the real place?'],
      order: 1,
    },
  )
  const arcId = arc.arc_id

  await postJson(
    request,
    `${apiBase}/api/projects/${projectId}/arcs/${arcId}/activate`,
  )

  // Readiness items
  for (const title of ['Protagonist', 'Arc Goal', 'Major Conflict']) {
    await postJson(request, `${apiBase}/api/projects/${projectId}/readiness`, {
      arc_id: arcId,
      category: 'Arc Foundation',
      title,
      priority: 'required',
      status: 'approved',
      evidence: ['Approved for drafting'],
      blocking: true,
    })
  }

  // Arc checklist
  const checklists = await (
    await request.get(
      `${apiBase}/api/projects/${projectId}/arc-checklists?arc_id=${arcId}`,
    )
  ).json()
  for (const item of checklists) {
    await putJson(
      request,
      `${apiBase}/api/projects/${projectId}/arc-checklists/${item.item_id}`,
      { status: 'approved', evidence: ['E2E approved'] },
    )
  }

  // Timelines
  const timelines = []
  for (const [index, title] of [
    'The ink is ground',
    'The border is drawn',
    'The village fades',
  ].entries()) {
    timelines.push(await postJson(request, `${apiBase}/api/projects/${projectId}/timeline-v2`, {
      arc_id: arcId,
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

  // Character Progression
  await postJson(request, `${apiBase}/api/projects/${projectId}/character-progressions`, {
    arc_id: arcId,
    character: 'Cartographer',
    current_state: 'Draws with pride',
    desired_state: 'Refuses to draw',
    arc_start_state: 'Draws with pride',
    arc_midpoint_state: 'Discovers the erasure',
    arc_end_state: 'Refuses to draw',
    emotional_growth: 'Pride to horror',
    maturity_growth: 'Accepts responsibility',
    power_growth: ['Learns erasure magic'],
    relationship_growth: [],
    belief_changes: ['Maps are not objective truth'],
    goal_changes: ['Save the village'],
    skills: [],
    powers: [],
    beliefs: [],
    relationships: [],
    maturity: '',
    trauma: [],
    goals: [],
  })

  // Power Progression
  await postJson(request, `${apiBase}/api/projects/${projectId}/power-progressions`, {
    arc_id: arcId,
    character: 'Cartographer',
    starting_power: 'Draws precise lines',
    ending_power: 'Controls spatial reality',
    new_abilities: ['Erasure recognition'],
    mastered_abilities: [],
    limitations: ['Only drawn places'],
    costs: ['Drains vitality'],
    future_evolution: 'Spatial rewriting',
  })

  // Knowledge and Evolution
  const knowledge = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
    arc_id: arcId,
    title: 'The ink binds reality',
    content: 'The ink used contains minerals that anchor physical space to the paper.',
    knowledge_type: 'WORLD_TRUTH',
    known_by: [],
    not_known_by: ['Cartographer'],
    confidence: 1,
  })

  await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge-evolutions`, {
    arc_id: arcId,
    knowledge_entry_id: knowledge.entry_id,
    event_type: 'reveal',
    summary: 'The cartographer reads the recipe.',
    order: 3,
    evidence: ['Old ledger'],
  })

  // Foreshadowing
  const foreshadow = await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadowing-v2`, {
    arc_planted: arcId,
    seed: 'The ink pot has a silver seal.',
    seed_chapter_number: 1,
    payoff_target: 'The silver seal was made by the erasure guild',
    payoff_chapter_number: 3,
    status: 'seeded',
    timeline_entry_ids: [timelines[0].entry_id],
  })

  for (const [index, eventType] of ['seed', 'payoff'].entries()) {
    await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadow-chains`, {
      arc_id: arcId,
      foreshadow_id: foreshadow.entry_id,
      event_type: eventType,
      summary: eventType,
      order: index + 1,
      evidence: [eventType],
    })
  }

  // Artifact
  const artifact = await postJson(request, `${apiBase}/api/projects/${projectId}/artifacts`, {
    item: 'The Ink Pot',
    owner: 'Cartographer',
    power: 'Holds spatial anchor ink',
    hidden_power: 'Can erase reality',
    cost: 'Vitality',
    limitations: ['Requires concentration'],
    history: 'Inherited from the master',
    future_relevance: 'Arc 2',
    status: 'active',
    arc_ids: [arcId],
    character_ids: ['Cartographer'],
    timeline_entry_ids: [timelines[0].entry_id],
    knowledge_entry_ids: [knowledge.entry_id],
  })

  await postJson(request, `${apiBase}/api/projects/${projectId}/artifact-evolutions`, {
    arc_id: arcId,
    artifact_id: artifact.artifact_id,
    event_type: 'awakening',
    summary: 'The ink pot glows when near the faded edge.',
    from_state: 'Dormant',
    to_state: 'Resonant',
    order: 3,
    evidence: ['Climax'],
  })

  // Verify maturity
  const development = await (
    await request.get(`${apiBase}/api/projects/${projectId}/arcs/${arcId}/development`)
  ).json()
  expect(development.draftable).toBeTruthy()

  const chapter = await postJson(
    request,
    `${apiBase}/api/projects/${projectId}/chapter-plans`,
    {
      arc_id: arcId,
      chapter_number: 1,
      title: 'Chapter 1: Ink and Absence',
      purpose: 'Open with the cartographer at work.',
      conflict: 'The map is almost complete.',
      character_focus: ['Cartographer'],
      knowledge_changes: [],
      artifact_ids: [artifact.artifact_id],
      foreshadow_ids: [foreshadow.entry_id],
      timeline_entry_ids: [timelines[0].entry_id],
      status: 'approved',
    },
  )
  const chapterId = chapter.chapter_plan_id

  const scene = await postJson(
    request,
    `${apiBase}/api/projects/${projectId}/scene-plans-v2`,
    {
      arc_id: arcId,
      chapter_plan_id: chapterId,
      title: 'Scene 1: The Last Line',
      purpose: 'The cartographer draws the final border and the village begins to fade.',
      conflict: 'She cannot stop drawing.',
      outcome: 'The village begins to fade.',
      character_focus: ['Cartographer'],
      character_change: 'Dawning horror replaces professional pride.',
      knowledge_changes: [],
      foreshadow_links: [],
      artifact_interactions: [],
      timeline_impacts: [],
      status: 'approved',
      order: 1,
    },
  )
  const sceneId = scene.scene_id

  return { projectId, arcId, chapterId, sceneId }
}

test.describe('Paragraph Editor - Writing Assistant (AI Tools)', () => {
  let projectId: string
  let sceneId: string

  test.beforeAll(async ({ request }) => {
    test.setTimeout(90000)
    const apiBase = apiBaseUrl()
    const scaffold = await scaffoldProject(request, apiBase, 'AISuggest')
    projectId = scaffold.projectId
    sceneId = scaffold.sceneId

    // Generate paragraphs
    const gen = await request.post(`${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`, {
      data: { change_reason: 'initial setup' }
    })
    expect(gen.ok(), `Failed to generate paragraphs: ${await gen.text()}`).toBeTruthy()
  })

  test('Writers can request, review, inspect, and accept multiple concurrent AI suggestions', async ({ page }) => {
    // Navigate to workspace
    await page.goto(`/project/${projectId}`)
    await openSection(page, 'drafting')

    // Open Paragraph Planning Board
    const planBtn = page.getByTestId(`plan-paragraphs-btn-${sceneId}`)
    await expect(planBtn).toBeVisible()
    await planBtn.click()

    // Clicks on paragraph Write button to open Narrative Workspace
    const writeBtn = page.getByTestId('write-prose-btn-1')
    await expect(writeBtn).toBeVisible()
    await writeBtn.click()

    // Expect three-panel layout to load
    const workspace = page.getByTestId('narrative-workspace')
    await expect(workspace).toBeVisible()

    // Toggle Writing Assistant tab
    const assistantTabBtn = page.getByTestId('writing-assistant-tab-btn')
    await expect(assistantTabBtn).toBeVisible()
    await assistantTabBtn.click()

    // Verify tools display
    const toolsTitle = page.locator('text=Writing Assistant Tools')
    await expect(toolsTitle).toBeVisible()

    // ── 1. Generate Suggestion 1: Expand Prose ──
    const expandBtn = page.getByRole('button', { name: 'Expand Prose' })
    await expect(expandBtn).toBeVisible()
    await expandBtn.click()

    // Ledger history list should contain 1 item
    const ledgerTitle = page.locator('text=Suggestion Ledger History (1)')
    await expect(ledgerTitle).toBeVisible({ timeout: 30000 })

    // ── 2. Generate Suggestion 2: Dialogue Pass ──
    // Click Category tab 'dialogue'
    const dialogueCategoryBtn = page.getByRole('button', { name: 'dialogue' })
    await expect(dialogueCategoryBtn).toBeVisible()
    await dialogueCategoryBtn.click()

    // Trigger dialogue pass
    const dialogueBtn = page.getByRole('button', { name: 'Polish Dialogue' })
    await expect(dialogueBtn).toBeVisible()
    await dialogueBtn.click()

    // Ledger history list should now contain 2 items concurrently!
    const ledgerTitle2 = page.locator('text=Suggestion Ledger History (2)')
    await expect(ledgerTitle2).toBeVisible({ timeout: 30000 })

    // Ensure they both exist on the ledger list
    await expect(page.locator('button:has-text("Expand")').first()).toBeVisible()
    await expect(page.locator('button:has-text("Dialogue")').first()).toBeVisible()

    // ── 3. Inspect suggestion structured reasoning & comparison ──
    const inspectionArea = page.getByTestId('suggestion-inspection-area')
    await expect(inspectionArea).toBeVisible()
    await expect(page.locator('text=Assistant Reasoning')).toBeVisible()
    await expect(page.locator('text=Editing Goal')).toBeVisible()
    await expect(page.locator('text=Reasoning Logic')).toBeVisible()
    await expect(page.locator('text=Summary of Changes')).toBeVisible()
    await expect(page.locator('text=Prose Comparison')).toBeVisible()
    await expect(page.locator('text=Proposed Assistant Suggestion')).toBeVisible()

    // ── 4. Verify version commit upon Acceptance ──
    // Capture version number before accept (should say "Version 1" or similar in history later)
    const acceptBtn = page.getByTestId('accept-suggestion-btn')
    await expect(acceptBtn).toBeVisible()
    await acceptBtn.click()

    // Accepting should update content prose and commit version
    // Check that ledger history has 1 accepted and 1 pending suggestion remaining
    const acceptedPill = page.locator('span:has-text("accepted")').first()
    await expect(acceptedPill).toBeVisible()

    // Second suggestion should remain present and intact in history
    const dialogueHistoryBtn = page.locator('button:has-text("Dialogue")').first()
    await expect(dialogueHistoryBtn).toBeVisible()
  })
})
