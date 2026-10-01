import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

import EditorialWorkspace from './EditorialWorkspace'


const sceneDraft = {
  draft_id: 'scene-draft-1',
  scene_id: 'scene-1',
  arc_id: 'arc-1',
  version_number: 2,
  status: 'approved',
  active: true,
  generated_text: 'Mara hears the crown answer.',
} as any

const chapterDraft = {
  draft_id: 'chapter-draft-1',
  chapter_plan_id: 'chapter-1',
  arc_id: 'arc-1',
  version_number: 1,
  status: 'approved',
  active: true,
  generated_text: 'The archive closes at dusk.',
} as any


test('renders editorial scores, findings, branch lineage, and comparison', () => {
  const onReview = vi.fn()
  const onDialogue = vi.fn()
  const onBranchStatus = vi.fn()
  const onCompare = vi.fn()

  render(
    <EditorialWorkspace
      arcs={[{
        arc_id: 'arc-1',
        title: 'Ash And Stars',
        development_status: 'draftable',
      } as any]}
      sceneDrafts={[sceneDraft]}
      chapterDrafts={[chapterDraft]}
      reports={[{
        report_id: 'report-1',
        subject_type: 'scene',
        subject_id: 'scene-draft-1',
        report_type: 'editorial',
        generated_by: 'EditorAgent',
        score: 84,
        blockers: [],
        findings: [{
          category: 'pacing',
          severity: 'warning',
          message: 'The turn arrives before the emotional beat settles.',
          evidence: ['paragraph 3'],
        }],
        recommendations: ['Give Mara one more beat before the reveal.'],
      } as any]}
      scores={[{
        score_id: 'score-1',
        subject_type: 'scene',
        subject_id: 'scene-draft-1',
        score_type: 'scene_editorial',
        score: 84,
        dimensions: { style: 82, dialogue: 80, pacing: 86 },
      } as any]}
      branches={[{
        branch_id: 'branch-1',
        source_draft_id: 'scene-draft-1',
        source_version_number: 2,
        title: 'Slow the reveal',
        status: 'review',
      } as any]}
      versions={[{
        revision_id: 'revision-1',
        branch_id: 'branch-1',
        version_number: 1,
        generated_text: 'Mara waits. Then the crown answers.',
      } as any]}
      comparisons={{
        'branch-1': {
          branch_id: 'branch-1',
          revision_id: 'revision-1',
          version_number: 1,
          source_text: sceneDraft.generated_text,
          revision_text: 'Mara waits. Then the crown answers.',
          source_word_count: 6,
          revision_word_count: 7,
          similarity: 0.72,
        } as any,
      }}
      onReview={onReview}
      onDialogue={onDialogue}
      onCreateBranch={() => undefined}
      onGenerateRevision={() => undefined}
      onBranchStatus={onBranchStatus}
      onCompare={onCompare}
    />,
  )

  expect(screen.getByTestId('editorial-workspace')).toHaveTextContent('Approved drafts remain authoritative')
  expect(screen.getByTestId('editorial-score-card')).toHaveTextContent('84')
  expect(screen.getByTestId('editorial-report-card')).toHaveTextContent('emotional beat')
  expect(screen.getByTestId('revision-branch-card')).toHaveTextContent('Slow the reveal')
  expect(screen.getByTestId('revision-comparison')).toHaveTextContent('72% similar')

  fireEvent.click(screen.getAllByRole('button', { name: /Editorial Review/ })[0])
  fireEvent.click(screen.getAllByRole('button', { name: /Dialogue Review/ })[0])
  fireEvent.click(screen.getByRole('button', { name: 'Approve Branch' }))
  fireEvent.click(screen.getByRole('button', { name: /Compare/ }))

  expect(onReview).toHaveBeenCalledWith('scene', 'scene-draft-1')
  expect(onDialogue).toHaveBeenCalledWith('scene', 'scene-draft-1')
  expect(onBranchStatus).toHaveBeenCalledWith('branch-1', 'approved')
  expect(onCompare).toHaveBeenCalledWith('branch-1')
})
