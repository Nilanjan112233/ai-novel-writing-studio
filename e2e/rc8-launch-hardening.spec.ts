import { expect, test } from '@playwright/test'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function createMinimalScene(request: any) {
  const projectResponse = await request.post(`${apiBase}/api/projects`, { data: {
    title: `RC8 Visible Failure ${Date.now()}`,
    premise: 'A locksmith hears one impossible door asking to be opened.',
    genre: 'Mystery',
    tone: 'Tense',
  } })
  expect(projectResponse.ok(), await projectResponse.text()).toBeTruthy()
  const project = await projectResponse.json()
  const arcResponse = await request.post(`${apiBase}/api/projects/${project.id}/arcs`, { data: {
    title: 'The Asking Door', purpose: 'Find who is trapped.', goal: 'Open the sealed door.',
    conflict: 'Opening it may release the murderer.', stakes: 'A second victim disappears.',
    chapter_range: [1, 1], order: 1,
  } })
  expect(arcResponse.ok(), await arcResponse.text()).toBeTruthy()
  const arc = await arcResponse.json()
  const chapterResponse = await request.post(`${apiBase}/api/projects/${project.id}/chapter-plans`, { data: {
    arc_id: arc.arc_id, chapter_number: 1, title: 'Three Knocks',
    purpose: 'Introduce the impossible door.', conflict: 'The locksmith recognizes the victim’s knock.',
    character_focus: ['Mira'], status: 'planned',
  } })
  expect(chapterResponse.ok(), await chapterResponse.text()).toBeTruthy()
  const chapter = await chapterResponse.json()
  const sceneResponse = await request.post(`${apiBase}/api/projects/${project.id}/scene-plans-v2`, { data: {
    arc_id: arc.arc_id, chapter_plan_id: chapter.chapter_plan_id, title: 'The Door Speaks',
    purpose: 'Make Mira answer the knock.', conflict: 'The voice knows her hidden crime.',
    outcome: 'Mira lies and takes the key.', character_focus: ['Mira'],
    character_change: 'Professional distance becomes personal fear.', order: 1, status: 'planned',
  } })
  expect(sceneResponse.ok(), await sceneResponse.text()).toBeTruthy()
  return { project, scene: await sceneResponse.json() }
}

test('failed draft generation is visible, recoverable, and protects existing prose', async ({ page, request }) => {
  const { project, scene } = await createMinimalScene(request)
  await page.route(`**/api/projects/${project.id}/scene-plans/${scene.scene_id}/generate-draft`, async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Provider timeout after the scene passed planning checks.' }),
    })
  })
  await page.goto(`/project/${project.id}?section=drafting`)
  const workspace = page.getByTestId('drafting-workspace')
  await expect(workspace).toBeVisible({ timeout: 60_000 })
  await workspace.getByRole('button', { name: 'Generate Exploratory Draft' }).click()
  const failure = page.getByTestId('operation-failure')
  await expect(failure).toBeVisible()
  await expect(failure).toContainText('Draft generation needs your attention')
  await expect(failure).toContainText('existing prose and approved story decisions are unchanged')
  await expect(failure.getByRole('button', { name: 'Retry safely' })).toBeVisible()
  await expect(failure).not.toContainText('Provider timeout')
})
