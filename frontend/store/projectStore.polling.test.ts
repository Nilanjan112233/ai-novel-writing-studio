import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useProjectStore, getWorkflowNodeStatus } from './projectStore'

vi.mock('@/lib/api', () => ({
  rc6Api: { getWorkspaceBootstrap: vi.fn() },
  projectsApi: { getAll: vi.fn(), create: vi.fn(), getTimeline: vi.fn(), getWorkspaceContext: vi.fn().mockResolvedValue(null), deleteProject: vi.fn(), archive: vi.fn(), duplicate: vi.fn() },
  workflowApi: {
    run: vi.fn(),
    runCycle: vi.fn(),
    getRuns: vi.fn(),
    getOutputs: vi.fn(),
    getCycles: vi.fn(),
    submitAnswer: vi.fn(),
  },
  dataApi: {
    getStoryBible: vi.fn(),
    getStoryHealth: vi.fn().mockResolvedValue(null),
    getQuestions: vi.fn(),
    getOutline: vi.fn(),
    getCharacterBibles: vi.fn(),
    getNarrativeWorld: vi.fn(),
    getPlotThreads: vi.fn(),
    getContinuity: vi.fn(),
    getScenes: vi.fn(),
    getSceneDrafts: vi.fn(),
    getRelationships: vi.fn(),
    getThemes: vi.fn(),
    getForeshadowing: vi.fn(),
    getDiscussion: vi.fn(),
    getStoryVision: vi.fn(),
    getArcs: vi.fn(),
    getPowerSystem: vi.fn(),
    getCharacterJourneys: vi.fn(),
    getMysteries: vi.fn(),
    getAIInsights: vi.fn(),
    getFactions: vi.fn(),
    getLatestOrchestration: vi.fn(),
    getLatestContext: vi.fn(),
    getCognition: vi.fn(),
    getObservability: vi.fn(),
    getStoryRoom: vi.fn().mockResolvedValue(null),
    draftScenes: vi.fn(),
    runStoryAudit: vi.fn(),
    previewChangeImpact: vi.fn(),
    updateChangeImpactStatus: vi.fn(),
  },
}))

describe('getWorkflowNodeStatus', () => {
  it('marks all nodes completed when run is completed', () => {
    const run = {
      id: '1',
      project_id: 'p1',
      status: 'completed',
      current_agent: 'completed',
      started_at: new Date().toISOString(),
    }
    expect(getWorkflowNodeStatus('narrativedirectoragent', run)).toBe('completed')
    expect(getWorkflowNodeStatus('revision', run)).toBe('completed')
  })

  it('highlights question node when waiting for user', () => {
    const run = {
      id: '1',
      project_id: 'p1',
      status: 'waiting_for_user',
      current_agent: 'question',
      started_at: new Date().toISOString(),
    }
    expect(getWorkflowNodeStatus('question', run)).toBe('waiting')
    expect(getWorkflowNodeStatus('narrativedirectoragent', run)).toBe('completed')
  })
})

describe('pollRunStatus', () => {
  afterEach(() => {
    useProjectStore.getState().stopPolling()
  })

  it('refreshes the Story Bible without starting a polling timer', async () => {
    const { dataApi, rc6Api } = await import('@/lib/api')
    vi.mocked(dataApi.getStoryBible).mockResolvedValue({
      project_id: 'p1',
      cycle_number: 1,
      version: 2,
      updated_at: new Date().toISOString(),
      sections: {
        story_vision: { project_id: 'p1', premise: 'Test', genre: 'Fantasy', themes: [], inspirations: [], narrative_goals: [] },
        characters: [],
        character_journeys: [],
        world: {},
        power_system: {},
        factions: [],
        relationships: [],
        plot_threads: [],
        themes: {},
        foreshadowing: [],
        mysteries: [],
        timeline: [],
        arcs: [],
        questions: [{ id: 'q1', project_id: 'p1', text: 'Q?', choices: ['A'], answered: false, created_at: new Date().toISOString() }],
        active_questions: [],
        resolved_questions: [],
        ai_insights: {},
        drafting: { scene_plans: [], scene_drafts: [] },
        discussion: [],
        canon_registry: [],
        decision_registry: [],
        discussion_decisions: [],
        canon: {},
        contradictions: [],
        continuity_reports: [],
        workflow: {
          cycles: [],
          runs: [{ id: 'run1', project_id: 'p1', status: 'completed', current_agent: 'completed', started_at: new Date().toISOString() }],
          agents: [{ id: 'o1', run_id: 'run1', agent_name: 'NarrativeDirectorAgent', summary: 'Done', metadata: {}, created_at: new Date().toISOString() }],
        },
      },
    })
    const storyBible = await dataApi.getStoryBible('p1')
    vi.mocked(dataApi.getQuestions).mockResolvedValue(storyBible.sections.questions)
    vi.mocked(rc6Api.getWorkspaceBootstrap).mockResolvedValue({
      project_id: 'p1',
      project: { id: 'p1', title: 'Polling project' },
      story_bible: storyBible,
      story_health: null,
      completeness: {},
      companion: {},
      version: 'rc6-v1',
      generated_at: new Date().toISOString(),
    } as never)

    useProjectStore.setState({ isRunningWorkflow: true, pollingIntervalId: null })
    useProjectStore.getState().pollRunStatus('p1')

    await vi.waitFor(
      () => {
        const state = useProjectStore.getState()
        expect(state.outputs.length).toBeGreaterThan(0)
      },
      { timeout: 5000 }
    )

    const state = useProjectStore.getState()
    expect(state.questions.length).toBeGreaterThan(0)
    expect(state.pollingIntervalId).toBeNull()
  })
})
