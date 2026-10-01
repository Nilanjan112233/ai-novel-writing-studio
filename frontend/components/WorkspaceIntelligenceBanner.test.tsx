import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { expect, test, vi } from 'vitest'

import WorkspaceIntelligenceBanner from './WorkspaceIntelligenceBanner'
import { dataApi } from '@/lib/api'


vi.mock('@/lib/api', () => ({
  dataApi: { getWorkspaceIntelligence: vi.fn() },
}))


test('surfaces cached narrative intelligence throughout the workspace', async () => {
  vi.mocked(dataApi.getWorkspaceIntelligence).mockResolvedValue({
    recommendations: [{
      recommendation_id: 'finding-1',
      severity: 'high',
      message: 'This chapter introduces two unresolved mysteries.',
      actions: ['Track both mysteries.'],
      evidence: ['Chapter 12'],
      affected_chapters: [12],
      affected_scenes: ['scene-12-a'],
      why: 'Matched the open chapter.',
    }],
  })
  const onExplain = vi.fn()
  render(<WorkspaceIntelligenceBanner projectId="project-1" surface="editor" onExplain={onExplain} />)
  expect(await screen.findByText('This chapter introduces two unresolved mysteries.')).toBeInTheDocument()
  expect(screen.getByText(/Chapters 12/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Explain' }))
  expect(onExplain).toHaveBeenCalled()
})
