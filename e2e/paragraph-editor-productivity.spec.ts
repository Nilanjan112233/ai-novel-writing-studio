/**
 * paragraph-editor-productivity.spec.ts
 *
 * Playwright E2E test suite for Milestone 5.B Productivity & Collaboration tools.
 * Verifies version history checkpoints, side-by-side diffs, version restore,
 * comment threads (with reply and resolution workflows), Cmd+K command palette,
 * and live modular writing analytics.
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
    premise: 'A disgraced royal astronomer must prove the stars remember a kingdom erased from every history.',
    genre: 'Fantasy / Mystery',
    tone: 'Poetic and scholarly',
    themes: ['Stellar memory', 'Loss', 'Astronomy'],
  })
  const projectId = project.id

  const arc = await postJson(
    request,
    `${apiBase}/api/projects/${projectId}/arcs`,
    {
      title: 'Arc 1: The Constellation of Shadows',
      purpose: 'Introduce the astronomer and the celestial anomaly.',
      goal: 'Identify the missing star from old charts.',
      conflict: 'All library archives describing the star have been burned.',
      stakes: 'The memories of the lost kingdom will fade forever.',
      resolution_direction: 'She maps the stars by hand to reconstruct the constellation.',
      approval_status: 'approved',
      development_status: 'approved',
      chapter_range: [1, 3],
      mysteries: ['Why did the king order the deletion of the star?'],
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
    'The telescope is calibrated',
    'The chart is copied',
    'The light changes',
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
    character: 'Astronomer',
    current_state: 'Observes with detached interest',
    desired_state: 'Strives to defend memory',
    arc_start_state: 'Observes with detached interest',
    arc_midpoint_state: 'Discovers the missing star in old ledger',
    arc_end_state: 'Strives to defend memory',
    emotional_growth: 'Scholarly indifference to radical protection',
    maturity_growth: 'Stands up to the royal censors',
    power_growth: ['Learns stellar mapping'],
    relationship_growth: [],
    belief_changes: ['History is what we choose to remember'],
    goal_changes: ['Rebuild the atlas'],
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
    character: 'Astronomer',
    starting_power: 'Identifies spectral patterns',
    ending_power: 'Reconstructs star layouts from residual radiation',
    new_abilities: ['Spectral memory tracking'],
    mastered_abilities: [],
    limitations: ['Only visible stars'],
    costs: ['Strains sight'],
    future_evolution: 'Star weaving',
  })

  // Knowledge and Evolution
  const knowledge = await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge`, {
    arc_id: arcId,
    title: 'The royal deletion policy',
    content: 'The censors use a chemical compound to dissolve ink on specific ledger pages.',
    knowledge_type: 'WORLD_TRUTH',
    known_by: [],
    not_known_by: ['Astronomer'],
    confidence: 1,
  })
  await postJson(request, `${apiBase}/api/projects/${projectId}/knowledge-evolutions`, {
    arc_id: arcId,
    knowledge_entry_id: knowledge.entry_id,
    event_type: 'reveal',
    summary: 'The astronomer finds chemical traces on blank pages.',
    order: 3,
    evidence: ['Acid stains'],
  })

  // Foreshadowing
  const foreshadow = await postJson(request, `${apiBase}/api/projects/${projectId}/foreshadowing-v2`, {
    arc_planted: arcId,
    seed: 'A smell of burnt sulfur in the library.',
    seed_chapter_number: 1,
    payoff_target: 'The sulfur compound matches the censors solvent.',
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
    item: 'The Silver Astrolabe',
    owner: 'Astronomer',
    power: 'Aligns mirrors automatically',
    hidden_power: 'Reveals invisible stars',
    cost: 'Concentration',
    limitations: ['Requires moonlight'],
    history: 'Gifted by her mentor',
    future_relevance: 'Arc 2',
    status: 'active',
    arc_ids: [arcId],
    character_ids: ['Astronomer'],
    timeline_entry_ids: [timelines[0].entry_id],
    knowledge_entry_ids: [knowledge.entry_id],
  })
  await postJson(request, `${apiBase}/api/projects/${projectId}/artifact-evolutions`, {
    arc_id: arcId,
    artifact_id: artifact.artifact_id,
    event_type: 'awakening',
    summary: 'The astrolabe mirrors align to a blank spot in the sky.',
    from_state: 'Standard instrument',
    to_state: 'Anomaly tracker',
    order: 3,
    evidence: ['Star projection'],
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
      title: 'Chapter 1: The Dark Observatory',
      purpose: 'Establish the setting and character frustration.',
      conflict: 'The sky is clear but the records are empty.',
      character_focus: ['Astronomer'],
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
      title: 'Scene 1: Cleaning the Lens',
      purpose: 'The astronomer aligns the telescope to a blank spot in the constellation.',
      conflict: 'She sees stars that have no corresponding entries in the ledgers.',
      outcome: 'Frustration grows as she suspects royal tampering.',
      character_focus: ['Astronomer'],
      character_change: 'Skepticism turns to determination.',
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

test.describe('Paragraph Editor - Productivity & Collaboration tools', () => {
  test.setTimeout(120_000)
  let projectId: string
  let sceneId: string

  test.beforeAll(async ({ request }) => {
    test.setTimeout(90000)
    const apiBase = apiBaseUrl()
    const scaffold = await scaffoldProject(request, apiBase, 'Astronomy')
    projectId = scaffold.projectId
    sceneId = scaffold.sceneId

    // Generate initial paragraph skeleton
    const gen = await request.post(`${apiBase}/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`, {
      data: { change_reason: 'initial setup' }
    })
    const responseBody = await gen.text()
    expect(
      gen.ok(),
      `Paragraph productivity setup failed: ${gen.status()} ${gen.statusText()}\n${responseBody}`,
    ).toBeTruthy()
    const genData = JSON.parse(responseBody)
    expect(genData.paragraphs.length).toBeGreaterThan(0)
  })

  test('Writers can save versions, compare diffs, restore history, manage comment threads, use command palette, and view writing analytics', async ({ page }) => {
    // Navigate to workspace
    await page.goto(`/project/${projectId}`)
    await page.getByTestId('section-drafting').click()

    // Open Paragraph Planning Board
    const planBtn = page.getByTestId(`plan-paragraphs-btn-${sceneId}`)
    await expect(planBtn).toBeVisible()
    await planBtn.click()

    // Clicks on paragraph Write button to open Narrative Workspace
    const writeBtn = page.getByTestId('write-prose-btn-1')
    await expect(writeBtn).toBeVisible()
    await writeBtn.click()

    // ── 1. COLLABORATIVE COMMENTS & REVIEW THREADS ──
    const commentsTabBtn = page.getByRole('button', { name: 'Comments' })
    await expect(commentsTabBtn).toBeVisible()
    await commentsTabBtn.click()

    // Add a comment
    const commentInput = page.getByPlaceholder('Add a comment… (Ctrl+Enter to send)')
    await expect(commentInput).toBeVisible()
    await commentInput.fill('Consider shifting focus to the silver reflections on the glass.')
    const sendCommentBtn = page.locator('button[title="Add comment (Ctrl+Enter)"]')
    await sendCommentBtn.click()

    // Verify comment is displayed
    const commentText = page.getByRole('paragraph').filter({ hasText: 'Consider shifting focus to the silver reflections' })
    await expect(commentText).toBeVisible()

    // Add a reply
    const replyBtn = page.getByRole('button', { name: 'Reply' })
    await expect(replyBtn).toBeVisible()
    await replyBtn.click()

    const replyInput = page.getByPlaceholder('Write a reply…')
    await expect(replyInput).toBeVisible()
    await replyInput.fill('Good idea, that heightens the scholarly atmosphere.')
    const sendReplyBtn = page.locator('div.border-t.ml-6 button').first()
    await sendReplyBtn.click()

    // Verify reply is displayed
    await expect(page.getByRole('paragraph').filter({ hasText: 'Good idea, that heightens the scholarly atmosphere.' })).toBeVisible()

    // Resolve comment
    const resolveBtn = page.getByRole('button', { name: 'Resolve', exact: true })
    await expect(resolveBtn).toBeVisible()
    await resolveBtn.click()

    // Verify comment is resolved (hidden under "open" tab)
    await expect(commentText).not.toBeVisible()

    // Click "resolved" filter tab
    const resolvedFilterBtn = page.getByRole('button', { name: 'resolved' })
    await resolvedFilterBtn.click()
    // It should now show up
    await expect(commentText).toBeVisible()

    // ── 2. KEYBOARD PRODUCTIVITY COMMAND PALETTE (Cmd+K) ──
    // Simulate pressing Control+k to open Command Palette
    await page.keyboard.press('Control+k')
    const palette = page.getByTestId('command-palette')
    await expect(palette).toBeVisible()

    // Search and run command to switch to Version History panel
    const paletteInput = page.getByTestId('command-palette-input')
    await paletteInput.fill('History')
    const historyCommandBtn = page.getByRole('option', { name: 'Show Version History' })
    await expect(historyCommandBtn).toBeVisible()
    await historyCommandBtn.click()

    // Command palette should close and the History tab should be active
    await expect(palette).not.toBeVisible()
    const historyHeader = page.locator('text=version')
    await expect(historyHeader).toBeVisible()

    // ── 3. MODULAR WRITING ANALYTICS ──
    // Click on Analytics tab
    const analyticsTabBtn = page.getByRole('button', { name: 'Analytics' })
    await expect(analyticsTabBtn).toBeVisible()
    await analyticsTabBtn.click()

    // Verify empty placeholder is shown initially
    await expect(page.locator('text=Start writing to see analytics.')).toBeVisible()

    // ── 4. VERSION HISTORY TIMELINE, DIFF VIEWER & RESTORE ──
    // Select editor area and type first draft version
    const editor = page.getByTestId('paragraph-prose-editor')
    await expect(editor).toBeVisible()
    await editor.click()
    await page.keyboard.type('The silver gears of the astrolabe ground with a soft sound.')

    // Now stats should be visible on Analytics tab because prose is no longer empty!
    await expect(page.locator('text=Word Count Progress')).toBeVisible()
    await expect(page.locator('text=Prose Composition')).toBeVisible()

    // Trigger manual save
    const saveBtn = page.getByTestId('paragraph-manual-save-btn')
    await expect(saveBtn).toBeVisible()
    await saveBtn.click()

    // Open History Tab
    await expect(historyHeader).not.toBeVisible() // We are on Analytics tab right now
    const historyTabBtn = page.getByTestId('narrative-workspace').getByRole('button', { name: 'History' })
    await historyTabBtn.click()

    // History ledger list should contain 1 version (the manual save we just did)
    // Wait, initial skeleton is version 1. So manual save should make it version 2.
    // Let's check if there is a version entry for v1
    const v1Item = page.locator('text=v1')
    await expect(v1Item).toBeVisible()

    // Type a second draft modification
    await editor.click()
    // Append some text
    await page.keyboard.type(' Under the moonlight, the telescope alignment mirrors slid into position.')
    // Save version 3
    await saveBtn.click()

    // Expect to see v2 in the timeline
    const v2Item = page.locator('text=v2')
    await expect(v2Item).toBeVisible()

    // Click on v1 to view diff
    await v1Item.click()

    // Click View Diff
    const viewDiffBtn = page.getByRole('button', { name: 'View Diff' })
    await expect(viewDiffBtn).toBeVisible()
    await viewDiffBtn.click()

    // Verify diff compares v1 vs current
    await expect(page.locator('text=v1 vs Current')).toBeVisible()
    // Added words should show in green, deleted/original should match
    await expect(page.locator('span.bg-emerald-100').first()).toBeVisible()

    // Restore version 1
    const restoreBtn = page.getByRole('button', { name: 'Restore' })
    await expect(restoreBtn).toBeVisible()
    await restoreBtn.click()

    // Double confirmation: button text shifts to 'Confirm' (in our code it displays as 'Confirm')
    const confirmBtn = page.getByRole('button', { name: 'Confirm' })
    await expect(confirmBtn).toBeVisible()
    await confirmBtn.click()

    // Editor should revert back to original version 1 prose (empty or initial skeleton)
    // Let's verify by checking that the appended text is gone from the editor
    await expect(editor).not.toHaveText(/alignment mirrors slid into position/)
  })
})
