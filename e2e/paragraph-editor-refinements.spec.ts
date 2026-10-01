/**
 * paragraph-editor-refinements.spec.ts
 *
 * Playwright E2E test suite for Milestone 5.1 UX refinements.
 * Verifies the three-panel Narrative Workspace layout, collapsibility,
 * Outline navigator switching, focus mode, and telemetry diagnostics.
 */

import { APIRequestContext, expect, test } from '@playwright/test'
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
  const res = await request.post(url, { data, timeout: 120000 })
  expect(res.ok(), `POST ${url} failed: ${await res.text()}`).toBeTruthy()
  return res.json()
}

async function putJson(
  request: APIRequestContext,
  url: string,
  data: Record<string, unknown>,
): Promise<any> {
  const res = await request.put(url, { data, timeout: 120000 })
  expect(res.ok(), `PUT ${url} failed: ${await res.text()}`).toBeTruthy()
  return res.json()
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

  // 1. Timelines
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

  // 2. Character Progression
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

  // 3. Power Progression
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

  // 4. Knowledge and Evolution
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

  // 5. Foreshadowing and Chain
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

  // 6. Artifact and Evolution
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

test.describe('Paragraph Editor Workspace Refinements', () => {
  let projectId: string
  let sceneId: string

  test.beforeAll(async ({ request }) => {
    test.setTimeout(90000)
    const apiBase = apiBaseUrl()
    const scaffold = await scaffoldProject(request, apiBase, 'UXRefine')
    projectId = scaffold.projectId
    sceneId = scaffold.sceneId

    // Generate paragraphs
    const gen = await request.post(`${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`, {
      data: { change_reason: 'initial setup' }
    })
    expect(gen.ok(), `Failed to generate paragraphs: ${await gen.text()}`).toBeTruthy()
    const genData = await gen.json()
    expect(genData.paragraphs).toBeDefined()
    expect(genData.paragraphs.length).toBeGreaterThan(0)

    // Duplicate paragraph 1 to ensure we have a second paragraph for navigation checks
    const firstParagraphId = genData.paragraphs[0].paragraph_id
    console.log(`INITIAL GENERATED PARAGRAPHS COUNT: ${genData.paragraphs.length}, FIRST ID: ${firstParagraphId}`)
    const dup = await request.post(`${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${firstParagraphId}/duplicate`)
    expect(dup.ok(), `Failed to duplicate paragraph: ${await dup.text()}`).toBeTruthy()
    const dupData = await dup.json()
    console.log(`DUPLICATED PARAGRAPH RESPONSE: ${JSON.stringify(dupData)}`)
  })

  test('Workspace renders three-panel layout and handles interactive toggles', async ({ page }) => {
    // Navigate to project workspace
    await page.goto(`/project/${projectId}`)
    await page.getByTestId('section-drafting').click()

    // Open Paragraph Planning Board
    const planBtn = page.getByTestId(`plan-paragraphs-btn-${sceneId}`)
    await expect(planBtn).toBeVisible()
    await planBtn.click()

    // Open Prose Editor on first paragraph
    const writeBtn = page.getByTestId('write-prose-btn-1')
    await expect(writeBtn).toBeVisible()
    await writeBtn.click()

    // ── 1. Coexisting Three-Panel Narrative Workspace ──
    const workspace = page.getByTestId('narrative-workspace')
    await expect(workspace).toBeVisible()

    // Verify left outline panel is visible by default
    const leftOutline = page.locator('aside[aria-label="Paragraph outline navigator"]')
    await expect(leftOutline).toBeVisible()

    // Verify middle editor content is visible
    const proseEditor = page.getByTestId('paragraph-prose-editor')
    await expect(proseEditor).toBeVisible()

    // Verify right context panel (Narrative Inspector) is visible by default
    const rightContext = page.locator('aside[aria-label="Narrative inspector panel"]')
    await expect(rightContext).toBeVisible()

    // Verify Scene Completion Progress dashboard is visible
    const sceneProgress = page.getByTestId('scene-progress-panel')
    await expect(sceneProgress).toBeVisible()

    // ── 2. Breadcrumbs Location Display ──
    // Expect breadcrumb text to include Project, Chapter, Scene paths
    await expect(page.locator('text=UXRefine').first()).toBeVisible()
    await expect(page.locator('text=Ink and Absence').first()).toBeVisible()
    await expect(page.locator('text=The Last Line').first()).toBeVisible()

    // ── 3. Quick Navigation Switching ──
    // Click on Paragraph 2 in the outline panel
    const p2OutlineItem = leftOutline.locator('button').nth(2)
    await expect(p2OutlineItem).toBeVisible()
    await p2OutlineItem.click()

    // Editor should focus on Paragraph 2
    await expect(page.locator('text=Paragraph 2')).toBeVisible()

    // ── 4. Side Panel Collapsibility & Focus Mode ──
    // Toggle Focus Mode (which collapses side panels)
    const focusBtn = page.getByRole('button', { name: 'Focus Mode' })
    await focusBtn.click()

    // Verify side panels are hidden
    await expect(leftOutline).toHaveClass(/w-0/)
    await expect(rightContext).toHaveClass(/w-0/)

    // Exit Focus Mode
    await focusBtn.click()
    
    // Side panels should restore visibility
    await expect(leftOutline).not.toHaveClass(/w-0/)
    await expect(rightContext).not.toHaveClass(/w-0/)

    // ── 5. Diagnostics Telemetry & Developer Mode ──
    // By default, Developer Telemetry Diagnostics should NOT be visible
    const telemetrySection = page.locator('text=Developer Telemetry Diagnostics')
    await expect(telemetrySection).not.toBeVisible()

    // Toggle Developer Diagnostics Mode by clicking the Cpu toggle button in the Inspector header
    const devToggleBtn = page.locator('button[title="Toggle Developer Diagnostics"]')
    await expect(devToggleBtn).toBeVisible()
    await devToggleBtn.click()

    // Telemetry dashboard should now be visible
    await expect(telemetrySection).toBeVisible()
    await expect(page.locator('text=Editor Load:')).toBeVisible()
    await expect(page.locator('text=Paragraph Switch:')).toBeVisible()
  })
})
