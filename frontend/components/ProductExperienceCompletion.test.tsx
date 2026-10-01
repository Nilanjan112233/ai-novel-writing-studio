import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'

import NarrativeCritiquePanel from './NarrativeCritiquePanel'
import NarrativeProductionPipeline from './NarrativeProductionPipeline'
import WorkspaceCompanion from './WorkspaceCompanion'
import { dataApi } from '@/lib/api'


vi.mock('@/lib/api', () => ({
  dataApi: {
    getNarrativeCompleteness: vi.fn(),
    getNovelCreationGuide: vi.fn(),
    getNarrativeCritique: vi.fn(),
    refreshNarrativeCritique: vi.fn(),
    getWorkspaceCompanion: vi.fn(),
    updateWorkspaceCompanionMessage: vi.fn(),
  },
}))

const criterion = { criterion_id: 'story.premise', label: 'A clear premise', met: true, required: true, evidence: ['Premise'], target: 'vision', suggested_improvement: 'No action required.' }
const milestone = { gate_id: 'concept_complete', label: 'Concept Complete', achieved: true, criteria: [criterion], blockers: [] }
const dimensions = Object.fromEntries(['story', 'character', 'world', 'power', 'relationship', 'mystery', 'timeline', 'canon'].map((dimension) => [dimension, { dimension, score: 75, status: 'in_progress', criteria: [criterion], blockers: [], remaining: [] }]))
const completeness = {
  project_id: 'project-1', overall_completion: 75, current_milestone: 'Concept Complete', dimensions,
  milestones: [milestone, ...['World Ready', 'Draft Ready', 'Revision Ready', 'Publication Ready'].map((label, index) => ({ gate_id: `gate-${index}`, label, achieved: false, criteria: [{ ...criterion, met: false }], blockers: [{ ...criterion, met: false }] }))],
  remaining_work: [], next_actions: [{ action_id: 'world', label: 'Define the world', reason: 'Add world rules.', target: 'world', milestone: 'World Ready' }], calculated_at: '2026-07-19T00:00:00Z',
}
const guide = { steps: [{ step_id: 'vision', label: 'Story vision', why_it_matters: 'Align the story promise.', target: 'vision', ai_systems: ['Story Coach'], completion: 75, required_information: [], optional_improvements: [] }], jump_freely: true, milestones: completeness.milestones, current_milestone: 'Concept Complete', next_actions: completeness.next_actions }


beforeEach(() => vi.clearAllMocks())

describe('completed product experience', () => {
  test('renders explicit production gates and a jump-anywhere creation guide', async () => {
    vi.mocked(dataApi.getNarrativeCompleteness).mockResolvedValue(completeness)
    vi.mocked(dataApi.getNovelCreationGuide).mockResolvedValue(guide)
    const navigate = vi.fn()
    render(<NarrativeProductionPipeline projectId="project-1" showGuide onNavigate={navigate} />)
    expect((await screen.findAllByText('Concept Complete')).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Publication Ready')).toBeInTheDocument()
    expect(screen.getByTestId('novel-creation-guide')).toHaveTextContent('Story vision')
    fireEvent.click(screen.getByText('Define the world'))
    expect(navigate).toHaveBeenCalledWith('world')
  })

  test('shows routed critique evidence and never presents automatic application', async () => {
    const result = { story_health_before: 90, story_health_after: 84, analysis_id: 'analysis-1', critique_finding_count: 1, generated_at: '2026-07-19T00:00:00Z', author_control: 'Improvements are proposals only and are never applied automatically.', findings: [{ finding_id: 'critique-1', finding_type: 'critique', domain: 'character', category: 'weak_motivation', severity: 'high', explanation: 'Asha acts without an established motivation.', affected_chapters: [3], affected_scenes: [], affected_elements: ['Asha'], evidence: ['Chapter 3'], recommended_actions: ['Clarify the goal.'], suggested_improvement: 'Clarify the goal.', responsible_subsystem: 'character_intelligence', confidence: .91 }] }
    vi.mocked(dataApi.getNarrativeCritique).mockResolvedValue(result)
    render(<NarrativeCritiquePanel projectId="project-1" onNavigate={vi.fn()} />)
    expect(await screen.findByText('weak motivation')).toBeInTheDocument()
    expect(screen.getByText(/Responsible: character intelligence/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Supporting evidence'))
    expect(screen.getByText(/Chapter 3/)).toBeInTheDocument()
  })

  test('keeps proactive companion quiet until expanded and supports navigation', async () => {
    vi.mocked(dataApi.getWorkspaceCompanion).mockResolvedValue({ messages: [{ message_id: 'message-1', kind: 'attention', title: 'Canon proposals need review', message: 'You have 2 canon proposals waiting for a decision.', target: 'canon', priority: 85, evidence: [], read: false, dismissed: false, created_at: '2026-07-19T00:00:00Z' }], headline: null, story_health: 82, current_milestone: 'World Ready', next_actions: [], behavior: { motion: 'subtle', interruptive: false, respects_reduced_motion: true }, refreshed_at: '2026-07-19T00:00:00Z' })
    const navigate = vi.fn()
    render(<WorkspaceCompanion projectId="project-1" onNavigate={navigate} onAsk={vi.fn()} />)
    const trigger = await screen.findByRole('button', { name: /Canon proposals need review/i })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(document.querySelector('[data-companion-state="notifying"]')).toBeInTheDocument()
    fireEvent.click(trigger)
    fireEvent.click(screen.getByText('Show me'))
    expect(navigate).toHaveBeenCalledWith('canon')
    await waitFor(() => expect(screen.getByText('Ask how this page works')).toBeInTheDocument())
  })
})
