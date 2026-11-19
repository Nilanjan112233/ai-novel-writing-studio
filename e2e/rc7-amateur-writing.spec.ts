import { expect, test } from '@playwright/test'


test('RC7: an amateur author turns planning into a protected first draft with useful guidance', async ({ page }, testInfo) => {
  test.setTimeout(420_000)
  const title = `RC7 Amateur Draft ${Date.now()}`
  const consoleDefects: string[] = []
  page.on('console', (message) => {
    if (['warning', 'error'].includes(message.type())) {
      consoleDefects.push(`${message.type()}: ${message.text()}`)
    }
  })
  page.on('pageerror', (error) => consoleDefects.push(`pageerror: ${error.message}`))

  await page.goto('/projects')
  await page.getByTestId('create-project-toggle').click()
  await page.getByLabel('Project name').fill(title)
  await page.getByLabel('Genre').fill('Character-driven fantasy mystery')
  await page.getByLabel('Tone').fill('Intimate, tense, and quietly hopeful')
  await page.getByLabel('Story seed').fill(
    'A village ferryman can hear the final regret of every passenger, but one silent child may expose why the river is taking memories.',
  )
  await page.getByTestId('create-project').click()
  await expect(page.getByTestId('start-your-novel')).toBeVisible({ timeout: 60_000 })
  await page.getByTestId('start-your-novel').click()
  await expect(page.getByTestId('start-your-novel-flow')).toContainText('Guided author workflow')

  const answers = [
    ['Main Character', 'Tomas Vale', 'A careful ferryman who hides that the river took his wife’s last memory. He wants to protect his daughter but fears the truth will make her hate him.'],
    ['World', 'The River Vey', 'Every crossing costs a small memory. Villagers treat the river as sacred, while the council secretly sells collected memories.'],
    ['Conflict', 'The silent passenger', 'Tomas must protect a child who paid no memory while the council hunts them. If he fails, his daughter’s stolen memories will be erased forever.'],
    ['First Decision', 'Tomas lies to his daughter', 'He tells Mara the child is an ordinary passenger, choosing immediate safety over their fragile trust.'],
    ['First Arc', 'The Fare That Was Not Paid', 'Tomas shelters the child, discovers the council’s ledger, and must choose between exposing the theft or recovering only his daughter’s memories.'],
    ['First Scene', 'The silent crossing', 'At dusk the child steps off Tomas’s boat without paying a memory. The river speaks Tomas’s dead wife’s name, and a council lantern appears upstream.'],
  ] as const

  for (const [index, [label, shortTitle, details]] of answers.entries()) {
    await page.getByRole('button', { name: new RegExp(`\\d+\\. ${label}`) }).click()
    await page.getByLabel(`${label} title`).fill(shortTitle)
    await page.getByLabel(`${label} details`).fill(details)
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await expect(page.getByTestId('start-your-novel-flow')).toContainText(
      `${index + 2} of 7 steps handled`,
      { timeout: 30_000 },
    )
  }
  await expect(page.getByTestId('start-your-novel-flow')).toContainText('7 of 7 steps handled')

  await page.getByTestId('nav-drafting').click()
  const drafting = page.getByTestId('drafting-workspace')
  await expect(drafting).toBeVisible({ timeout: 60_000 })
  await expect(page.getByTestId('writing-dashboard')).toContainText('Generate draft')
  await expect(drafting).toContainText('Planning checks still protect final approval')
  await expect(drafting).toContainText('The silent crossing')
  await expect(drafting.getByRole('button', { name: 'Generate Exploratory Draft' })).toBeEnabled()

  await page.getByTestId('writing-dashboard').getByRole('button', { name: /^Generate draft/i }).click()
  const draftCard = drafting.getByTestId('scene-draft-card').first()
  await expect(draftCard).toBeVisible({ timeout: 240_000 })
  await expect(draftCard).toContainText('Version A')
  await expect(draftCard).toContainText('EXPLORATORY')
  await expect(draftCard).not.toContainText('[Paragraph 1]')
  await draftCard.getByRole('button', { name: 'Why this draft?' }).click()
  await expect(draftCard).toContainText('Expected impact')
  await expect(draftCard).toContainText('What stays unchanged')
  await draftCard.getByRole('button', { name: 'Review' }).click()
  await expect(draftCard).toContainText('REVIEW', { timeout: 60_000 })

  const companion = page.getByTestId('workspace-companion')
  await companion.locator('button[aria-expanded]').click()
  // The Companion may prioritize a higher-severity story/canon issue, but it
  // must retain an actionable writing message for the newly created draft.
  await expect(companion).toContainText(
    /Revise or approve|Review this draft|ready for your review/i,
    { timeout: 60_000 },
  )
  await expect(companion).toContainText(/Choose a focused revision pass|Read the scene/i)

  await page.getByTestId('nav-assistant').click()
  await page.getByLabel('Ask the project assistant').fill(
    'I am new. Why is writing blocked, and what exact thing should I do next?',
  )
  await page.getByTestId('ask-project-assistant').click()
  await expect(page.getByTestId('assistant-message').last()).toBeVisible({ timeout: 90_000 })
  await expect(page.getByTestId('assistant-message').last()).toContainText(/You are at|approval checks/i)
  await expect(page.getByTestId('assistant-message').last()).toContainText(/exploratory draft/i)

  await page.screenshot({
    path: testInfo.outputPath('rc7-amateur-writing-acceptance.png'),
    fullPage: true,
  })
  expect(consoleDefects).toEqual([])
})
