import { expect, type Page } from '@playwright/test'
import { stepForSection } from '../frontend/lib/workspaceNav'

/**
 * Open a workspace section the way an author would: through the numbered
 * step in the sidebar (or "More tools"), then the section's tab.
 */
export async function openSection(page: Page, sectionId: string) {
  const target = page.getByTestId(`section-${sectionId}`)
  if (await target.isVisible().catch(() => false)) {
    await target.click()
    return
  }
  const step = stepForSection(sectionId)
  if (step.id === 'more') {
    const more = page.getByTestId('nav-more')
    if ((await more.getAttribute('aria-expanded')) !== 'true') await more.click()
    await target.click()
    return
  }
  await page.getByTestId(`nav-${step.id}`).click()
  if (step.sections.length > 1) {
    await expect(target).toBeVisible()
    await target.click()
  }
}

/** Open the overview (the project's home screen). */
export async function openOverview(page: Page) {
  await page.getByTestId('nav-overview').click()
  await expect(page.getByTestId('primary-project-dashboard')).toBeVisible()
}
