import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import InteractiveNarrativeStudio from './InteractiveNarrativeStudio'
import { dataApi } from '@/lib/api'


vi.mock('@/lib/api', () => ({
  dataApi: {
    getAssistantModes: vi.fn(),
    getAssistantHistory: vi.fn(),
    askProjectAssistant: vi.fn(),
    getCharacterConversationHistory: vi.fn(),
    converseWithCharacter: vi.fn(),
    getKnowledgeGraph: vi.fn(),
    getKnowledgeGraphNode: vi.fn(),
    getCanonProposals: vi.fn(),
    createCanonProposal: vi.fn(),
    reviewCanonProposal: vi.fn(),
    getWorkspaceIntelligence: vi.fn(),
    explainNarrativeFinding: vi.fn(),
  },
}))


const assistantMessage = {
  message_id: 'message-1',
  mode: 'continuity_expert',
  query: 'Open Chapter 12',
  answer: 'Chapter 12 contains one unresolved promise.',
  navigation_actions: [{ type: 'navigate', target: 'chapter', section: 'drafting', chapter_number: 12, label: 'Open Chapter 12' }],
  evidence: { finding_ids: ['finding-1'], node_ids: ['chapter:12'], chapters: [12], canon_facts: [], timeline_events: [], analysis_id: 'analysis-123456' },
  canon_proposal_ids: [],
  generation_metadata: { provider: 'gemini', model: 'gemini-3.1-flash-lite' },
  created_at: '2026-07-18T00:00:00Z',
}

const graph = {
  analysis_id: 'analysis-123456',
  graph_version: 1,
  nodes: [{
    node_id: 'character:mara', kind: 'character', label: 'Mara Venn', chapter_numbers: [1, 2], scene_ids: [],
    source_collection: 'character_bibles', source_id: 'Mara Venn', payload: { role: 'archivist' }, warning_count: 1,
    story_health_warnings: [{ finding_id: 'finding-1', severity: 'high', explanation: 'Mara disappears after chapter 2.' }],
  }],
  edges: [],
  counts: { nodes: 1, edges: 0, by_kind: { character: 1 } },
  source: 'narrative_analysis_engine',
}

const proposal = {
  proposal_id: 'proposal-1', canon_type: 'artifact', subject: 'Seal', field: 'material', value: 'bronze', confidence: 0.9,
  evidence: ['Chapter 1'], affected_chapters: [1], affected_scenes: [], source_type: 'character_conversation', source_id: 'turn-1',
  downstream_impact: { total_affected: 2, risk: 'low', requires_confirmation: false }, impact_id: 'impact-1', status: 'pending', created_at: '2026-07-18T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(dataApi.getAssistantModes).mockResolvedValue([
    { id: 'story_coach', label: 'Story Coach', description: 'Coach the author.' },
    { id: 'continuity_expert', label: 'Continuity Expert', description: 'Protect canon.' },
  ])
  vi.mocked(dataApi.getAssistantHistory).mockResolvedValue([])
  vi.mocked(dataApi.askProjectAssistant).mockResolvedValue(assistantMessage)
  vi.mocked(dataApi.getCharacterConversationHistory).mockResolvedValue([])
  vi.mocked(dataApi.converseWithCharacter).mockResolvedValue({
    conversation_id: 'conversation-1', turn_id: 'turn-1', character_name: 'Mara Venn', timeline_chapter: 3,
    author_message: 'What do you know?', character_response: 'Only what I learned before the bell fell silent.',
    awareness_boundary: { requested_chapter: 20, effective_chapter: 3, death_boundary_applied: true, death_chapter: 3 },
    evidence: { canon_ids: ['canon-1'], timeline_node_ids: ['timeline-3'], chapter_numbers: [1, 2, 3], knowledge_entry_ids: ['known-early'] },
    canon_proposal_ids: [], generation_metadata: {}, created_at: '2026-07-18T00:00:00Z',
  })
  vi.mocked(dataApi.getKnowledgeGraph).mockResolvedValue(graph)
  vi.mocked(dataApi.getKnowledgeGraphNode).mockResolvedValue({ node: graph.nodes[0], summary: { role: 'archivist' }, connected_entities: [] })
  vi.mocked(dataApi.getCanonProposals).mockResolvedValue([proposal])
  vi.mocked(dataApi.reviewCanonProposal).mockResolvedValue({ ...proposal, status: 'approved' })
  vi.mocked(dataApi.createCanonProposal).mockResolvedValue(proposal)
  vi.mocked(dataApi.getWorkspaceIntelligence).mockResolvedValue({ recommendations: [{
    recommendation_id: 'finding-1', severity: 'high', message: 'Mara disappears after chapter 2.', actions: ['Review her arc.'], evidence: ['Chapter 2'], affected_chapters: [2], affected_scenes: [], why: 'Matched current context.',
  }] })
  vi.mocked(dataApi.explainNarrativeFinding).mockResolvedValue({ why: 'The shared graph has no later presence.', evidence: ['Chapter 2'], canon_facts: [], timeline_events: [] })
})


