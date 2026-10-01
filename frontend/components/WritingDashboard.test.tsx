import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { dataApi } from '@/lib/api'
import WritingDashboard from './WritingDashboard'


vi.mock('@/lib/api', () => ({
  dataApi: {
    getWritingDashboard: vi.fn(),
  },
}))


test('explains the writing stage, blockers, context reuse, and next action', async () => {
  vi.mocked(dataApi.getWritingDashboard).mockResolvedValue({
    project_id: 'project-1',
    current_arc: { arc_id: 'arc-1', title: 'The Last Crossing' },
    current_chapter: { chapter_plan_id: 'chapter-1', number: 1, title: 'The Toll' },
    current_scene: { scene_id: 'scene-1', title: 'A Hand on the Rope', status: 'planned' },
    current_draft: null,
    metrics: {
      words: 0,
      characters: 0,
      reading_minutes: 0,
      writing_streak_days: 1,
      last_edited: null,
      pending_ai_suggestions: 0,
      pending_revisions: 0,
      approved_scenes: 0,
      total_scenes: 1,
    },
    workflow: {
      active_stage: 'Generate draft',
      steps: [
        { title: 'Scene plan', complete: true, current: false },
        { title: 'Generate draft', complete: false, current: true },
        { title: 'Review draft', complete: false, current: false },
      ],
    },
    scene_health: {
      result: 'FAIL',
      blockers: ['Scene plan is not approved', 'Chapter plan is not approved'],
      evidence: [],
    },
    next_action: {
      title: 'Generate your first draft',
      explanation: 'Explore the scene now while approval remains protected.',
      action: 'Generate draft',
      target: 'drafting',
      scene_id: 'scene-1',
      allow_exploratory: true,
    },
    context_used: {
      characters: 1,
      canon_facts: 2,
      timeline_events: 0,
      plot_threads: 1,
      approved_decisions: 3,
    },
    generated_at: new Date().toISOString(),
  })
  const onGenerate = vi.fn()
  const onNavigate = vi.fn()

  render(
    <WritingDashboard
      projectId="project-1"
      refreshKey="initial"
      onGenerate={onGenerate}
      onNavigate={onNavigate}
    />,
  )

  await waitFor(() => expect(screen.getByTestId('writing-dashboard')).toBeInTheDocument())
  expect(screen.getByTestId('writing-dashboard')).toHaveTextContent('Chapter 1: The Toll')
  expect(screen.getByTestId('writing-dashboard')).toHaveTextContent('Generate draft')
  expect(screen.getByTestId('writing-dashboard')).toHaveTextContent('Scene plan is not approved')
  expect(screen.getByTestId('writing-dashboard')).toHaveTextContent('1 characters')
  expect(screen.getByTestId('writing-dashboard')).toHaveTextContent('3 approved decisions')

  fireEvent.click(screen.getByRole('button', { name: /generate draft/i }))
  expect(onGenerate).toHaveBeenCalledWith('scene-1', true)

  fireEvent.click(screen.getByRole('button', { name: /review planning checks/i }))
  expect(onNavigate).toHaveBeenCalledWith('arc-development')
})
