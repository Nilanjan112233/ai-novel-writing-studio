import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { expect, test, vi } from 'vitest'

import StoryHealthDashboard from './StoryHealthDashboard'


test('renders health, audit findings, memory, and change impact controls', () => {
  const onAudit = vi.fn()
  const onPreviewImpact = vi.fn()
  const onImpactStatus = vi.fn()
  render(
    <StoryHealthDashboard
      health={{
        story_health_score: 74,
        status: 'watch',
        calculated_at: '2026-06-14T00:00:00Z',
        dimension_scores: {
          overall: 74,
          character: 82,
          canon: 70,
          timeline: 76,
          plot: 68,
          pacing: 72,
          continuity: 78,
          balance: 80,
        },
        analysis: {
          source_documents: 250,
          nodes: 250,
          edges: 403,
          findings: 1,
          recomputed_nodes: 1,
          reused_nodes: 249,
          duration_ms: 24,
          incremental: true,
        },
        findings: [{
          finding_id: 'finding-1',
          domain: 'plot',
          category: 'unresolved_promise',
          severity: 'high',
          explanation: 'The brass key promise has no detected resolution.',
          affected_chapters: [4],
          affected_scenes: ['scene-4'],
          affected_elements: ['key-thread'],
          evidence: ['Return the brass key'],
          recommended_actions: ['Link the promise to a later payoff.'],
          confidence: 0.92,
        }],
        metrics: {
          total_chapters: 50,
          total_words: 85000,
          open_mysteries: 4,
          resolved_mysteries: 2,
          unresolved_promises: 2,
          active_artifacts: 3,
          abandoned_artifacts: 1,
          active_foreshadowing: 5,
          resolved_foreshadowing: 2,
          canon_conflicts: 1,
          continuity_warnings: 2,
          pacing_warnings: 3,
          abandoned_characters: 1,
          character_arc_completion: 60,
          arc_completion: 50,
          manuscript_readiness: 'IN_REVIEW',
          editorial_blockers: 1,
        },
      }}
      audits={[{
        report_id: 'audit-1',
        result: 'WARNING',
        findings: [{
          category: 'unresolved_promise',
          severity: 'warning',
          message: 'The bell promise remains open.',
        }],
        finding_counts: { unresolved_promise: 1 },
        deterministic_finding_count: 1,
        agent_finding_count: 0,
        generated_by: ['deterministic'],
        created_at: '2026-06-14T00:00:00Z',
      }]}
      chapters={[{
        intelligence_id: 'chapter-50',
        chapter_plan_id: 'plan-50',
        chapter_draft_id: 'draft-50',
        chapter_draft_version: 1,
        chapter_number: 50,
        chapter_summary: 'Mara refuses the clean answer.',
        important_events: [],
        characters_present: ['Mara'],
        character_changes: [],
        knowledge_revealed: [],
        mysteries_introduced: [],
        mysteries_advanced: [],
        mysteries_resolved: [],
        foreshadowing_introduced: [],
        foreshadowing_advanced: [],
        foreshadowing_resolved: [],
        artifact_usage: [],
        relationship_changes: [],
        timeline_impact: [],
        canon_impact: [],
        unresolved_questions: [],
        future_obligations: ['Return the bell'],
        quality_findings: [],
        word_count: 1700,
        active: true,
        generated_at: '2026-06-14T00:00:00Z',
      }]}
      impacts={[]}
      busyId={null}
      onAudit={onAudit}
      onPreviewImpact={onPreviewImpact}
      onImpactStatus={onImpactStatus}
    />,
  )

  expect(screen.getByTestId('story-health-score')).toHaveTextContent('74')
  expect(screen.getByText('The bell promise remains open.')).toBeInTheDocument()
  expect(screen.getByText('Chapter 50')).toBeInTheDocument()
  expect(screen.getByTestId('narrative-intelligence-platform')).toBeInTheDocument()
  expect(screen.getByText(/Scores update when you approve chapters/)).toBeInTheDocument()
  expect(screen.getByText('The brass key promise has no detected resolution.')).toBeInTheDocument()
  expect(screen.getByText('Chapter 4')).toBeInTheDocument()

  fireEvent.click(screen.getByTestId('run-story-audit'))
  expect(onAudit).toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Change target'), {
    target: { value: 'Mara' },
  })
  fireEvent.click(screen.getByTestId('preview-change-impact'))
  expect(onPreviewImpact).toHaveBeenCalledWith(
    'character_removal',
    { name: 'Mara' },
  )
})