function renderStudio(onNavigate = vi.fn()) {
  render(
    <InteractiveNarrativeStudio
      projectId="project-1"
      characters={[{ name: 'Mara Venn', role: 'archivist' } as never]}
      onNavigate={onNavigate}
    />,
  )
  return onNavigate
}


test('asks the grounded project assistant and executes a navigation action', async () => {
  const onNavigate = renderStudio()
  await screen.findByText(/Ask about your novel or the application/)
  fireEvent.change(screen.getByLabelText('Assistant mode'), { target: { value: 'continuity_expert' } })
  fireEvent.change(screen.getByLabelText('Ask the project assistant'), { target: { value: 'Open Chapter 12' } })
  fireEvent.click(screen.getByTestId('ask-project-assistant'))
  expect(await screen.findByText('Chapter 12 contains one unresolved promise.')).toBeInTheDocument()
  expect(screen.getByText(/2 supporting story references/)).toBeInTheDocument()
  fireEvent.click(screen.getByTestId('assistant-navigation-action'))
  expect(onNavigate).toHaveBeenCalledWith('drafting', expect.objectContaining({ chapter_number: 12 }))
})


test('shows the enforced character awareness boundary', async () => {
  renderStudio()
  fireEvent.click(screen.getByTestId('interactive-tab-characters'))
  await waitFor(() => expect(screen.getByLabelText('Conversation character')).toHaveValue('Mara Venn'))
  fireEvent.change(screen.getByLabelText('Conversation timeline chapter'), { target: { value: '20' } })
  fireEvent.change(screen.getByLabelText('Message character'), { target: { value: 'What do you know?' } })
  fireEvent.click(screen.getByTestId('send-character-message'))
  expect(await screen.findByText('Only what I learned before the bell fell silent.')).toBeInTheDocument()
  expect(screen.getByText('Chapter 3 awareness')).toBeInTheDocument()
  expect(screen.getByText('Death boundary enforced')).toBeInTheDocument()
})


test('explores graph evidence, reviews canon proposals, and explains recommendations', async () => {
  renderStudio()
  fireEvent.click(screen.getByTestId('interactive-tab-graph'))
  expect(await screen.findByText(/1 story elements · 0 relationships/)).toBeInTheDocument()
  fireEvent.click(screen.getByLabelText('character: Mara Venn'))
  expect(await screen.findByTestId('knowledge-graph-inspector')).toHaveTextContent('Mara Venn')

  fireEvent.click(screen.getByTestId('interactive-tab-proposals'))
  expect(screen.getByText('Seal — material')).toBeInTheDocument()
  fireEvent.click(screen.getByTestId('approve-canon-proposal'))
  await waitFor(() => expect(dataApi.reviewCanonProposal).toHaveBeenCalledWith('project-1', 'proposal-1', expect.objectContaining({ decision: 'approved' })))

  fireEvent.click(screen.getByTestId('interactive-tab-intelligence'))
  fireEvent.click(screen.getByRole('button', { name: 'Why was this generated?' }))
  expect(await screen.findByTestId('explainability-panel')).toHaveTextContent('The shared graph has no later presence.')
})
