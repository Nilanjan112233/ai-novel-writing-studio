import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useProjectStore } from './projectStore'

// Mock the API modules
vi.mock('@/lib/api', () => ({
  projectsApi: {
    getAll: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    deleteProject: vi.fn(),
    archive: vi.fn(),
    duplicate: vi.fn(),
  },
  workflowApi: {
    run: vi.fn(),
    getRuns: vi.fn(),
    getOutputs: vi.fn(),
    submitAnswer: vi.fn(),
  },
  dataApi: {
    getStoryBible: vi.fn(),
    getStoryHealth: vi.fn().mockResolvedValue(null),
    updateStoryVision: vi.fn(),
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
    draftScenes: vi.fn(),
    runStoryAudit: vi.fn(),
    previewChangeImpact: vi.fn(),
    updateChangeImpactStatus: vi.fn(),
    generateSceneDraft: vi.fn(),
    mergeSceneDrafts: vi.fn(),
    updateRevisionBranchStatus: vi.fn(),
    assembleManuscript: vi.fn(),
  },
}))

describe('projectStore - New Project Form State', () => {
  beforeEach(() => {
    // Reset the store before each test
    useProjectStore.setState({
      newProjectTitle: '',
      newProjectPremise: '',
      newProjectGenre: '',
      newProjectTone: '',
    })
  })

  it('initializes with empty strings for new project form fields', () => {
    const state = useProjectStore.getState()
    expect(state.newProjectTitle).toBe('')
    expect(state.newProjectPremise).toBe('')
    expect(state.newProjectGenre).toBe('')
    expect(state.newProjectTone).toBe('')
  })

  it('setNewProjectTitle updates the title field', () => {
    const store = useProjectStore.getState()
    store.setNewProjectTitle('My Novel')
    expect(useProjectStore.getState().newProjectTitle).toBe('My Novel')
  })

  it('setNewProjectPremise updates the premise field', () => {
    const store = useProjectStore.getState()
    store.setNewProjectPremise('A story about adventure')
    expect(useProjectStore.getState().newProjectPremise).toBe('A story about adventure')
  })

  it('setNewProjectGenre updates the genre field', () => {
    const store = useProjectStore.getState()
    store.setNewProjectGenre('Fantasy')
    expect(useProjectStore.getState().newProjectGenre).toBe('Fantasy')
  })

  it('setNewProjectTone updates the tone field', () => {
    const store = useProjectStore.getState()
    store.setNewProjectTone('Dark')
    expect(useProjectStore.getState().newProjectTone).toBe('Dark')
  })

  it('all setters can be called in sequence', () => {
    const store = useProjectStore.getState()
    store.setNewProjectTitle('My Novel')
    store.setNewProjectPremise('A story about adventure')
    store.setNewProjectGenre('Fantasy')
    store.setNewProjectTone('Dark')

    const state = useProjectStore.getState()
    expect(state.newProjectTitle).toBe('My Novel')
    expect(state.newProjectPremise).toBe('A story about adventure')
    expect(state.newProjectGenre).toBe('Fantasy')
    expect(state.newProjectTone).toBe('Dark')
  })
})

describe('projectStore - Form Reset After Creation', () => {
  beforeEach(() => {
    // Reset the store before each test
    useProjectStore.setState({
      newProjectTitle: '',
      newProjectPremise: '',
      newProjectGenre: '',
      newProjectTone: '',
      loading: false,
      error: null,
    })
  })

  it('resets form fields after successful project creation', async () => {
    const { projectsApi } = await import('@/lib/api')
    
    // Mock successful API response (API now returns data directly, not response.data)
    vi.mocked(projectsApi.create).mockResolvedValue({
      id: '123',
      title: 'Test Novel',
      premise: 'Test premise',
      genre: 'Fantasy',
      tone: 'Dark',
      status: 'draft',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })

    vi.mocked(projectsApi.getAll).mockResolvedValue([])

    const store = useProjectStore.getState()
    
    // Set form values
    store.setNewProjectTitle('Test Novel')
    store.setNewProjectPremise('Test premise')
    store.setNewProjectGenre('Fantasy')
    store.setNewProjectTone('Dark')

    // Verify values are set
    expect(useProjectStore.getState().newProjectTitle).toBe('Test Novel')
    expect(useProjectStore.getState().newProjectPremise).toBe('Test premise')
    expect(useProjectStore.getState().newProjectGenre).toBe('Fantasy')
    expect(useProjectStore.getState().newProjectTone).toBe('Dark')

    // Create project
    await store.createProject({
      title: 'Test Novel',
      premise: 'Test premise',
      genre: 'Fantasy',
      tone: 'Dark',
    })

    // Verify values are reset
    expect(useProjectStore.getState().newProjectTitle).toBe('')
    expect(useProjectStore.getState().newProjectPremise).toBe('')
    expect(useProjectStore.getState().newProjectGenre).toBe('')
    expect(useProjectStore.getState().newProjectTone).toBe('')
  })
})

