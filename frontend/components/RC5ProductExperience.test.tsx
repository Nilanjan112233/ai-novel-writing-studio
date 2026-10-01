import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { expect, test, vi } from 'vitest'

import { authorText, EvidenceList } from './AuthorValue'
import PageGuidance from './PageGuidance'
import { ExplainabilityTimelineView, ProjectTimelineView } from './ProjectTimelines'
import { dataApi } from '@/lib/api'


vi.mock('@/lib/api', () => ({
  dataApi: {
    getProjectTimeline: vi.fn(),
    getExplainabilityTimeline: vi.fn(),
  },
}))


test('renders page purpose, importance, next step, and direct destination', () => {
  const navigate = vi.fn()
  render(<PageGuidance surface={{
    surface_id: 'canon', label: 'Canon', group: 'Govern', aliases: [],
    purpose: 'Shows official story facts.', why_it_matters: 'It protects story consistency.',
    what_to_do: 'Inspect facts and review proposals.', what_happens_next: 'Approved facts refresh the Story Bible.',
    actions: [{ label: 'Review Canon Queue', description: 'Review proposals.', destination: 'canon-queue' }],
  }} onNavigate={navigate} onAsk={vi.fn()} />)
  expect(screen.getByText('Shows official story facts.')).toBeInTheDocument()
  fireEvent.click(screen.getByLabelText('Show page guidance'))
  expect(screen.getByText('It protects story consistency.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Review Canon Queue' }))
  expect(navigate).toHaveBeenCalledWith('canon-queue')
})


test('formats evidence without exposing raw object payloads', () => {
  const evidence = { node_id: 'node-42', source_id: 'db-9', summary: 'A transition is missing between Chapters 8 and 9.' }
  expect(authorText(evidence)).toBe('A transition is missing between Chapters 8 and 9.')
  render(<EvidenceList values={[evidence]} />)
  expect(screen.getByText(/transition is missing/)).toBeInTheDocument()
  expect(screen.queryByText(/node-42/)).not.toBeInTheDocument()
})


test('renders project evolution and evidence-backed Story Health changes', async () => {
  vi.mocked(dataApi.getProjectTimeline).mockResolvedValue({ project_id: 'project-1', count: 1, story_timeline_is_separate: true, entries: [{
    entry_id: 'event-1', date: '2026-07-19T10:00:00Z', action: 'Canon proposal reviewed',
    summary: 'An author decision was recorded.', actor: 'You', affected_systems: ['Canon', 'Story Bible'],
    destination: 'canon-queue', changes: { story_health: 2, canon: 1, timeline: 0 },
    replay: { event: 'Canon proposal reviewed', outcome: 'Story Bible refreshed.', destination: 'canon-queue' },
  }] })
  vi.mocked(dataApi.getExplainabilityTimeline).mockResolvedValue({ project_id: 'project-1', count: 1, changes: [{
    change_id: 'change-1', date: '2026-07-19T10:00:00Z', overall: { from: 82, to: 86, delta: 4 },
    score_changes: [{ category: 'canon', label: 'Canon', from: 80, to: 90, delta: 10 }],
    reasons: [{ direction: 'improved', domain: 'canon', message: 'Resolved: The crown material conflict was resolved.', finding_id: 'finding-1', destination: 'canon' }],
    what_happened: 'Story Health changed after approved evidence refreshed.',
    why_it_matters: 'This shows why the score moved.', suggested_next_step: 'canon',
  }] })
  const navigate = vi.fn()
  const { rerender } = render(<ProjectTimelineView projectId="project-1" onNavigate={navigate} />)
  expect(await screen.findByText('Canon proposal reviewed')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Canon proposal reviewed'))
  fireEvent.click(await screen.findByRole('button', { name: /Open related workspace/ }))
  expect(navigate).toHaveBeenCalledWith('canon-queue')

  rerender(<ExplainabilityTimelineView projectId="project-1" onNavigate={navigate} />)
  expect(await screen.findByText(/Story Health 82/)).toBeInTheDocument()
  expect(screen.getByText(/Resolved: The crown material conflict/)).toBeInTheDocument()
})
