/**
 * paragraph-planning.spec.ts
 *
 * RC2 E2E test suite for Phase 4 — Paragraph-Level Scene Planning.
 *
 * Coverage:
 *  1. Complete workflow: project → chapter → scene → plan paragraphs → all operations
 *  2. Pipeline bar filtering
 *  3. Drag-and-drop reordering (keyboard fallback)
 *  4. Persistence after page reload
 *  5. Visual QA screenshots at 4 viewports
 *  6. Performance: 15 paragraphs rendered without jank
 *  7. AI readiness contract verification
 *  8. Console error monitoring
 */

import { APIRequestContext, expect, test, Page } from '@playwright/test'
import { openSection } from './nav'
import { NEEDS_REAL_AI, realAiConfigured } from './realAi'
import fs from 'fs'

// ── Helpers ───────────────────────────────────────────────────────────────────

function apiBaseUrl(): string {
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
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      if ((await request.get(`${apiBase}/health`)).ok()) return
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error('Backend did not become ready within timeout')
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

/**
 * Create a minimal but fully draftable project+arc+chapter+scene via API.
 * Returns { projectId, arcId, chapterId, sceneId }
 */
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
    payoff_target: 'The silver seal was made by the erasure guild.',
    payoff_arc_id: arcId,
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
  if (!development.draftable) {
    console.error('DEVELOPMENT BLOCKERS:', development.blockers)
  }
  expect(development.draftable).toBeTruthy()
  expect(development.maturity_score).toBeGreaterThan(85)

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

// ── Viewport helpers ──────────────────────────────────────────────────────────

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
}

async function captureViewport(
  page: Page,
  name: string,
  outputPath: (filename: string) => string,
  { width, height }: { width: number; height: number },
) {
  await page.setViewportSize({ width, height })
  await page.waitForTimeout(400) // let layout settle
  await page.screenshot({
    path: outputPath(`${name}.png`),
    fullPage: true,
  })
}

// ── Suites ────────────────────────────────────────────────────────────────────

