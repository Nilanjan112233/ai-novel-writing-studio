import { expect, test, APIRequestContext } from '@playwright/test'
import { MongoClient, ObjectId } from 'mongodb'
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
      // Frontend can become ready before backend migrations finish.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Backend did not become ready')
}


test.describe('Phase 7 Interactive Narrative Studio', () => {
  test.setTimeout(600000)

  test('converses, navigates, explains the graph, and governs canon with real Gemini', async ({ page, request }) => {
    const apiBase = apiBaseUrl()
    await waitForBackend(request, apiBase)
    const providerSettings = await (await request.get(`${apiBase}/api/settings/ai`)).json()
    test.skip(!providerSettings.providers?.gemini?.configured, 'Gemini is not configured in NovelForge settings')
    const model = 'gemini-3.1-flash-lite'

    const modelTest = await request.post(`${apiBase}/api/settings/test-model`, {
      data: { provider: 'gemini', model },
    })
    expect(modelTest.ok(), await modelTest.text()).toBeTruthy()
    const modelTestBody = await modelTest.json()
    expect(modelTestBody.success, JSON.stringify(modelTestBody)).toBeTruthy()
    const execution = await (await request.get(`${apiBase}/api/settings/execution`)).json()
    expect((await request.put(`${apiBase}/api/settings/execution`, {
      data: {
        ...execution,
        execution_mode: 'full',
        default_provider: 'gemini',
        default_model: model,
        enable_reflection_loops: false,
        provider_requests_per_minute: 5,
      },
    })).ok()).toBeTruthy()

    const created = await request.post(`${apiBase}/api/projects`, {
      data: {
        title: `Phase 7 Browser Proof ${Date.now()}`,
        premise: 'An archivist discovers that the city bell edits promises after they are spoken.',
        genre: 'Literary fantasy',
        tone: 'Intimate and uncertain',
      },
    })
    expect(created.ok(), await created.text()).toBeTruthy()
    const projectId = (await created.json()).id
    const pid = new ObjectId(projectId)
    const mongo = new MongoClient(process.env.MONGODB_URL || 'mongodb://localhost:27017')
    await mongo.connect()
    const db = mongo.db(process.env.DATABASE_NAME || 'novelforge')
    const now = new Date()
    await db.collection('character_bibles').insertOne({
      project_id: pid,
      name: 'Mara Venn',
      role: 'archivist',
      personality: ['observant', 'defensive'],
      motivations: ['protect the dockworkers pact'],
      beliefs: ['easy consensus hides a cost'],
      emotional_state: 'wary',
      dialogue_style: 'precise, with strategic omissions',
      vocabulary: ['record', 'oath', 'witness'],
      internal_conflicts: ['truth versus mercy'],
      current_status: 'dead',
      death_chapter: 3,
      updated_at: now,
    })
    await db.collection('chapter_intelligence').insertMany(Array.from({ length: 20 }, (_, index) => {
      const chapter = index + 1
      return {
        project_id: pid,
        intelligence_id: `phase7-chapter-${chapter}`,
        chapter_plan_id: `phase7-plan-${chapter}`,
        chapter_draft_id: `phase7-draft-${chapter}`,
        chapter_number: chapter,
        title: `Chapter ${chapter}`,
        chapter_summary: chapter <= 3 ? 'Mara hears the bell distort an oath.' : 'Soren investigates the history Mara never learned.',
        important_events: [`Event ${chapter}`],
        characters_present: chapter <= 3 ? ['Mara Venn'] : ['Soren Vale'],
        future_obligations: chapter === 1 ? ['Return the cracked seal'] : [],
        mysteries_resolved: [],
        foreshadowing_resolved: [],
        word_count: 1600,
        active: true,
        updated_at: now,
      }
    }))
    await db.collection('timeline_entries').insertMany(Array.from({ length: 20 }, (_, index) => ({
      project_id: pid,
      entry_id: `phase7-timeline-${index + 1}`,
      title: `Timeline event ${index + 1}`,
      chapter_number: index + 1,
      order: index + 1,
      updated_at: now,
    })))
    await db.collection('knowledge_entries').insertMany([
      { project_id: pid, entry_id: 'mara-early', title: 'The bell alters memory', content: 'Mara knows the bell changes agreement.', knowledge_type: 'CHARACTER_KNOWLEDGE', known_by: ['Mara Venn'], learned_chapter: 2 },
      { project_id: pid, entry_id: 'mara-future', title: 'The council confession', content: 'This is learned after Mara dies.', knowledge_type: 'CHARACTER_KNOWLEDGE', known_by: ['Mara Venn'], learned_chapter: 12 },
    ])
    await db.collection('mystery_registry').insertOne({
      project_id: pid,
      mystery_id: 'bell-teacher',
      question: 'Who taught the bell to erase agreement?',
      status: 'open',
      introduced_chapter: 1,
      updated_at: now,
    })
    await db.collection('power_progressions').insertOne({
      project_id: pid,
      progression_id: 'bell-memory',
      name: 'Bell Memory',
      character: 'Mara Venn',
      limitations: ['cannot restore consent'],
      updated_at: now,
    })
    await mongo.close()

    const analysis = await request.post(`${apiBase}/api/projects/${projectId}/narrative-analysis`, { data: { force: true } })
    expect(analysis.ok(), await analysis.text()).toBeTruthy()
    const audit = await request.post(`${apiBase}/api/projects/${projectId}/story-audit`, { data: { include_agent: false } })
    expect(audit.ok(), await audit.text()).toBeTruthy()

    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`/project/${projectId}`)
    await expect(page.getByTestId('workspace-intelligence-banner')).toBeVisible()
    await page.getByTestId('nav-assistant').click()
    await expect(page.getByTestId('interactive-assistant-drawer')).toBeVisible()
    await page.getByLabel('Assistant mode').selectOption('continuity_expert')
    await page.getByLabel('Ask the project assistant').fill('Open Chapter 12 and explain the unresolved mystery.')
    await page.getByTestId('ask-project-assistant').click()
    const assistantMessage = page.getByTestId('assistant-message').last()
    await expect(assistantMessage).toBeVisible({ timeout: 120000 })
    await expect(assistantMessage).toContainText('supporting story references')
    await assistantMessage.getByTestId('assistant-navigation-action').first().click()
    await expect(page.getByTestId('drafting-panel')).toBeVisible()

    await page.getByTestId('nav-assistant').click()
    await page.getByTestId('interactive-tab-characters').click()
    await page.getByLabel('Conversation timeline chapter').fill('20')
    await page.getByLabel('Message character').fill('What do you know about the council confession?')
    await page.getByTestId('send-character-message').click()
    const characterTurn = page.getByTestId('character-conversation-turn').last()
    await expect(characterTurn).toBeVisible({ timeout: 120000 })
    await expect(characterTurn).toContainText('Chapter 3 awareness')
    await expect(characterTurn).toContainText('Death boundary enforced')

    await page.getByTestId('interactive-tab-graph').click()
    await expect(page.getByTestId('knowledge-graph-canvas')).toBeVisible()
    await expect(page.getByTestId('knowledge-graph-panel')).toContainText('story elements')
    await expect(page.getByTestId('knowledge-graph-panel')).toContainText('relationships')
    await page.getByLabel('character: Mara Venn').click()
    await expect(page.getByTestId('knowledge-graph-inspector')).toContainText('Mara Venn')

    const proposed = await request.post(`${apiBase}/api/projects/${projectId}/canon/proposals`, {
      data: {
        canon_type: 'artifact',
        subject: 'Cracked seal',
        field: 'material',
        value: 'bell bronze',
        confidence: 0.91,
        evidence: ['Chapter 1'],
        affected_chapters: [1],
      },
    })
    expect(proposed.ok(), await proposed.text()).toBeTruthy()
    await page.reload()
    await page.getByTestId('nav-assistant').click()
    await page.getByTestId('interactive-tab-proposals').click()
    const proposalCard = page.getByTestId('canon-proposal-card').filter({ hasText: 'Cracked seal — material' })
    await expect(proposalCard).toBeVisible()
    const decisionResponse = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/canon/proposals/`)
    ))
    await proposalCard.getByTestId('approve-canon-proposal').click()
    const reviewed = await decisionResponse
    expect(reviewed.ok(), `${reviewed.status()} ${await reviewed.text()}`).toBeTruthy()
    await expect(proposalCard).toContainText('approved', { timeout: 120000 })

    await page.getByTestId('interactive-tab-intelligence').click()
    const recommendation = page.getByTestId('workspace-recommendation').first()
    await expect(recommendation).toBeVisible()
    await recommendation.getByRole('button', { name: 'Why was this generated?' }).click()
    await expect(page.getByTestId('explainability-panel')).toBeVisible()
    await page.screenshot({
      path: 'artifacts/phase7-interactive-studio-desktop.png',
      fullPage: true,
    })

    const integrity = await request.get(`${apiBase}/api/projects/${projectId}/audit`)
    expect(integrity.ok(), await integrity.text()).toBeTruthy()
    expect((await integrity.json()).status).toBe('pass')

    await page.setViewportSize({ width: 390, height: 844 })
    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
      window.scrollTo(0, 0)
    })
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
    expect(await page.evaluate(() => window.scrollX)).toBe(0)
    const mobileDrawer = page.getByTestId('interactive-assistant-drawer')
    await expect(mobileDrawer).toHaveCSS('transform', 'none')
    const mobileBounds = await mobileDrawer.evaluate((element) => {
      const rect = element.getBoundingClientRect()
      return { left: rect.left, right: rect.right, width: rect.width, innerWidth: window.innerWidth, clientWidth: document.documentElement.clientWidth }
    })
    expect(mobileBounds.left).toBeGreaterThanOrEqual(0)
    expect(mobileBounds.right).toBeLessThanOrEqual(mobileBounds.innerWidth)
    expect(mobileBounds.width).toBe(mobileBounds.clientWidth)
    await page.screenshot({
      path: 'artifacts/phase7-interactive-studio-mobile.png',
    })

    const deletion = await request.delete(`${apiBase}/api/projects/${projectId}`)
    expect(deletion.ok(), await deletion.text()).toBeTruthy()
  })
})
