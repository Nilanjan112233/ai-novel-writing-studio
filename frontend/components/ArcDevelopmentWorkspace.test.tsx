import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

import ArcDevelopmentWorkspace from './ArcDevelopmentWorkspace'
import StoryRoom from './StoryRoom'


const arc = {
  arc_id: 'arc-1',
  title: 'The Aether Crown',
  goal: 'Restore the first road.',
  approval_status: 'active',
  development_status: 'draftable',
  focus_role: 'current',
  arc_maturity_score: 92,
  maturity_threshold: 85,
  chapter_range: [1, 6],
  readiness_status: 'READY',
  drafting_eligible: true,
  major_events: [],
  conflicts: [],
  payoffs: [],
  mysteries: [],
  character_changes: [],
  dependencies: [],
} as any


test('assembles one arc into a development workspace', () => {
  render(
    <ArcDevelopmentWorkspace
      arcs={[arc]}
      reports={[{
        project_id: 'project',
        arc_id: 'arc-1',
        development_status: 'draftable',
        focus_role: 'current',
        maturity_score: 92,
        maturity_threshold: 85,
        dimensions: {
          goal_clarity: {
            score: 100,
            weight: 10,
            data_complete: true,
            checklist_satisfied: 1,
            checklist_total: 1,
            evidence: ['arc.goal'],
          },
        },
        checklist: { total: 1, satisfied: 1, required_open: [] },
        dependencies: { items: [], blockers: [], satisfied: true },
        readiness_status: 'READY',
        draftable: true,
        blockers: [],
        evaluated_at: '',
      }]}
      checklists={[{
        project_id: 'project',
        arc_id: 'arc-1',
        item_id: 'goal',
        category: 'Arc',
        title: 'Main Goal Defined',
        description: '',
        priority: 'required',
        status: 'approved',
        dimension: 'goal_clarity',
        weight: 1,
        evidence: [],
        blocking: true,
        source: 'user',
      }]}
      dependencies={[]}
      chapters={[{
        project_id: 'project',
        chapter_plan_id: 'chapter-1',
        arc_id: 'arc-1',
        chapter_number: 1,
        title: 'The Blank Road',
        purpose: 'Introduce the erased border.',
        conflict: 'The archive closes.',
        character_focus: ['Mara'],
        knowledge_changes: [],
        artifact_ids: [],
        foreshadow_ids: [],
        timeline_entry_ids: [],
        status: 'approved',
      }]}
      scenes={[{
        project_id: 'project',
        scene_id: 'scene-1',
        arc_id: 'arc-1',
        chapter_plan_id: 'chapter-1',
        title: 'At the border',
        purpose: 'Make the loss personal.',
        conflict: 'No one remembers the road.',
        outcome: 'The crown wakes.',
        character_focus: ['Mara'],
        character_change: 'Isolation becomes suspicion.',
        knowledge_changes: [],
        foreshadow_links: [],
        artifact_interactions: [],
        timeline_impacts: [],
        status: 'approved',
        order: 1,
      }]}
      characterProgressions={[]}
      powerProgressions={[]}
      knowledge={[]}
      knowledgeEvolutions={[]}
      foreshadowChains={[]}
      artifacts={[]}
      artifactEvolutions={[]}
      onActivate={() => undefined}
      onChecklistStatus={() => undefined}
      draftableArcIds={['arc-1']}
    />,
  )
  expect(screen.getByTestId('arc-development-workspace')).toHaveTextContent('92')
  expect(screen.getByTestId('arc-development-workspace')).toHaveTextContent('DRAFTABLE')
  expect(screen.getByTestId('arc-chapter-plans')).toHaveTextContent('The Blank Road')
  expect(screen.getByTestId('arc-scene-plans')).toHaveTextContent('At the border')
  fireEvent.click(screen.getByTestId('arc-drafting-tab'))
  expect(screen.getByTestId('drafting-workspace')).toHaveTextContent('Drafting gates satisfied')
  expect(screen.getByRole('button', { name: 'Generate Scene' })).toBeEnabled()
})


test('renders the Story Room lanes', () => {
  render(
    <StoryRoom
      room={{
        project_id: 'project',
        current_arc: arc,
        active_discussions: [],
        open_planning_items: [{
          project_id: 'project',
          arc_id: 'arc-1',
          item_id: 'climax',
          category: 'Structure',
          title: 'Climax Defined',
          description: '',
          priority: 'required',
          status: 'missing',
          dimension: 'timeline_coverage',
          weight: 1,
          evidence: [],
          blocking: true,
          source: 'system',
        }],
        blocked_items: [],
        suggestions: [],
        agent_proposals: [],
        draft_queue: [],
        review_queue: [],
        continuity_warnings: [],
        generation_history: { total_versions: 4 },
        generated_at: '',
      }}
    />,
  )
  expect(screen.getByTestId('story-room')).toHaveTextContent('The Aether Crown')
  expect(screen.getByTestId('story-room')).toHaveTextContent('Climax Defined')
  expect(screen.getByTestId('story-room')).toHaveTextContent('4 immutable versions')
})