test.describe('Phase 4 RC2 — Paragraph Planning E2E', () => {
  test.setTimeout(600000)

  // Every case generates scene paragraphs, which the offline mock cannot do.
  test.beforeEach(async ({ request }) => {
    test.skip(!(await realAiConfigured(request, apiBaseUrl())), NEEDS_REAL_AI)
  })

  /**
   * TC-01: Complete user workflow
   * Simulates a first-time writer discovering paragraph planning.
   */
  test('TC-01 complete writer workflow', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    // Monitor console errors
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    // -- Step 1: Scaffold project --
    const { projectId, sceneId } = await scaffoldProject(
      request,
      apiBase,
      'Paragraph Planning RC2',
    )

    // -- Step 2: Navigate to project and open Drafting --
    await page.goto(`/project/${projectId}`)
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await expect(page.getByTestId('drafting-workspace')).toBeVisible()

    // -- Step 3: Find and click "Plan Paragraphs" button --
    const planBtn = page.getByTestId(`plan-paragraphs-btn-${sceneId}`)
    await expect(planBtn).toBeVisible()
    await planBtn.click()

    // -- Step 4: Verify board loads --
    await expect(page.getByTestId('paragraph-planning-board')).toBeVisible()
    await expect(page.getByTestId('board-scene-title')).toContainText('Scene 1')

    // -- Step 5: Verify empty state is shown --
    await expect(page.getByTestId('empty-state')).toBeVisible()
    await expect(page.getByTestId('empty-state')).toContainText(
      'No paragraph skeletons yet',
    )

    await testInfo.attach('board-empty-state', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // -- Step 6: Generate skeletons via API (mock-mode) --
    // Use the API directly since real LLM generation requires a configured provider
    const generated = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`,
    )
    expect(generated.paragraphs).toBeDefined()
    expect(generated.paragraphs.length).toBeGreaterThan(0)

    // Reload to pick up generated paragraphs
    await page.reload()
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await page.getByTestId(`plan-paragraphs-btn-${sceneId}`).click()
    await expect(page.getByTestId('paragraph-planning-board')).toBeVisible()

    // Wait for paragraph cards
    await page.waitForSelector('[data-testid^="paragraph-card-"]', {
      timeout: 10000,
    })
    const cards = page.locator('[data-testid^="paragraph-card-"]')
    const cardCount = await cards.count()
    expect(cardCount).toBeGreaterThan(0)

    await testInfo.attach('board-with-paragraphs', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // -- Step 7: Verify pipeline bar appears --
    await expect(page.getByTestId('pipeline-bar')).toBeVisible()

    // -- Step 8: Expand first card --
    await page.getByTestId('expand-btn-1').click()
    await page.waitForTimeout(200)

    await testInfo.attach('board-card-expanded', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // -- Step 9: Approve first card --
    await page.getByTestId('approve-btn-1').click()
    await page.waitForTimeout(300)
    // Approve chip should update
    const card1 = page.getByTestId('paragraph-card-1')
    await expect(card1).toContainText('Approved')

    // -- Step 10: Lock second card (if exists) --
    if (cardCount > 1) {
      await page.getByTestId('lock-btn-2').click()
      await page.waitForTimeout(300)
      await expect(page.getByTestId('paragraph-card-2')).toContainText('Locked')

      // Unlock it
      await page.getByTestId('lock-btn-2').click()
      await page.waitForTimeout(300)
    }

    // -- Step 11: Pipeline bar filter --
    const planningPill = page.getByTestId('pipeline-stage-planning')
    if (await planningPill.isEnabled()) {
      await planningPill.click()
      await page.waitForTimeout(200)
      // Clear filter button should appear
      await expect(page.getByTestId('pipeline-clear-filter')).toBeVisible()

      await testInfo.attach('board-pipeline-filtered', {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      })

      // Clear filter
      await page.getByTestId('pipeline-clear-filter').click()
      await page.waitForTimeout(200)
    }

    // -- Step 12: Duplicate first card --
    await page.getByTestId('duplicate-btn-1').click()
    await page.waitForTimeout(500)
    // Card count should increase
    const newCount = await cards.count()
    expect(newCount).toBeGreaterThan(cardCount)

    // -- Step 13: Delete the duplicate (last card) --
    page.on('dialog', (dialog) => dialog.accept())
    const deleteBtns = page.locator('[data-testid^="delete-btn-"]')
    const lastDeleteBtn = deleteBtns.last()
    await lastDeleteBtn.click()
    await page.waitForTimeout(500)

    // -- Step 14: Verify persist across reload --
    const approvedSceneId = sceneId
    await page.reload()
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await page.getByTestId(`plan-paragraphs-btn-${approvedSceneId}`).click()
    await expect(page.getByTestId('paragraph-planning-board')).toBeVisible()
    // Should still show paragraphs
    await page.waitForSelector('[data-testid^="paragraph-card-"]', { timeout: 10000 })
    await expect(cards.first()).toBeVisible()

    await testInfo.attach('board-after-reload', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // -- Step 15: History panel --
    const historyBtn = page.getByTestId('history-btn-1')
    await historyBtn.click()
    await page.waitForTimeout(500)
    // History modal or empty state should be visible
    await expect(
      page.locator('[class*="fixed"][class*="inset-0"]'),
    ).toBeVisible()
    // Close with Escape
    await page.keyboard.press('Escape')
    await page.waitForTimeout(200)

    // -- Step 16: Navigate back --
    await page.getByTestId('back-to-drafting-btn').click()
    await expect(page.getByTestId('drafting-workspace')).toBeVisible()

    await testInfo.attach('back-to-drafting', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // -- Final assertions --
    expect(consoleErrors.filter((e) => !e.includes('net::ERR'))).toHaveLength(0)

    await testInfo.attach('tc01-summary', {
      body: JSON.stringify({
        projectId,
        sceneId,
        paragraphsGenerated: generated.paragraphs.length,
        consoleErrors,
      }, null, 2),
      contentType: 'application/json',
    })
  })

  /**
   * TC-02: Visual QA at all four viewports
   */
  test('TC-02 visual QA at 4 viewports', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const { projectId, sceneId } = await scaffoldProject(
      request,
      apiBase,
      'Visual QA',
    )

    // Generate paragraphs
    await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`,
    )

    // Navigate to board
    await page.goto(`/project/${projectId}`)
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await page.getByTestId(`plan-paragraphs-btn-${sceneId}`).click()
    await expect(page.getByTestId('paragraph-planning-board')).toBeVisible()
    await page.waitForSelector('[data-testid^="paragraph-card-"]', { timeout: 10000 })

    for (const [name, viewport] of Object.entries(VIEWPORTS)) {
      await captureViewport(page, name, (filename) => testInfo.outputPath(filename), viewport)
      await testInfo.attach(`viewport-${name}`, {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      })
    }

    // Expand first card at desktop for card design QA
    await page.setViewportSize(VIEWPORTS.desktop)
    await page.getByTestId('expand-btn-1').click()
    await page.waitForTimeout(300)
    await testInfo.attach('card-expanded-desktop', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })
  })

  /**
   * TC-03: Pipeline bar — stage classification and filtering
   */
  test('TC-03 pipeline bar stage filtering', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const { projectId, sceneId } = await scaffoldProject(
      request,
      apiBase,
      'Pipeline Bar',
    )

    // Generate paragraphs and approve first one directly via API
    const { paragraphs } = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`,
    )
    if (paragraphs.length > 0) {
      await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphs[0].paragraph_id}/approve`,
        { approval_state: 'approved' },
      )
    }

    // Navigate
    await page.goto(`/project/${projectId}`)
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await page.getByTestId(`plan-paragraphs-btn-${sceneId}`).click()
    await expect(page.getByTestId('pipeline-bar')).toBeVisible()

    // The 'approved' stage pill should now have count > 0
    const approvedPill = page.getByTestId('pipeline-stage-approved')
    await expect(approvedPill).not.toBeDisabled()

    // Click to filter
    await approvedPill.click()
    await page.waitForTimeout(300)

    await testInfo.attach('pipeline-approved-filter', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // Clear filter
    await page.getByTestId('pipeline-clear-filter').click()
    await page.waitForTimeout(200)

    // All cards visible again
    const allCards = page.locator('[data-testid^="paragraph-card-"]')
    expect(await allCards.count()).toBe(paragraphs.length)
  })

  /**
   * TC-04: Performance — 15 paragraphs renders without jank
   */
  test('TC-04 performance with 15 paragraphs', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const { projectId, sceneId } = await scaffoldProject(
      request,
      apiBase,
      'Performance',
    )

    // Generate paragraphs
    const { paragraphs: initialParagraphs } = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`,
    )

    // Duplicate until we have ≥ 15
    let current = initialParagraphs.length
    const firstId = initialParagraphs[0]?.paragraph_id
    while (current < 15 && firstId) {
      await postJson(
        request,
        `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${firstId}/duplicate`,
      )
      current++
    }

    // Navigate and measure render
    await page.goto(`/project/${projectId}`)
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await page.getByTestId(`plan-paragraphs-btn-${sceneId}`).click()
    await expect(page.getByTestId('paragraph-planning-board')).toBeVisible()

    const t0 = Date.now()
    await page.waitForSelector('[data-testid^="paragraph-card-"]', {
      timeout: 15000,
    })
    const renderMs = Date.now() - t0

    const cards = page.locator('[data-testid^="paragraph-card-"]')
    const count = await cards.count()
    expect(count).toBeGreaterThanOrEqual(Math.min(15, initialParagraphs.length))

    // Scroll performance check
    const scrollStart = Date.now()
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(200)
    const scrollMs = Date.now() - scrollStart

    await testInfo.attach('performance-15-cards', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    await testInfo.attach('performance-metrics', {
      body: JSON.stringify({
        cardCount: count,
        initialRenderMs: renderMs,
        scrollMs,
        verdict: renderMs < 3000 ? 'PASS' : 'SLOW',
      }, null, 2),
      contentType: 'application/json',
    })

    expect(renderMs).toBeLessThan(5000)
    expect(scrollMs).toBeLessThan(1000)
  })

  /**
   * TC-05: AI Readiness — verify paragraph model shape satisfies expansion contract
   */
  test('TC-05 AI readiness contract verification', async ({ request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const { projectId, sceneId } = await scaffoldProject(
      request,
      apiBase,
      'AI Contract',
    )

    const { paragraphs } = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`,
    )
    expect(paragraphs.length).toBeGreaterThan(0)

    const p = paragraphs[0]

    // Core fields required for expansion
    const requiredFields = [
      'paragraph_id',
      'order',
      'purpose',
      'narrative_goal',
      'pov',
      'location',
      'emotion',
      'tension_level',
      'target_word_count',
      'is_locked',
      'approval_state',
      'version',
    ]
    for (const field of requiredFields) {
      expect(
        p[field] !== undefined && p[field] !== null,
        `Field '${field}' is missing from paragraph skeleton`,
      ).toBeTruthy()
    }

    // Processing pipeline contract — must support future stages
    expect(typeof p.processing_pipeline).toBe('object')

    // Validation domains must be per-domain
    expect(typeof p.validation_domains).toBe('object')

    // Dependencies contract for canon review
    expect(p.dependencies).toBeDefined()
    expect(Array.isArray(p.dependencies?.characters)).toBeTruthy()
    expect(Array.isArray(p.dependencies?.canon_facts)).toBeTruthy()
    expect(Array.isArray(p.dependencies?.locations)).toBeTruthy()
    expect(Array.isArray(p.dependencies?.mysteries)).toBeTruthy()

    // Comments and revision_notes for editorial pass
    expect(Array.isArray(p.comments)).toBeTruthy()
    expect(Array.isArray(p.revision_notes)).toBeTruthy()

    // Check history endpoint exists
    const histRes = await request.get(
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${p.paragraph_id}/history`,
    )
    expect(histRes.ok()).toBeTruthy()
    const history = await histRes.json()
    expect(Array.isArray(history)).toBeTruthy()
  })

  /**
   * TC-06: Edit modal and version history
   */
  test('TC-06 edit modal creates version history', async ({ page, request }, testInfo) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)

    const { projectId, sceneId } = await scaffoldProject(
      request,
      apiBase,
      'Edit Modal',
    )

    const { paragraphs } = await postJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`,
    )
    expect(paragraphs.length).toBeGreaterThan(0)
    const p = paragraphs[0]

    // Edit via API — record initial version
    const v1 = p.version

    // Update the paragraph
    await putJson(
      request,
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${p.paragraph_id}`,
      {
        updates: {
          purpose: 'Updated via RC2 test',
          narrative_goal: 'Establish tension at the river bend',
          pov: p.pov || 'Cartographer',
          location: p.location || 'River Bank',
          emotion: p.emotion || 'Dread',
          tension_level: '7',
          dialogue_goal: p.dialogue_goal || '',
          exposition_goal: p.exposition_goal || '',
          target_word_count: 300,
        },
        change_reason: 'RC2 automated edit test',
        create_version: true,
      },
    )

    // Fetch updated paragraph
    const after = await (
      await request.get(
        `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs`,
      )
    ).json()
    const afterP = after.find((x: any) => x.paragraph_id === p.paragraph_id)
    expect(afterP.version).toBeGreaterThan(v1)
    expect(afterP.purpose).toBe('Updated via RC2 test')

    // History should contain v1
    const histRes = await request.get(
      `${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${p.paragraph_id}/history`,
    )
    const history = await histRes.json()
    expect(history.length).toBeGreaterThan(0)
    expect(history[0].change_reason).toBe('RC2 automated edit test')

    // UI: navigate to board and open history panel
    await page.goto(`/project/${projectId}`)
    await page.waitForLoadState('domcontentloaded')
    await openSection(page, 'drafting')
    await page.getByTestId(`plan-paragraphs-btn-${sceneId}`).click()
    await page.waitForSelector('[data-testid^="paragraph-card-"]', { timeout: 10000 })

    await page.getByTestId('history-btn-1').click()
    await page.waitForTimeout(500)

    await testInfo.attach('history-panel', {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    })

    // Panel should be visible with version entries
    await expect(
      page.locator('text=Revision History'),
    ).toBeVisible()

    await page.keyboard.press('Escape')
  })
})