describe('projectStore - Story Intelligence refresh ordering', () => {
  it('does not erase dedicated Story Health when Story Bible has an empty legacy projection', async () => {
    const { dataApi } = await import('@/lib/api')
    const authoritativeHealth = {
      project_id: 'phase7-race-proof',
      story_health_score: 100,
      status: 'healthy',
      metrics: {},
      dimension_scores: {},
      findings: [],
    } as any
    useProjectStore.setState({ storyHealth: authoritativeHealth })
    vi.mocked(dataApi.getStoryBible).mockResolvedValue({
      project_id: 'phase7-race-proof',
      version: 1,
      sections: {
        workflow: { agents: [], runs: [], cycles: [] },
        story_intelligence: { health: {}, audits: [], change_impacts: [] },
      },
    } as any)

    await useProjectStore.getState().fetchStoryBible('phase7-race-proof')

    expect(useProjectStore.getState().storyHealth).toBe(authoritativeHealth)
  })
})

describe('projectStore - author-facing operation failures', () => {
  beforeEach(() => {
    useProjectStore.setState({ operationFailure: null, error: null })
    vi.clearAllMocks()
  })

  it('keeps a failed generation visible, safe, retryable, and dismissible', async () => {
    const { dataApi } = await import('@/lib/api')
    vi.mocked(dataApi.generateSceneDraft).mockRejectedValueOnce(
      new Error('provider timeout after validation')
    )
    await useProjectStore.getState().generateSceneDraft('project-1', 'scene-1')

    const failure = useProjectStore.getState().operationFailure
    expect(failure?.operation).toBe('Draft generation')
    expect(failure?.safety).toContain('existing prose')
    expect(failure?.safety).toContain('unchanged')
    expect(failure?.destination).toBe('drafting')
    expect(failure?.retry).toBeTypeOf('function')

    useProjectStore.getState().dismissOperationFailure()
    expect(useProjectStore.getState().operationFailure).toBeNull()
  })

  it.each([
    {
      operation: 'Draft merge',
      destination: 'drafting',
      reject: async () => {
        const { dataApi } = await import('@/lib/api')
        vi.mocked(dataApi.mergeSceneDrafts).mockRejectedValueOnce(new Error('merge conflict'))
        await useProjectStore.getState().mergeSceneDrafts('project-1', 'left', 'right', 'merged prose')
      },
    },
    {
      operation: 'Revision status change',
      destination: 'editorial',
      reject: async () => {
        const { dataApi } = await import('@/lib/api')
        vi.mocked(dataApi.updateRevisionBranchStatus).mockRejectedValueOnce(new Error('revision conflict'))
        await useProjectStore.getState().updateRevisionBranchStatus('project-1', 'branch-1', 'approved')
      },
    },
    {
      operation: 'Manuscript assembly',
      destination: 'manuscript',
      reject: async () => {
        const { dataApi } = await import('@/lib/api')
        vi.mocked(dataApi.assembleManuscript).mockRejectedValueOnce(new Error('chapter not approved'))
        await useProjectStore.getState().assembleManuscript('project-1', 'manuscript-1', ['chapter-1'])
      },
    },
  ])('keeps $operation failures visible and retryable', async ({ operation, destination, reject }) => {
    await reject()

    const failure = useProjectStore.getState().operationFailure
    expect(failure?.operation).toBe(operation)
    expect(failure?.destination).toBe(destination)
    expect(failure?.safety).toContain('unchanged')
    expect(failure?.retry).toBeTypeOf('function')
  })
})
