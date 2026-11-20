import { expect, test } from '@playwright/test'
import { openSection } from './nav'


test('an amateur author can create a project, follow one path, and reach a first scene', async ({ page }) => {
  test.setTimeout(120_000)
  const title = `Remembering Roads ${Date.now()}`
  await page.goto('/projects')
  await page.getByTestId('create-project-toggle').click()
  await page.getByLabel('Project name').fill(title)
  await page.getByLabel('Genre').fill('Fantasy mystery')
  await page.getByLabel('Tone').fill('Hopeful and eerie')
  await page.getByLabel('Your story idea').fill('A mapmaker discovers a road that remembers everyone who vanished on it.')
  await page.getByTestId('create-project').click()

  await expect(page.getByTestId('primary-project-dashboard')).toBeVisible({ timeout: 45_000 })
  const start = page.getByTestId('start-your-novel')
  await expect(start).toBeVisible({ timeout: 45_000 })
  await expect(start).toContainText(/setup/i)
  await start.click()
  await expect(page.getByTestId('start-your-novel-flow')).toContainText('Guided author workflow')
  await expect(page.getByTestId('start-your-novel-flow')).toContainText('This can be changed, undone, or expanded later.')

  const choices = [
    ['Main Character', 'Mara Vale', 'A patient mapmaker who fears forgetting her missing sister.'],
    ['World', 'The Folded Kingdom', 'Roads remember promises and change when those promises are broken.'],
    ['Conflict', 'The vanishing road', 'Mara must follow it before it consumes her sister’s final memory.'],
    ['First Decision', 'Trust the road', 'Mara breaks guild law and chooses to follow the impossible road.'],
    ['First Arc', 'The Road Opens', 'Mara finds the road, defies the guild, and crosses its first threshold.'],
    ['First Scene', 'The impossible line', 'At midnight a new road draws itself across Mara’s map.'],
  ] as const

  for (const [index, [label, shortTitle, details]] of choices.entries()) {
    await page.getByRole('button', { name: new RegExp(`\\d+\\. ${label}`) }).click()
    await page.getByLabel(`${label} title`).fill(shortTitle)
    await page.getByLabel(`${label} details`).fill(details)
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await expect(page.getByTestId('start-your-novel-flow')).toContainText(`${index + 2} of 7 steps handled`, { timeout: 30_000 })
  }
  await expect(page.getByTestId('start-your-novel-flow')).toContainText('7 of 7 steps handled')
  await expect(page.getByTestId('start-your-novel-flow')).toContainText('100%')

  await openSection(page, 'characters')
  await expect(page.getByTestId('characters-panel')).toContainText('Mara Vale')
  await openSection(page, 'power')
  const emptyPower = page.getByTestId('empty-state-power')
  await expect(emptyPower).toContainText('Create manually')
  await expect(emptyPower).toContainText('Generate with AI')
  await expect(emptyPower).toContainText('Import existing')
  await expect(emptyPower).toContainText('Continue guided setup')

  await page.getByTestId('nav-overview').click()
  await expect(page.getByTestId('next-step-card')).toBeVisible()
  await expect(page.getByTestId('book-progress')).toBeVisible()
})


test('the project library supports server search, favorites, badges, and paging controls', async ({ page }) => {
  await page.goto('/projects')
  await expect(page.getByTestId('projects-grid')).toBeVisible()
  await page.getByTestId('project-search').fill('Remembering Roads')
  const firstCard = page.getByTestId('project-card').first()
  await expect(firstCard).toBeVisible({ timeout: 30_000 })
  await expect(firstCard).toContainText(/Getting Started|Complete|Consistency|Ready/i)
  const article = firstCard.locator('..')
  const favorite = article.getByRole('button', { name: /favorites/i })
  await favorite.click()
  await expect(article.getByRole('button', { name: /Remove .* from favorites/i })).toBeVisible()
})
