import axios from 'axios'
import type {
  BeginnerFlow,
  EditableDecision,
  ProjectLibraryPage,
  WorkspaceBootstrap,
} from '@/types'

// The backend listens on port 8000 by default (see scripts/dev.ts and docker-compose.yml).
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    ...(process.env.NEXT_PUBLIC_NOVELFORGE_LOCAL_TOKEN
      ? { 'X-NovelForge-Token': process.env.NEXT_PUBLIC_NOVELFORGE_LOCAL_TOKEN }
      : {}),
  },
})

// Real provider work may include one schema-correction pass. Keep ordinary reads
// responsive, but do not tell the author a long-running AI action failed while
// the backend is still safely completing it.
const AI_ACTION_TIMEOUT = 240000

const workspaceBootstrapRequests = new Map<string, Promise<WorkspaceBootstrap>>()

export const projectsApi = {
  getAll: async (options?: { includeArchived?: boolean; includeTrashed?: boolean }) => {
    const response = options
      ? await api.get('/api/projects', {
          params: {
            include_archived: options.includeArchived || undefined,
            include_trashed: options.includeTrashed || undefined,
          },
        })
      : await api.get('/api/projects')
    return response.data
  },
  getById: async (id: string) => {
    const response = await api.get(`/api/projects/${id}`)
    return response.data
  },
  create: async (data: any) => {
    const response = await api.post('/api/projects', data)
    return response.data
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/api/projects/${id}`, data)
    return response.data
  },
  deleteProject: async (id: string) => {
    const response = await api.post(`/api/projects/${id}/trash`)
    return response.data
  },
  delete: async (id: string) => {
    const response = await api.delete(`/api/projects/${id}`)
    return response.data
  },
  archive: async (id: string) => {
    const response = await api.post(`/api/projects/${id}/archive`)
    return response.data
  },
  unarchive: async (id: string) => {
    const response = await api.post(`/api/projects/${id}/unarchive`)
    return response.data
  },
  restore: async (id: string) => {
    const response = await api.post(`/api/projects/${id}/restore`)
    return response.data
  },
  purge: async (id: string, confirmationTitle: string) => {
    const response = await api.delete(`/api/projects/${id}/purge`, {
      data: { confirmation_title: confirmationTitle },
    })
    return response.data
  },
  duplicate: async (id: string, mode: 'shell' | 'story' = 'shell') => {
    const response = await api.post(`/api/projects/${id}/duplicate`, undefined, { params: { mode } })
    return response.data
  },
  getTimeline: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/timeline`)
    return response.data
  },
  addMessage: async (projectId: string, data: any) => {
    const response = await api.post(`/api/projects/${projectId}/messages`, data)
    return response.data
  },
  deleteMessage: async (messageId: string) => {
    const response = await api.delete(`/api/messages/${messageId}`)
    return response.data
  },
  getWorkspaceContext: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/workspace-context`)
    return response.data
  },
}

export const rc6Api = {
  getBeginnerFlow: async (projectId: string): Promise<BeginnerFlow> => {
    const response = await api.get(`/api/projects/${projectId}/beginner-flow`)
    return response.data
  },
  updateBeginnerStep: async (
    projectId: string,
    stepId: string,
    data: {
      action: 'save' | 'skip' | 'reopen'
      title?: string
      details?: string
      source_mode?: 'manual' | 'ai' | 'import'
    },
  ): Promise<BeginnerFlow> => {
    const response = await api.put(`/api/projects/${projectId}/beginner-flow/${stepId}`, data)
    return response.data
  },
  createWorkspaceEntry: async (
    projectId: string,
    data: {
      area: 'character' | 'world' | 'timeline' | 'power' | 'relationship' | 'theme' | 'plot_thread' | 'arc' | 'mystery' | 'faction' | 'scene'
      title: string
      details: string
      source_mode: 'manual' | 'ai' | 'import'
    },
  ) => {
    const response = await api.post(`/api/projects/${projectId}/workspace-entries`, data)
    return response.data
  },
  getDecisions: async (projectId: string): Promise<{ project_id: string; decisions: EditableDecision[] }> => {
    const response = await api.get(`/api/projects/${projectId}/decisions`)
    return response.data
  },
  previewDecisionImpact: async (projectId: string, questionId: string): Promise<EditableDecision> => {
    const response = await api.get(`/api/projects/${projectId}/decisions/${questionId}/impact`)
    return response.data
  },
  changeDecision: async (
    projectId: string,
    questionId: string,
    data: { answer: string; reason?: string },
  ): Promise<EditableDecision> => {
    const response = await api.put(`/api/projects/${projectId}/decisions/${questionId}`, data)
    return response.data
  },
  undoDecision: async (
    projectId: string,
    questionId: string,
    reason = '',
  ): Promise<EditableDecision> => {
    const response = await api.post(`/api/projects/${projectId}/decisions/${questionId}/undo`, { reason })
    return response.data
  },
  reopenDecision: async (
    projectId: string,
    questionId: string,
    reason = '',
  ): Promise<EditableDecision> => {
    const response = await api.post(`/api/projects/${projectId}/decisions/${questionId}/reopen`, { reason })
    return response.data
  },
  getWorkspaceBootstrap: async (projectId: string): Promise<WorkspaceBootstrap> => {
    const existing = workspaceBootstrapRequests.get(projectId)
    if (existing) return existing
    const request = api
      .get(`/api/projects/${projectId}/workspace-bootstrap`)
      .then((response) => response.data as WorkspaceBootstrap)
      .finally(() => workspaceBootstrapRequests.delete(projectId))
    workspaceBootstrapRequests.set(projectId, request)
    return request
  },
  getProjectLibrary: async (params: {
    status?: 'active' | 'archived' | 'trashed' | 'all'
    search?: string
    page?: number
    page_size?: number
    favorites_only?: boolean
  }): Promise<ProjectLibraryPage> => {
    const response = await api.get('/api/project-library', { params })
    return response.data
  },
  setFavorite: async (projectId: string, favorite: boolean) => {
    const response = await api.put(`/api/project-library/${projectId}/favorite`, { favorite })
    return response.data
  },
  touchProject: async (projectId: string) => {
    const response = await api.post(`/api/project-library/${projectId}/touch`)
    return response.data
  },
}

export const workflowApi = {
  run: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/run`)
    return response.data
  },
  runCycle: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/cycle`)
    return response.data
  },
  getRuns: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/runs`)
    return response.data
  },
  getRun: async (projectId: string, runId: string) => {
    const response = await api.get(`/api/projects/${projectId}/runs/${runId}`)
    return response.data
  },
  getCycles: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/cycles`)
    return response.data
  },
  submitAnswer: async (projectId: string, data: any) => {
    const response = await api.post(`/api/projects/${projectId}/answers`, data)
    return response.data
  },
  getOutputs: async (projectId: string, runId?: string) => {
    const response = await api.get(`/api/projects/${projectId}/outputs`, { params: { run_id: runId } })
    return response.data
  },
}

export const dataApi = {
  getOutline: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/outline`)
    return response.data
  },
  getCharacters: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/characters`)
    return response.data
  },
  getWorld: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/world`)
    return response.data
  },
  getQuestions: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/questions`)
    return response.data
  },
  getDiscussion: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/discussion`)
    return response.data
  },
  recordDiscussionDecision: async (projectId: string, messageId: string, data: any) => {
    const response = await api.post(`/api/projects/${projectId}/discussion/${messageId}/decision`, data)
    return response.data
  },
  getStoryVision: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/story-vision`)
    return response.data
  },
  updateStoryVision: async (projectId: string, data: Record<string, unknown>) => {
    const response = await api.put(`/api/projects/${projectId}/story-vision`, data)
    return response.data
  },
  getStoryBible: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/story-bible`)
    return response.data
  },
  getStoryHealth: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/story-health`)
    return response.data
  },
  getNarrativeCritique: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/narrative-critique`)
    return response.data
  },
  refreshNarrativeCritique: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/narrative-critique/refresh`, {})
    return response.data
  },
  getNarrativeCompleteness: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/narrative-completeness`)
    return response.data
  },
  getNovelCreationGuide: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/novel-creation-guide`)
    return response.data
  },
  getWorkspaceCompanion: async (projectId: string, activeSurface = '') => {
    const response = await api.get(`/api/projects/${projectId}/workspace-companion`, {
      params: { active_surface: activeSurface },
    })
    return response.data
  },
  updateWorkspaceCompanionMessage: async (projectId: string, messageId: string, data: { read?: boolean; dismissed?: boolean; completed?: boolean; snooze_hours?: number }) => {
    const response = await api.put(`/api/projects/${projectId}/workspace-companion/messages/${messageId}`, data)
    return response.data
  },
  markWorkspaceCompanionRead: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/workspace-companion/read`)
    return response.data
  },
  getApplicationKnowledge: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/application-knowledge`)
    return response.data
  },
  getApplicationSurface: async (projectId: string, surfaceId: string) => {
    const response = await api.get(`/api/projects/${projectId}/application-knowledge/${encodeURIComponent(surfaceId)}`)
    return response.data
  },
  getProjectTimeline: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/project-timeline`)
    return response.data
  },
  getExplainabilityTimeline: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/explainability-timeline`)
    return response.data
  },
  getCanonExplorer: async (projectId: string, params?: { search?: string; canon_type?: string; active?: boolean }) => {
    const response = await api.get(`/api/projects/${projectId}/canon-explorer`, { params })
    return response.data
  },
  getCanonExplorerDetail: async (projectId: string, canonId: string) => {
    const response = await api.get(`/api/projects/${projectId}/canon-explorer/${encodeURIComponent(canonId)}`)
    return response.data
  },
  proposeCanonExplorerEdit: async (projectId: string, canonId: string, data: Record<string, unknown>) => {
    const response = await api.post(`/api/projects/${projectId}/canon-explorer/${encodeURIComponent(canonId)}/propose-edit`, data)
    return response.data
  },
  getAssistantModes: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/interactive/modes`)
    return response.data
  },
  askProjectAssistant: async (projectId: string, query: string, mode: string, activeSurface = 'dashboard', intent?: 'narrative_creation', requestId?: string) => {
    const response = await api.post(`/api/projects/${projectId}/assistant`, { query, mode, active_surface: activeSurface, intent, request_id: requestId }, { timeout: AI_ACTION_TIMEOUT })
    return response.data
  },
  storyStudio: async (projectId: string, data: {
    query: string
    mode?: string
    active_surface?: string
    target?: Record<string, unknown>
    request_id?: string
    allow_mutations?: boolean
    model_preference?: string
    model_scope?: 'message' | 'conversation'
  }) => {
    const response = await api.post(`/api/projects/${projectId}/story-studio`, data, { timeout: AI_ACTION_TIMEOUT })
    return response.data
  },
  getStoryStudioJobs: async (projectId: string, limit = 25) => {
    const response = await api.get(`/api/projects/${projectId}/story-studio/jobs`, { params: { limit } })
    return response.data
  },
  getAssistantHistory: async (projectId: string, limit = 50) => {
    const response = await api.get(`/api/projects/${projectId}/assistant/history`, { params: { limit } })
    return response.data
  },
  converseWithCharacter: async (
    projectId: string,
    data: { character_name: string; message: string; chapter_number?: number; conversation_id?: string },
  ) => {
    const response = await api.post(`/api/projects/${projectId}/character-conversations`, data)
    return response.data
  },
  getCharacterConversationHistory: async (projectId: string, characterName: string) => {
    const response = await api.get(`/api/projects/${projectId}/character-conversations/${encodeURIComponent(characterName)}`)
    return response.data
  },
  getKnowledgeGraph: async (projectId: string, kind?: string, search = '') => {
    const response = await api.get(`/api/projects/${projectId}/knowledge-graph`, {
      params: { kind: kind || undefined, search: search || undefined },
    })
    return response.data
  },
  getKnowledgeGraphNode: async (projectId: string, nodeId: string) => {
    const response = await api.get(`/api/projects/${projectId}/knowledge-graph/nodes/${encodeURIComponent(nodeId)}`)
    return response.data
  },
  explainNarrativeFinding: async (projectId: string, findingId: string) => {
    const response = await api.get(`/api/projects/${projectId}/narrative-findings/${findingId}/explanation`)
    return response.data
  },
  getWorkspaceIntelligence: async (
    projectId: string,
    data: { surface: string; chapter_number?: number; scene_id?: string; character_name?: string },
  ) => {
    const response = await api.post(`/api/projects/${projectId}/workspace-intelligence`, data)
    return response.data
  },
  getCanonProposals: async (projectId: string, status?: string) => {
    const response = await api.get(`/api/projects/${projectId}/canon/proposals`, { params: { status } })
    return response.data
  },
  createCanonProposal: async (projectId: string, data: Record<string, unknown>) => {
    const response = await api.post(`/api/projects/${projectId}/canon/proposals`, data)
    return response.data
  },
  reviewCanonProposal: async (
    projectId: string,
    proposalId: string,
    data: { decision: 'approved' | 'rejected'; note?: string; confirm_high_impact?: boolean },
  ) => {
    const response = await api.put(`/api/projects/${projectId}/canon/proposals/${proposalId}`, data)
    return response.data
  },
  runStoryAudit: async (projectId: string, includeAgent = true) => {
    const response = await api.post(`/api/projects/${projectId}/story-audit`, {
      include_agent: includeAgent,
    }, { timeout: AI_ACTION_TIMEOUT })
    return response.data
  },
  previewChangeImpact: async (
    projectId: string,
    data: Record<string, unknown>,
  ) => {
    const response = await api.post(`/api/projects/${projectId}/change-impact`, data)
    return response.data
  },
  updateChangeImpactStatus: async (
    projectId: string,
    impactId: string,
    status: 'approved' | 'rejected',
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/change-impacts/${impactId}/status`,
      { status },
    )
    return response.data
  },
  getArcs: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/arcs`)
    return response.data
  },
  getPowerSystem: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/power-system`)
    return response.data
  },
  getCharacterJourneys: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/character-journeys`)
    return response.data
  },
  getMysteries: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/mysteries`)
    return response.data
  },
  getAIInsights: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/ai-insights`)
    return response.data
  },
  getFactions: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/factions`)
    return response.data
  },
  getCharacterBibles: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/character-bibles`)
    return response.data
  },
  getStoryKnowledgeCandidates: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/story-knowledge/candidates`)
    return response.data
  },
  reextractDiscoveryKnowledge: async (projectId: string, draftId: string) => {
    const response = await api.post(`/api/projects/${projectId}/discovery-writing/extractions/${draftId}/reextract`)
    return response.data
  },
  decideStoryKnowledgeCandidate: async (projectId: string, candidateId: string, decision: 'confirm' | 'reject') => {
    const response = await api.post(`/api/projects/${projectId}/story-knowledge/candidates/${candidateId}/decision`, { decision })
    return response.data
  },
  reprojectStoryKnowledge: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/story-knowledge/reproject`)
    return response.data
  },
  getNarrativeWorld: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/world-bible`)
    return response.data
  },
  getPlotThreads: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/plot-threads`)
    return response.data
  },
  getThemes: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/themes`)
    return response.data
  },
  getForeshadowing: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/foreshadowing`)
    return response.data
  },
  getScenes: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scenes`)
    return response.data
  },
  getSceneDrafts: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scene-drafts`)
    return response.data
  },
  getChapterDrafts: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/chapter-drafts`)
    return response.data
  },
  getWritingState: async (projectId: string, signal?: AbortSignal) => {
    const response = await api.get(`/api/projects/${projectId}/writing-state`, { signal })
    return response.data
  },
  getChapterContext: async (projectId: string, chapterNumber: number) => {
    const response = await api.get(`/api/projects/${projectId}/writing-state/chapters/${chapterNumber}/context`)
    return response.data
  },
  compareChapterVersions: async (projectId: string, chapterNumber: number) => {
    const response = await api.get(`/api/projects/${projectId}/writing-state/chapters/${chapterNumber}/compare`)
    return response.data
  },
  getWritingActivity: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/writing-activity`)
    return response.data
  },
  getDraftReviewQueue: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/draft-review-queue`)
    return response.data
  },
  getWritingDashboard: async (projectId: string, signal?: AbortSignal) => {
    const response = await api.get(`/api/projects/${projectId}/writing-dashboard`, { signal })
    return response.data
  },
  generateSceneDraft: async (
    projectId: string,
    sceneId: string,
    options: {
      changeReason?: string
      operation?: string
      allowExploratory?: boolean
      requestId?: string
    } = {},
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/scene-plans/${sceneId}/generate-draft`,
      {
        change_reason: options.changeReason || '',
        operation: options.operation || 'generate',
        allow_exploratory: Boolean(options.allowExploratory),
        request_id: options.requestId || crypto.randomUUID(),
      },
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  generateChapterDraft: async (projectId: string, chapterPlanId: string, changeReason = '', wordRange?: { minimum?: number; target?: number; maximum?: number }) => {
    const response = await api.post(
      `/api/projects/${projectId}/chapter-plans/${chapterPlanId}/generate-draft`,
      { change_reason: changeReason, word_range: wordRange },
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  generateDiscoveryWriting: async (projectId: string, data: {
    instruction: string
    minimum?: number
    target?: number
    maximum?: number
    chapter_number?: number
  }) => {
    const response = await api.post(`/api/projects/${projectId}/discovery-writing`, {
      instruction: data.instruction,
      target_word_min: data.minimum,
      target_word_count: data.target,
      target_word_max: data.maximum,
      chapter_number: data.chapter_number,
    }, { timeout: AI_ACTION_TIMEOUT })
    return response.data
  },
  getDiscoveryExtractions: async (projectId: string, limit = 100) => {
    const response = await api.get(`/api/projects/${projectId}/discovery-writing/extractions`, { params: { limit } })
    return response.data
  },
  updateDraftStatus: async (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
    status: string,
    reason = '',
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/${draftType}-drafts/${draftId}/status`,
      { status, reason },
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  editChapterContent: async (projectId: string, draftId: string, editedText: string, reason = 'Author edited chapter prose') => {
    const response = await api.put(
      `/api/projects/${projectId}/chapter-drafts/${draftId}/content`,
      { edited_text: editedText, reason },
    )
    return response.data
  },
  regenerateDraft: async (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
    changeReason: string,
    operation = 'rewrite',
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/${draftType}-drafts/${draftId}/regenerate`,
      {
        change_reason: changeReason,
        operation,
        request_id: crypto.randomUUID(),
      },
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  rollbackDraft: async (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/${draftType}-drafts/${draftId}/rollback`,
    )
    return response.data
  },
  setSceneDraftFavorite: async (
    projectId: string,
    draftId: string,
    favorite: boolean,
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/scene-drafts/${draftId}/favorite`,
      { favorite },
    )
    return response.data
  },
  compareSceneDrafts: async (
    projectId: string,
    leftDraftId: string,
    rightDraftId: string,
  ) => {
    const response = await api.get(`/api/projects/${projectId}/scene-drafts/compare`, {
      params: { left_draft_id: leftDraftId, right_draft_id: rightDraftId },
    })
    return response.data
  },
  createWritersRoom: async (
    projectId: string,
    draftId: string,
    instruction = '',
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/scene-drafts/${draftId}/writers-room`,
      {
        directions: ['emotion', 'action', 'mystery'],
        instruction,
        request_id: crypto.randomUUID(),
      },
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  mergeSceneDrafts: async (
    projectId: string,
    leftDraftId: string,
    rightDraftId: string,
    mergedText: string,
  ) => {
    const response = await api.post(`/api/projects/${projectId}/scene-drafts/merge`, {
      left_draft_id: leftDraftId,
      right_draft_id: rightDraftId,
      merged_text: mergedText,
      reason: 'Author merged preferred elements after side-by-side comparison.',
    })
    return response.data
  },
  requestEditorialReview: async (
    projectId: string,
    subjectType: 'scene' | 'chapter' | 'arc',
    subjectId: string,
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/editorial/review/${subjectType}/${subjectId}`,
      {},
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  requestDialogueReview: async (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/editorial/dialogue/${draftType}/${draftId}`,
      {},
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  getEditorialDashboard: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/editorial/dashboard`)
    return response.data
  },
  createRevisionBranch: async (
    projectId: string,
    data: Record<string, unknown>,
  ) => {
    const response = await api.post(`/api/projects/${projectId}/revision-branches`, data)
    return response.data
  },
  createSelectionRevision: async (projectId: string, draftId: string, selectedText: string, instruction: string) => {
    const response = await api.post(`/api/projects/${projectId}/chapter-drafts/${draftId}/selection-revision`, {
      selected_text: selectedText,
      instruction,
    }, { timeout: AI_ACTION_TIMEOUT })
    return response.data
  },
  generateRevision: async (
    projectId: string,
    branchId: string,
    changeReason: string,
    revisionPass = 'development',
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/revision-branches/${branchId}/generate`,
      {
        change_reason: changeReason,
        revision_pass: revisionPass,
        request_id: crypto.randomUUID(),
      },
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  updateRevisionBranchStatus: async (
    projectId: string,
    branchId: string,
    status: string,
    reason = '',
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/revision-branches/${branchId}/status`,
      { status, reason },
    )
    return response.data
  },
  compareRevision: async (projectId: string, branchId: string) => {
    const response = await api.get(
      `/api/projects/${projectId}/revision-branches/${branchId}/compare`,
    )
    return response.data
  },
  applyRevision: async (projectId: string, branchId: string) => {
    const response = await api.post(
      `/api/projects/${projectId}/revision-branches/${branchId}/apply`,
      {},
    )
    return response.data
  },
  createManuscript: async (projectId: string, title = '') => {
    const response = await api.post(`/api/projects/${projectId}/manuscripts`, { title })
    return response.data
  },
  assembleManuscript: async (
    projectId: string,
    manuscriptId: string,
    chapterDraftIds: string[] = [],
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/manuscripts/${manuscriptId}/assemble`,
      { chapter_draft_ids: chapterDraftIds },
    )
    return response.data
  },
  reviewManuscript: async (projectId: string, manuscriptId: string) => {
    const response = await api.post(
      `/api/projects/${projectId}/manuscripts/${manuscriptId}/review`,
      {},
      { timeout: AI_ACTION_TIMEOUT },
    )
    return response.data
  },
  updateManuscriptStatus: async (
    projectId: string,
    manuscriptId: string,
    status: string,
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/manuscripts/${manuscriptId}/status`,
      { status },
    )
    return response.data
  },
  rollbackManuscript: async (
    projectId: string,
    manuscriptId: string,
    versionId: string,
  ) => {
    const response = await api.post(
      `/api/projects/${projectId}/manuscripts/${manuscriptId}/rollback/${versionId}`,
    )
    return response.data
  },
  getPublicationPreflight: async (projectId: string, manuscriptId: string) => {
    const response = await api.get(
      `/api/projects/${projectId}/manuscripts/${manuscriptId}/publication-preflight`,
    )
    return response.data
  },
  createPublicationExport: async (projectId: string, manuscriptId: string) => {
    const response = await api.post(
      `/api/projects/${projectId}/manuscripts/${manuscriptId}/publication-exports`,
    )
    return response.data
  },
  downloadPublicationExport: async (projectId: string, exportId: string, kind: string) => {
    const response = await api.get(
      `/api/projects/${projectId}/publication-exports/${exportId}/${kind}`,
      { responseType: 'blob' },
    )
    return response.data as Blob
  },
  validateCanon: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/canon/validate`)
    return response.data
  },
  reviewCanon: async (projectId: string) => {
    const response = await api.post(`/api/projects/${projectId}/canon/review`)
    return response.data
  },
  updateCanonConflictStatus: async (
    projectId: string,
    conflictId: string,
    status: string,
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/canon/conflicts/${conflictId}/status`,
      { status },
    )
    return response.data
  },
  updateCanonRecordActive: async (
    projectId: string,
    canonId: string,
    active: boolean,
  ) => {
    const response = await api.put(
      `/api/projects/${projectId}/canon/registry/${canonId}/active`,
      { active },
    )
    return response.data
  },
  draftScenes: async (projectId: string, arcId: string) => {
    const response = await api.post(`/api/projects/${projectId}/draft-scenes`, { arc_id: arcId })
    return response.data
  },
  getReadinessReport: async (projectId: string, arcId?: string) => {
    const response = await api.get(`/api/projects/${projectId}/readiness/report`, { params: { arc_id: arcId } })
    return response.data
  },
  getTimelineV2: async (projectId: string, arcId?: string) => {
    const response = await api.get(`/api/projects/${projectId}/timeline-v2`, { params: { arc_id: arcId } })
    return response.data
  },
  getKnowledge: async (projectId: string, knowledgeType?: string) => {
    const response = await api.get(`/api/projects/${projectId}/knowledge`, { params: { knowledge_type: knowledgeType } })
    return response.data
  },
  getArcDevelopment: async (projectId: string, arcId: string) => {
    const response = await api.get(`/api/projects/${projectId}/arcs/${arcId}/development`)
    return response.data
  },
  activateArc: async (projectId: string, arcId: string) => {
    const response = await api.post(`/api/projects/${projectId}/arcs/${arcId}/activate`)
    return response.data
  },
  updateArcChecklist: async (projectId: string, itemId: string, data: Record<string, unknown>) => {
    const response = await api.put(`/api/projects/${projectId}/arc-checklists/${itemId}`, data)
    return response.data
  },
  updatePlanningStatus: async (
    projectId: string,
    planType: 'scene' | 'chapter',
    planId: string,
    status: string,
  ) => {
    const path = planType === 'scene'
      ? `scene-plans-v2/${planId}`
      : `chapter-plans/${planId}`
    const response = await api.put(`/api/projects/${projectId}/${path}`, { status })
    return response.data
  },
  getStoryRoom: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/story-room`)
    return response.data
  },
  getRelationships: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/relationships`)
    return response.data
  },
  getContinuity: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/continuity`)
    return response.data
  },
  searchMemory: async (projectId: string, q: string, topK = 10) => {
    const response = await api.get(`/api/projects/${projectId}/memory/search`, { params: { q, top_k: topK } })
    return response.data
  },
  getLatestOrchestration: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/orchestration/latest`)
    return response.data
  },
  getOrchestrationHistory: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/orchestration/history`)
    return response.data
  },
  getLatestContext: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/context/latest`)
    return response.data
  },
  getObservability: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/observability/latest`)
    return response.data
  },
  getCognition: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/cognition`)
    return response.data
  },
  getSceneParagraphs: async (projectId: string, sceneId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs`)
    return response.data
  },
  /**
   * Fetch the authoritative prose content document for the Tiptap editor.
   *
   * Returns `paragraph_content` if it exists, or a synthesised fallback from
   * the skeleton's `prose` field so the editor is never blank on first open.
   */
  getParagraphContent: async (projectId: string, sceneId: string, paragraphId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/content`)
    return response.data
  },

  generateSceneParagraphs: async (projectId: string, sceneId: string, changeReason = '') => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/generate`, { change_reason: changeReason })
    return response.data
  },
  updateParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string, updates: Record<string, unknown>, changeReason = '', createVersion = false) => {
    const response = await api.put(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}`, { updates, change_reason: changeReason, create_version: createVersion })
    return response.data
  },
  reorderParagraphSkeletons: async (projectId: string, sceneId: string, reorderPayload: { paragraph_id: string; order: number }[]) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/reorder`, { reorder_payload: reorderPayload })
    return response.data
  },
  lockParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string, isLocked: boolean) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/lock`, { is_locked: isLocked })
    return response.data
  },
  deleteParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string) => {
    const response = await api.delete(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}`)
    return response.data
  },
  duplicateParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/duplicate`)
    return response.data
  },
  approveParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string, approvalState: string) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/approve`, { approval_state: approvalState })
    return response.data
  },
  regenerateParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string, changeReason = '') => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/regenerate`, { change_reason: changeReason })
    return response.data
  },
  getParagraphHistory: async (projectId: string, sceneId: string, paragraphId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/history`)
    return response.data
  },
  restoreParagraphVersion: async (projectId: string, sceneId: string, paragraphId: string, versionId: string) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/restore/${versionId}`)
    return response.data
  },
  getParagraphSuggestions: async (projectId: string, sceneId: string, paragraphId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/suggestions`)
    return response.data
  },
  acceptParagraphSuggestion: async (projectId: string, sceneId: string, paragraphId: string, suggestionId: string) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/suggestions/${suggestionId}/accept`)
    return response.data
  },
  rejectParagraphSuggestion: async (projectId: string, sceneId: string, paragraphId: string, suggestionId: string) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/suggestions/${suggestionId}/reject`)
    return response.data
  },
  aiEditParagraph: async (projectId: string, sceneId: string, paragraphId: string, mode: string, prompt: string) => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/ai-edit`, { mode, prompt })
    return response.data
  },
  getParagraphComments: async (projectId: string, sceneId: string, paragraphId: string) => {
    const response = await api.get(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/comments`)
    return response.data
  },
  addParagraphComment: async (projectId: string, sceneId: string, paragraphId: string, content: string, author = 'Author') => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/comments`, { content, author })
    return response.data
  },
  replyParagraphComment: async (projectId: string, sceneId: string, paragraphId: string, commentId: string, content: string, author = 'Author') => {
    const response = await api.post(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/comments/${commentId}/reply`, { content, author })
    return response.data
  },
  resolveParagraphComment: async (projectId: string, sceneId: string, paragraphId: string, commentId: string) => {
    const response = await api.put(`/api/projects/${projectId}/scenes/${sceneId}/paragraphs/${paragraphId}/comments/${commentId}/resolve`)
    return response.data
  },
}

export const projectEventUrl = (projectId: string) => `${API_BASE}/api/projects/${projectId}/stream`

export const settingsApi = {
  get: async () => {
    const response = await api.get('/api/settings/ai')
    return response.data
  },
  update: async (data: any) => {
    const response = await api.put('/api/settings/ai', data)
    return response.data
  },
  test: async (provider: string, settings?: any) => {
    const response = await api.post(`/api/settings/ai/test/${provider}`, settings)
    return response.data
  },
  getExecution: async () => {
    const response = await api.get('/api/settings/execution')
    return response.data
  },
  updateExecution: async (data: any) => {
    const response = await api.put('/api/settings/execution', data)
    return response.data
  },
  getAgentAssignments: async () => {
    const response = await api.get('/api/settings/agents')
    return response.data
  },
  updateAgentAssignments: async (data: any) => {
    const response = await api.put('/api/settings/agents', data)
    return response.data
  },
  applyPreset: async (preset: string) => {
    const response = await api.post(`/api/settings/presets/${preset}`)
    return response.data
  },
  testModel: async (data: any) => {
    const response = await api.post('/api/ai/test-model', data)
    return response.data
  },
  getModels: async (provider?: string, refresh = false, verifiedOnly = false) => {
    const response = await api.get('/api/settings/models', { params: { provider, refresh, verified_only: verifiedOnly } })
    return response.data
  },
  getModelValidations: async (provider?: string) => {
    const response = await api.get('/api/settings/model-validations', { params: { provider } })
    return response.data
  },
  validateModels: async (provider: string) => {
    const response = await api.post('/api/settings/validate-models', { provider })
    return response.data
  },
  validateProvider: async (provider: string, apiKey?: string) => {
    const response = await api.post(`/api/settings/providers/${provider}/validate`, { api_key: apiKey })
    return response.data
  },
  discoverModels: async (provider: string, apiKey?: string) => {
    const response = await api.post(`/api/settings/providers/${provider}/discover`, { api_key: apiKey })
    return response.data
  },
  getExecutionTraces: async (limit = 50) => {
    const response = await api.get('/api/settings/execution-traces', { params: { limit } })
    return response.data
  },
  runAIWorkflowTest: async (provider: string, model: string) => {
    const response = await api.post('/api/settings/run-ai-workflow-test', { provider, model })
    return response.data
  },
  runFullWorkflowTest: async (provider: string, model: string) => {
    const response = await api.post('/api/settings/run-full-workflow-test', { provider, model })
    return response.data
  },
  getHealth: async () => {
    const response = await api.get('/api/settings/health')
    return response.data
  },
  getRecommendation: async (params: any) => {
    const response = await api.get('/api/settings/recommendations', { params })
    return response.data
  },
  getMemory: async () => {
    const response = await api.get('/api/settings/memory')
    return response.data
  },
  updateMemory: async (data: any) => {
    const response = await api.put('/api/settings/memory', data)
    return response.data
  },
  testMemory: async () => {
    const response = await api.post('/api/settings/memory/test')
    return response.data
  },
  smokeTestMemory: async () => {
    const response = await api.post('/api/settings/memory/smoke-test')
    return response.data
  },
}

export const operationsApi = {
  getReadiness: async () => {
    const response = await api.get('/api/operations/readiness')
    return response.data
  },
  getPrivacy: async () => {
    const response = await api.get('/api/operations/privacy')
    return response.data
  },
  createSupportBundle: async () => {
    const response = await api.post('/api/operations/support-bundles')
    return response.data
  },
  downloadSupportBundle: async (supportId: string) => {
    const response = await api.get(`/api/operations/support-bundles/${supportId}/download`, { responseType: 'blob' })
    return response.data as Blob
  },
  submitFeedback: async (data: { category: string; message: string; include_diagnostics: boolean; include_story_content?: boolean }) => {
    const response = await api.post('/api/operations/feedback', data)
    return response.data
  },
  createAllBackups: async (reason = 'all-project author backup') => {
    const response = await api.post('/api/operations/backups', { reason })
    return response.data
  },
  listBackups: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/backups`)
    return response.data
  },
  createBackup: async (projectId: string, reason = 'manual') => {
    const response = await api.post(`/api/projects/${projectId}/backups`, { reason }, { timeout: 180000 })
    return response.data
  },
  validateBackup: async (backupId: string) => {
    const response = await api.post(`/api/backups/${backupId}/validate`)
    return response.data
  },
  importBackup: async (file: File) => {
    const response = await api.post('/api/backups/import', file, {
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-NovelForge-Filename': file.name,
      },
    })
    return response.data
  },
  restoreBackup: async (backupId: string, title = '', requestId = '') => {
    const response = await api.post(
      `/api/backups/${backupId}/restore`,
      { title, request_id: requestId },
      { timeout: 180000 },
    )
    return response.data
  },
  downloadBackup: async (backupId: string) => {
    const response = await api.get(`/api/backups/${backupId}/download`, { responseType: 'blob' })
    return response.data as Blob
  },
}

export default api
