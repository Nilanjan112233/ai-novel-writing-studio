import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { vi } from 'vitest'

import CanonDashboard from './CanonDashboard'
import ManuscriptWorkspace from './ManuscriptWorkspace'


test('renders manuscript versions, validation, and manual approval controls', () => {
  const onStatus = vi.fn()
  render(
    <ManuscriptWorkspace
      manuscripts={[{
        project_id: 'project-1',
        manuscript_id: 'manuscript-1',
        title: 'The Eternal Throne',
        status: 'validated',
        active: true,
        version: 2,
        current_version_id: 'version-2',
        created_at: '2026-06-14',
        updated_at: '2026-06-14',
      }]}
      versions={[{
        project_id: 'project-1',
        manuscript_id: 'manuscript-1',
        version_id: 'version-2',
        version_number: 2,
        parent_version_id: 'version-1',
        source_chapters: [],
        assembled_text: 'Approved chapter text.',
        chapter_count: 3,
        validation_result: 'PASS',
        created_at: '2026-06-14',
      }]}
      reports={[{
        project_id: 'project-1',
        report_id: 'report-1',
        manuscript_id: 'manuscript-1',
        version_id: 'version-2',
        report_type: 'deterministic_validation',
        result: 'PASS',
        findings: [],
        evidence: [],
        created_at: '2026-06-14',
      }]}
      chapterDrafts={[]}
      onCreate={vi.fn()}
      onAssemble={vi.fn()}
      onReview={vi.fn()}
      onStatus={onStatus}
      onRollback={vi.fn()}
    />,
  )

  expect(screen.getByTestId('manuscript-workspace')).toHaveTextContent('Your approved chapters are copied in exactly as written')
  expect(screen.getByTestId('manuscript-version')).toHaveTextContent('Version 2')
  expect(screen.getByTestId('manuscript-report')).toHaveTextContent('PASS')
  fireEvent.click(screen.getByText('Approve Manuscript'))
  expect(onStatus).toHaveBeenCalledWith('manuscript-1', 'approved')
})


test('renders typed canon, conflicts, and review history', () => {
  const onConflictStatus = vi.fn()
  render(
    <CanonDashboard
      records={[{
        project_id: 'project-1',
        canon_id: 'canon-1',
        canon_type: 'artifact',
        source_collection: 'artifact_registry',
        source_id: 'artifact-1',
        source_version: 1,
        authority_level: 'approved',
        active: true,
        subject: 'Ember Crown',
        field: 'owner',
        value: 'Mara',
        evidence: [],
        created_at: '2026-06-14',
        updated_at: '2026-06-14',
      }]}
      conflicts={[{
        project_id: 'project-1',
        conflict_id: 'conflict-1',
        conflict_type: 'artifact_authority_conflict',
        domain: 'artifact',
        subject: 'Ember Crown',
        field: 'owner',
        severity: 'high',
        message: 'Active canon has two owners.',
        canon_ids: ['canon-1'],
        evidence: ['Mara', 'Ilyan'],
        status: 'open',
        detected_at: '2026-06-14',
      }]}
      reports={[{
        project_id: 'project-1',
        report_id: 'report-1',
        report_type: 'canon_review',
        result: 'WARNING',
        findings: [],
        recommendations: ['Resolve ownership.'],
        evidence: [],
        generated_by: 'CanonAgent',
        created_at: '2026-06-14',
      }]}
      onValidate={vi.fn()}
      onReview={vi.fn()}
      onConflictStatus={onConflictStatus}
      onRecordActive={vi.fn()}
    />,
  )

  expect(screen.getByTestId('canon-dashboard')).toHaveTextContent('Ember Crown')
  expect(screen.getByTestId('canon-conflict')).toHaveTextContent('Active canon has two owners')
  fireEvent.click(screen.getByText('Acknowledge'))
  expect(onConflictStatus).toHaveBeenCalledWith('conflict-1', 'acknowledged')
})
