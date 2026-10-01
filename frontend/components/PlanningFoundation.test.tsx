import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

import ArcBoard from './ArcBoard'
import KnowledgeView from './KnowledgeView'
import ReadinessDashboard from './ReadinessDashboard'
import TimelineV2 from './TimelineV2'


const arcs = [
  {
    arc_id: 'arc-1',
    title: 'The Waking Map',
    goal: 'Restore the first memory road.',
    approval_status: 'approved',
    chapter_range: [1, 10],
    readiness_status: 'READY',
    drafting_eligible: true,
    major_events: [],
    conflicts: [],
    payoffs: [],
    mysteries: [],
    character_changes: [],
    dependencies: [],
  },
  {
    arc_id: 'arc-3',
    title: 'Beyond the Veil',
    goal: '',
    approval_status: 'draft',
    chapter_range: [21, null],
    readiness_status: 'NOT_READY',
    drafting_eligible: false,
    major_events: [],
    conflicts: [],
    payoffs: [],
    mysteries: [],
    character_changes: [],
    dependencies: [],
  },
] as any


test('renders readiness and arc drafting eligibility', () => {
  const item = {
    item_id: 'goal',
    project_id: 'project',
    arc_id: 'arc-1',
    category: 'Arc',
    title: 'Arc Goal',
    description: '',
    priority: 'required',
    status: 'approved',
    evidence: ['Approved'],
    blocking: true,
    created_at: '',
    updated_at: '',
  } as any
  render(
    <>
      <ReadinessDashboard
        items={[item]}
        reports={[{
          project_id: 'project',
          arc_id: 'arc-1',
          status: 'READY',
          drafting_eligible: true,
          counts: { approved: 1 },
          total_items: 1,
          required_items: 1,
          satisfied_required_items: 1,
          blockers: [],
          missing: [],
          recommended: [],
          ready: [item],
          evaluated_at: '',
        }]}
        arcs={arcs}
      />
      <ArcBoard arcs={arcs} />
    </>,
  )
  expect(screen.getByTestId('readiness-dashboard')).toHaveTextContent('READY')
  expect(screen.getByTestId('arc-board')).toHaveTextContent('Draftable')
  expect(screen.getByTestId('arc-column-idea')).toHaveTextContent('Beyond the Veil')
})


test('renders reader knowledge separately from character knowledge', () => {
  render(
    <KnowledgeView
      entries={[{
        project_id: 'project',
        entry_id: 'clue',
        title: 'The compass glows',
        content: 'Readers see the glow while Elara looks away.',
        knowledge_type: 'READER_KNOWLEDGE',
        known_by: ['Reader'],
        not_known_by: ['Elara'],
        learned_how: 'Visual clue',
        is_false: false,
        confidence: 0.75,
        source: 'foreshadow',
      }]}
    />,
  )
  expect(screen.getByTestId('knowledge-layer-reader_knowledge')).toHaveTextContent('Reader')
  expect(screen.getByTestId('knowledge-layer-reader_knowledge')).toHaveTextContent('Elara')
  expect(screen.getByTestId('knowledge-layer-character_knowledge')).toHaveTextContent('Nothing recorded')
})


test('renders explicit unknown future timeline space', () => {
  render(
    <TimelineV2
      arcs={arcs}
      entries={[{
        project_id: 'project',
        entry_id: 'unknown-1',
        arc_id: 'arc-3',
        title: 'Unknown future turning point',
        summary: '',
        importance: 'major',
        status: 'planned',
        certainty: 'unknown',
        dependencies: [],
        chapter_range: [],
        order: 30,
      }]}
    />,
  )
  expect(screen.getByTestId('timeline-v2')).toHaveTextContent('Beyond the Veil')
  expect(screen.getByTestId('timeline-unknown')).toHaveTextContent('Details intentionally unresolved')
})

test('renders timeline entries returned without optional dependency fields', () => {
  render(
    <TimelineV2
      arcs={[]}
      entries={[{
        project_id: 'project',
        entry_id: 'api-entry',
        title: 'Elias disappeared',
        summary: 'A confirmed planning event.',
        importance: 'major',
        status: 'planned',
        certainty: 'unknown',
        order: 0,
      } as never]}
    />,
  )
  expect(screen.getByTestId('timeline-v2')).toHaveTextContent('Elias disappeared')
})
