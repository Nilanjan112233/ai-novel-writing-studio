import { create } from 'zustand'
import axios from 'axios'
import { projectsApi, workflowApi, dataApi, projectEventUrl, rc6Api } from '@/lib/api'
import {
  Project,
  Run,
  AgentOutput,
  Question,
  Outline,
  TimelineMessage,
  Cycle,
  CharacterBible,
  NarrativeWorldBible,
  PlotThread,
  ContinuityReport,
  SceneEntry,
  SceneDraft,
  ChapterDraft,
  ParagraphSkeleton,
  RelationshipEdge,
  ThemeRegistry,
  ForeshadowEntry,
  DiscussionMessage,
  StoryVision,
  StoryArc,
  PowerSystem,
  CharacterJourney,
  MysteryRegistryEntry,
  AIInsights,
  FactionRecord,
  OrchestrationRun,
  ContextPacketRecord,
  CognitionEvent,
  ObservabilityEvent,
  StoryBible,
  ReadinessItem,
  ReadinessReport,
  TimelineEntryV2,
  CharacterProgression,
  KnowledgeEntry,
  ArtifactRegistryEntry,
  ArcChecklistItem,
  ArcDependency,
  ArcDevelopmentReport,
  ChapterPlan,
  ScenePlanV2,
  PowerProgression,
  EvolutionEvent,
  StoryRoom,
  EditorialReport,
  EditorialScore,
  RevisionBranch,
  RevisionVersion,
  RevisionComparison,
  Manuscript,
  ManuscriptVersion,
  ManuscriptReport,
  CanonRecord,
  CanonConflict,
  ChapterIntelligence,
  StoryAuditReport,
  StoryHealth,
  ChangeImpact,
  ParagraphContent,
  ParagraphSuggestion,
  ParagraphVersion,
  ParagraphComment,
} from '@/types'
import { eventBus } from '@/lib/eventBus'



const TERMINAL_STATUSES = new Set(['completed', 'waiting_for_user', 'failed', 'interrupted'])

export interface OperationFailure {
  operation: string
  explanation: string
  safety: string
  destination?: string
  technicalDetails?: string
  referenceId?: string
  occurredAt: string
  retry?: () => Promise<void>
}

function rawFailureDetail(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail ?? error.response?.data?.message
    if (typeof detail === 'string') return detail
    if (detail) return JSON.stringify(detail)
  }
  return error instanceof Error ? error.message : String(error || 'Unknown operation failure')
}

function authorFailure(
  operation: string,
  error: unknown,
  destination: string,
  retry: () => Promise<void>,
): OperationFailure {
  const technicalDetails = rawFailureDetail(error)
  const referenceId = axios.isAxiosError(error)
    ? String(error.response?.headers?.['x-novelforge-reference'] || error.response?.data?.reference_id || '') || undefined
    : undefined
  const lower = technicalDetails.toLowerCase()
  let explanation = `${operation} couldn't be completed. Please review the open checks and try again.`
  if (operation === 'Draft generation') {
    explanation = lower.includes('eligible') || lower.includes('validation')
      ? 'Draft generation is waiting for the scene’s planning and continuity checks.'
      : 'Draft generation couldn’t be completed by the writing service.'
  } else if (operation === 'Draft approval') {
    explanation = 'This draft couldn’t be approved because one or more story checks still need attention.'
  } else if (operation === 'Chapter assembly') {
    explanation = 'This chapter couldn’t be assembled because every included scene needs an approved draft.'
  } else if (operation.includes('revision') || operation === 'Editorial review') {
    explanation = `${operation} couldn’t be completed. The current draft remains available for review.`
  } else if (operation.includes('Canon')) {
    explanation = `${operation} couldn’t be completed. No official story fact was changed.`
  } else if (lower.includes('timeout') || lower.includes('network')) {
    explanation = `${operation} couldn’t reach the AI service. You can safely retry when the connection recovers.`
  }
  return {
    operation,
    explanation,
    safety: 'Your existing prose and approved story decisions are unchanged.',
    destination,
    technicalDetails,
    referenceId,
    occurredAt: new Date().toISOString(),
    retry,
  }
}

function projectStateFromStoryBible(
  storyBible: StoryBible,
  currentStoryHealth: StoryHealth | null,
): Partial<ProjectState> {
  const sections = storyBible?.sections
  if (!sections) return { storyBible }
  const workflowAgents = sections.workflow?.agents || []
  const runs = sections.workflow?.runs || []
  const cycles = sections.workflow?.cycles || []
  return {
    storyBible,
    storyVision: sections.story_vision || null,
    characterBibles: sections.characters || [],
    characterJourneys: sections.character_journeys || [],
    narrativeWorldBible: sections.world || null,
    powerSystem: sections.power_system || null,
    factions: sections.factions || [],
    relationships: sections.relationships || [],
    plotThreads: sections.plot_threads || [],
    themeRegistry: sections.themes || null,
    foreshadowing: sections.foreshadowing || [],
    mysteries: sections.mysteries || [],
    storyTimeline: sections.timeline || [],
    storyArcs: sections.arcs || [],
    readinessItems: sections.readiness?.items || [],
    readinessReports: sections.readiness?.reports || [],
    characterProgressions: sections.character_progressions || [],
    knowledgeEntries: sections.knowledge || [],
    artifactRegistry: sections.artifacts || [],
    arcChecklists: sections.arc_development?.checklists || [],
    arcDependencies: sections.arc_development?.dependencies || [],
    arcDevelopmentReports: sections.arc_development?.reports || [],
    chapterPlans: sections.drafting?.chapter_plans || [],
    powerProgressions: sections.power_progressions || [],
    knowledgeEvolutions: sections.knowledge_evolutions || [],
    artifactEvolutions: sections.artifact_evolutions || [],
    foreshadowChains: sections.foreshadow_chains || [],
    questions: sections.questions || [],
    aiInsights: sections.ai_insights || null,
    scenes: sections.drafting?.scene_plans || [],
    sceneDrafts: sections.drafting?.scene_drafts || [],
    chapterDrafts: sections.drafting?.chapter_drafts || [],
    editorialReports: sections.editorial?.reports || [],
    editorialScores: sections.editorial?.scores || [],
    revisionBranches: sections.editorial?.revision_branches || [],
    revisionVersions: sections.editorial?.revision_versions || [],
    manuscripts: sections.manuscript?.manuscripts || [],
    manuscriptVersions: sections.manuscript?.versions || [],
    manuscriptReports: sections.manuscript?.reports || [],
    canonRecords: sections.canon_governance?.registry || [],
    canonConflicts: sections.canon_governance?.conflicts || [],
    chapterIntelligence: sections.chapter_intelligence || [],
    storyAudits: sections.story_intelligence?.audits || [],
    storyHealth: typeof sections.story_intelligence?.health?.story_health_score === 'number'
      ? sections.story_intelligence.health
      : currentStoryHealth,
    changeImpacts: sections.story_intelligence?.change_impacts || [],
    discussionMessages: sections.discussion || [],
    continuityReports: sections.continuity_reports || [],
    cycles,
    runs,
    currentRun: runs[0] || null,
    orchestrationRun: sections.workflow?.latest_orchestration?.id
      ? sections.workflow.latest_orchestration
      : null,
    outputs: workflowAgents.map((item) => ({
      id: item.id,
      run_id: item.run_id,
      agent_name: item.agent_name,
      content: item.summary,
      metadata: item.metadata || {},
      created_at: item.created_at,
    })),
  }
}

const AGENT_SEQUENCE = [
  'narrativedirectoragent',
  'story_architect',
  'characterjourneyagent',
  'worldagent',
  'powersystemagent',
  'factionagent',
  'relationshipagent',
  'themeagent',
  'mysteryagent',
  'arcarchitectagent',
  'pacingagent',
  'question',
  'readinessagent',
  'knowledgeagent',
  'storydevelopmentagent',
  'sceneplanneragent',
]

export function normalizeAgentName(agent?: string): string {
  return normalizeAgent(agent)
}

function normalizeAgent(agent?: string): string {
  if (!agent) return ''
  const key = agent.toLowerCase().replace(/\s+/g, '_').replace(/_agent$/, '')
  if (key.includes('intake')) return 'intake'
  if (key.includes('brainstorm')) return 'brainstorm'
  if (key.includes('critic')) return 'critic'
  if (key.includes('arcarchitect')) return 'arcarchitectagent'
  if (key.includes('architect') || key === 'architect') return 'story_architect'
  if (key.includes('question')) return 'question'
  if (key.includes('readiness')) return 'readinessagent'
  if (key.includes('knowledge')) return 'knowledgeagent'
  if (key.includes('storydevelopment')) return 'storydevelopmentagent'
  if (key.includes('revision')) return 'revision'
  if (key.includes('narrativedirector')) return 'narrativedirectoragent'
  if (key.includes('power')) return 'powersystemagent'
  if (key.includes('mystery')) return 'mysteryagent'
  if (key.includes('theme')) return 'themeagent'
  if (key.includes('faction')) return 'factionagent'
  if (key.includes('relationship')) return 'relationshipagent'
  if (key.includes('pacing')) return 'pacingagent'
  if (key.includes('characterjourney')) return 'characterjourneyagent'
  if (key.includes('character')) return 'characteragent'
  if (key.includes('world')) return 'worldagent'
  if (key.includes('timeline')) return 'timelineagent'
  if (key.includes('continuity')) return 'continuityagent'
  if (key.includes('canon')) return 'canonagent'
  if (key.includes('review')) return 'reviewagent'
  if (key.includes('drafting')) return 'draftingagent'
  if (key.includes('sceneplanner')) return 'sceneplanneragent'
  if (key === 'completed' || key === 'failed') return key
  return key
}

export function getWorkflowNodeStatus(
  nodeId: string,
  run: Run | null
): 'pending' | 'active' | 'completed' | 'waiting' | 'failed' {
  if (!run) return 'pending'

  const current = normalizeAgent(run.current_agent)
  const idx = AGENT_SEQUENCE.indexOf(nodeId)
  const currentIdx = AGENT_SEQUENCE.indexOf(current)

  if (run.status === 'waiting_for_user' && nodeId === 'question') {
    return 'waiting'
  }

  if (run.status === 'completed' || run.current_agent === 'completed') {
    return 'completed'
  }

  if (run.status === 'failed') {
    if (current === nodeId || (current === 'failed' && idx === Math.max(currentIdx, 0))) {
      return 'failed'
    }
    return idx < Math.max(currentIdx, 0) ? 'completed' : 'pending'
  }

  if (current === nodeId || (run.status === 'running' && current === nodeId)) {
    return 'active'
  }

  if (currentIdx >= 0 && idx >= 0 && idx < currentIdx) {
    return 'completed'
  }

  if (run.status === 'completed') {
    return 'completed'
  }

  return 'pending'
}

interface ProjectState {
  projects: Project[]
  selectedProject: Project | null
  currentRun: Run | null
  runs: Run[]
  outputs: AgentOutput[]
  questions: Question[]
  outline: Outline | null
  loading: boolean
  isRunningWorkflow: boolean
  error: string | null
  operationFailure: OperationFailure | null
  pollingIntervalId: ReturnType<typeof setInterval> | null
  liveSyncIntervalId: ReturnType<typeof setInterval> | null
  projectEventSource: EventSource | null
  selectedTab: string

  newProjectTitle: string
  newProjectPremise: string
  newProjectIdeaDump: string
  newProjectGenre: string
  newProjectTone: string
  newProjectThemes: string
  newProjectInspirations: string
  newProjectCharacterNotes: string
  newProjectWorldNotes: string
  newProjectPlotNotes: string
  newProjectNotes: string

  timelineMessages: TimelineMessage[]
  cycles: Cycle[]
  characterBibles: CharacterBible[]
  narrativeWorldBible: NarrativeWorldBible | null
  plotThreads: PlotThread[]
  continuityReports: ContinuityReport[]
  scenes: ScenePlanV2[]
  sceneDrafts: SceneDraft[]
  chapterDrafts: ChapterDraft[]
  relationships: RelationshipEdge[]
  themeRegistry: ThemeRegistry | null
  foreshadowing: ForeshadowEntry[]
  discussionMessages: DiscussionMessage[]
  storyVision: StoryVision | null
  storyArcs: StoryArc[]
  powerSystem: PowerSystem | null
  characterJourneys: CharacterJourney[]
  mysteries: MysteryRegistryEntry[]
  aiInsights: AIInsights | null
  factions: FactionRecord[]
  storyBible: StoryBible | null
  storyTimeline: TimelineEntryV2[]
  readinessItems: ReadinessItem[]
  readinessReports: ReadinessReport[]
  characterProgressions: CharacterProgression[]
  knowledgeEntries: KnowledgeEntry[]
  artifactRegistry: ArtifactRegistryEntry[]
  arcChecklists: ArcChecklistItem[]
  arcDependencies: ArcDependency[]
  arcDevelopmentReports: ArcDevelopmentReport[]
  chapterPlans: ChapterPlan[]
  powerProgressions: PowerProgression[]
  knowledgeEvolutions: EvolutionEvent[]
  artifactEvolutions: EvolutionEvent[]
  foreshadowChains: EvolutionEvent[]
  storyRoom: StoryRoom | null
  editorialReports: EditorialReport[]
  editorialScores: EditorialScore[]
  revisionBranches: RevisionBranch[]
  revisionVersions: RevisionVersion[]
  revisionComparisons: Record<string, RevisionComparison>
  manuscripts: Manuscript[]
  manuscriptVersions: ManuscriptVersion[]
  manuscriptReports: ManuscriptReport[]
  canonRecords: CanonRecord[]
  canonConflicts: CanonConflict[]
  chapterIntelligence: ChapterIntelligence[]
  storyAudits: StoryAuditReport[]
  storyHealth: StoryHealth | null
  changeImpacts: ChangeImpact[]
  workspaceContext: any | null
  intelligenceActionId: string | null
  orchestrationRun: OrchestrationRun | null
  contextPacket: ContextPacketRecord | null
  cognitionEvents: CognitionEvent[]
  observabilityEvents: ObservabilityEvent[]
  newChatMessage: string
  isSendingMessage: boolean
  isRunningCycle: boolean
  isDraftingScenes: boolean
  draftActionId: string | null
  editorialActionId: string | null
  manuscriptActionId: string | null
  paragraphs: ParagraphSkeleton[]
  isParagraphsLoading: boolean
  /** Prose content keyed by paragraph_id — loaded on demand for the editor. */
  paragraphContents: Record<string, ParagraphContent>
  isParagraphContentLoading: boolean
  suggestions: ParagraphSuggestion[]
  isSuggestionsLoading: boolean
  /** Version history keyed by paragraph_id */
  versionHistory: Record<string, ParagraphVersion[]>
  isVersionHistoryLoading: boolean
  /** Comments keyed by paragraph_id */
  paragraphComments: Record<string, ParagraphComment[]>
  isCommentsLoading: boolean

  fetchSceneParagraphs: (projectId: string, sceneId: string) => Promise<void>
  generateSceneParagraphs: (projectId: string, sceneId: string, changeReason?: string) => Promise<void>
  updateParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    updates: Record<string, any>,
    changeReason?: string,
    createVersion?: boolean,
  ) => Promise<void>
  reorderParagraphSkeletons: (
    projectId: string,
    sceneId: string,
    reorderPayload: { paragraph_id: string; order: number }[],
  ) => Promise<void>
  lockParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    isLocked: boolean,
  ) => Promise<void>
  deleteParagraphSkeleton: (projectId: string, sceneId: string, paragraphId: string) => Promise<void>
  duplicateParagraphSkeleton: (projectId: string, sceneId: string, paragraphId: string) => Promise<void>
  approveParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    approvalState: string,
  ) => Promise<void>
  regenerateParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    changeReason?: string,
  ) => Promise<void>
  getParagraphHistory: (projectId: string, sceneId: string, paragraphId: string) => Promise<any[]>
  /**
   * Load the authoritative prose for a paragraph into `paragraphContents[paragraphId]`.
   * Safe to call repeatedly — cached per paragraph_id until the user leaves the scene.
   */
  fetchParagraphContent: (projectId: string, sceneId: string, paragraphId: string) => Promise<void>
  fetchParagraphSuggestions: (projectId: string, sceneId: string, paragraphId: string) => Promise<void>
  triggerAiEdit: (projectId: string, sceneId: string, paragraphId: string, mode: string, prompt: string) => Promise<void>
  acceptParagraphSuggestion: (projectId: string, sceneId: string, paragraphId: string, suggestionId: string) => Promise<void>
  rejectParagraphSuggestion: (projectId: string, sceneId: string, paragraphId: string, suggestionId: string) => Promise<void>
  fetchVersionHistory: (projectId: string, sceneId: string, paragraphId: string) => Promise<void>
  restoreVersion: (projectId: string, sceneId: string, paragraphId: string, versionId: string) => Promise<void>
  fetchParagraphComments: (projectId: string, sceneId: string, paragraphId: string) => Promise<void>
  addParagraphComment: (projectId: string, sceneId: string, paragraphId: string, content: string) => Promise<void>
  replyParagraphComment: (projectId: string, sceneId: string, paragraphId: string, commentId: string, content: string) => Promise<void>
  resolveParagraphComment: (projectId: string, sceneId: string, paragraphId: string, commentId: string) => Promise<void>

  fetchProjects: (includeLifecycle?: boolean) => Promise<void>
  fetchProject: (id: string) => Promise<void>
  createProject: (data: Record<string, unknown>) => Promise<Project | null>
  deleteProject: (projectId: string) => Promise<void>
  archiveProject: (projectId: string) => Promise<void>
  unarchiveProject: (projectId: string) => Promise<void>
  restoreProject: (projectId: string) => Promise<void>
  purgeProject: (projectId: string, confirmationTitle: string) => Promise<void>
  duplicateProject: (projectId: string, mode?: 'shell' | 'story') => Promise<Project | null>
  runWorkflow: (projectId: string) => Promise<void>
  runDiscussionCycle: (projectId: string) => Promise<void>
  pollRunStatus: (projectId: string) => void
  stopPolling: () => void
  startLiveSync: (projectId: string) => void
  stopLiveSync: () => void
  refreshProjectData: (projectId: string) => Promise<void>
  fetchRuns: (projectId: string) => Promise<Run[]>
  fetchOutputs: (projectId: string, runId?: string) => Promise<void>
  fetchQuestions: (projectId: string) => Promise<void>
  fetchOutline: (projectId: string) => Promise<void>
  fetchTimeline: (projectId: string) => Promise<void>
  fetchCycles: (projectId: string) => Promise<void>
  fetchNarrativeIntelligence: (projectId: string) => Promise<void>
  fetchStudioArtifacts: (projectId: string) => Promise<void>
  fetchOrchestrationIntelligence: (projectId: string) => Promise<void>
  fetchStoryBible: (projectId: string) => Promise<void>
  fetchStoryHealth: (projectId: string) => Promise<void>
  fetchWorkspaceContext: (projectId: string) => Promise<void>
  runStoryAudit: (projectId: string) => Promise<void>
  previewChangeImpact: (
    projectId: string,
    changeType: string,
    target: Record<string, unknown>,
    proposedChange?: Record<string, unknown>,
  ) => Promise<void>
  updateChangeImpactStatus: (
    projectId: string,
    impactId: string,
    status: 'approved' | 'rejected',
  ) => Promise<void>
  draftScenes: (projectId: string, arcId: string) => Promise<void>
  generateSceneDraft: (
    projectId: string,
    sceneId: string,
    options?: {
      changeReason?: string
      operation?: string
      allowExploratory?: boolean
    },
  ) => Promise<void>
  generateChapterDraft: (projectId: string, chapterPlanId: string) => Promise<void>
  updateDraftStatus: (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
    status: string,
    reason?: string,
  ) => Promise<void>
  regenerateDraft: (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
    changeReason: string,
    operation?: string,
  ) => Promise<void>
  setSceneDraftFavorite: (
    projectId: string,
    draftId: string,
    favorite: boolean,
  ) => Promise<void>
  createWritersRoom: (
    projectId: string,
    draftId: string,
    instruction?: string,
  ) => Promise<void>
  mergeSceneDrafts: (
    projectId: string,
    leftDraftId: string,
    rightDraftId: string,
    mergedText: string,
  ) => Promise<void>
  rollbackDraft: (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
  ) => Promise<void>
  requestEditorialReview: (
    projectId: string,
    subjectType: 'scene' | 'chapter' | 'arc',
    subjectId: string,
  ) => Promise<void>
  requestDialogueReview: (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
  ) => Promise<void>
  createRevisionBranch: (
    projectId: string,
    draftType: 'scene' | 'chapter',
    draftId: string,
    title?: string,
    revisionPass?: string,
  ) => Promise<void>
  generateRevision: (
    projectId: string,
    branchId: string,
    changeReason: string,
    revisionPass?: string,
  ) => Promise<void>
  updateRevisionBranchStatus: (
    projectId: string,
    branchId: string,
    status: string,
    reason?: string,
  ) => Promise<void>
  compareRevision: (projectId: string, branchId: string) => Promise<void>
  applyRevision: (projectId: string, branchId: string) => Promise<void>
  createManuscript: (projectId: string, title?: string) => Promise<void>
  assembleManuscript: (
    projectId: string,
    manuscriptId: string,
    chapterDraftIds: string[],
  ) => Promise<void>
  reviewManuscript: (projectId: string, manuscriptId: string) => Promise<void>
  updateManuscriptStatus: (
    projectId: string,
    manuscriptId: string,
    status: string,
  ) => Promise<void>
  rollbackManuscript: (
    projectId: string,
    manuscriptId: string,
    versionId: string,
  ) => Promise<void>
  validateCanon: (projectId: string) => Promise<void>
  reviewCanon: (projectId: string) => Promise<void>
  updateCanonConflictStatus: (
    projectId: string,
    conflictId: string,
    status: string,
  ) => Promise<void>
  updateCanonRecordActive: (
    projectId: string,
    canonId: string,
    active: boolean,
  ) => Promise<void>
  dismissOperationFailure: () => void
  retryOperationFailure: () => Promise<void>
  sendMessage: (projectId: string, content: string) => Promise<void>
  recordDiscussionDecision: (projectId: string, messageId: string, action: string, note?: string) => Promise<void>
  submitAnswers: (projectId: string, questionId: string, answer: string) => Promise<void>
  updateStoryVision: (projectId: string, data: Record<string, unknown>) => Promise<void>
  activateArc: (projectId: string, arcId: string) => Promise<void>
  updateArcChecklist: (projectId: string, itemId: string, status: string) => Promise<void>
  updatePlanningStatus: (projectId: string, planType: 'scene' | 'chapter', planId: string, status: string) => Promise<void>
  fetchStoryRoom: (projectId: string) => Promise<void>
  setSelectedProject: (project: Project | null) => void
  setSelectedTab: (tab: string) => void
  setNewProjectTitle: (value: string) => void
  setNewProjectPremise: (value: string) => void
  setNewProjectIdeaDump: (value: string) => void
  setNewProjectGenre: (value: string) => void
  setNewProjectTone: (value: string) => void
  setNewProjectThemes: (value: string) => void
  setNewProjectInspirations: (value: string) => void
  setNewProjectCharacterNotes: (value: string) => void
  setNewProjectWorldNotes: (value: string) => void
  setNewProjectPlotNotes: (value: string) => void
  setNewProjectNotes: (value: string) => void
  setNewChatMessage: (value: string) => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  selectedProject: null,
  currentRun: null,
  runs: [],
  outputs: [],
  questions: [],
  outline: null,
  timelineMessages: [],
  cycles: [],
  characterBibles: [],
  narrativeWorldBible: null,
  plotThreads: [],
  continuityReports: [],
  scenes: [],
  sceneDrafts: [],
  chapterDrafts: [],
  relationships: [],
  themeRegistry: null,
  foreshadowing: [],
  discussionMessages: [],
  storyVision: null,
  storyArcs: [],
  powerSystem: null,
  characterJourneys: [],
  mysteries: [],
  aiInsights: null,
  factions: [],
  storyBible: null,
  storyTimeline: [],
  readinessItems: [],
  readinessReports: [],
  characterProgressions: [],
  knowledgeEntries: [],
  artifactRegistry: [],
  arcChecklists: [],
  arcDependencies: [],
  arcDevelopmentReports: [],
  chapterPlans: [],
  powerProgressions: [],
  knowledgeEvolutions: [],
  artifactEvolutions: [],
  foreshadowChains: [],
  storyRoom: null,
  editorialReports: [],
  editorialScores: [],
  revisionBranches: [],
  revisionVersions: [],
  revisionComparisons: {},
  manuscripts: [],
  manuscriptVersions: [],
  manuscriptReports: [],
  canonRecords: [],
  canonConflicts: [],
  chapterIntelligence: [],
  storyAudits: [],
  storyHealth: null,
  workspaceContext: null,
  changeImpacts: [],
  intelligenceActionId: null,
  orchestrationRun: null,
  contextPacket: null,
  cognitionEvents: [],
  observabilityEvents: [],
  newChatMessage: '',
  isSendingMessage: false,
  isRunningCycle: false,
  isDraftingScenes: false,
  draftActionId: null,
  editorialActionId: null,
  manuscriptActionId: null,
  paragraphs: [],
  isParagraphsLoading: false,
  paragraphContents: {},
  isParagraphContentLoading: false,
  suggestions: [],
  isSuggestionsLoading: false,
  versionHistory: {},
  isVersionHistoryLoading: false,
  paragraphComments: {},
  isCommentsLoading: false,
  loading: false,

  isRunningWorkflow: false,
  error: null,
  operationFailure: null,
  pollingIntervalId: null,
  liveSyncIntervalId: null,
  projectEventSource: null,
  selectedTab: 'workflow',
  newProjectTitle: '',
  newProjectPremise: '',
  newProjectIdeaDump: '',
  newProjectGenre: '',
  newProjectTone: '',
  newProjectThemes: '',
  newProjectInspirations: '',
  newProjectCharacterNotes: '',
  newProjectWorldNotes: '',
  newProjectPlotNotes: '',
  newProjectNotes: '',

  dismissOperationFailure: () => set({ operationFailure: null, error: null }),
  retryOperationFailure: async () => {
    const failure = get().operationFailure
    if (failure?.retry) await failure.retry()
  },

  stopPolling: () => {
    const { pollingIntervalId } = get()
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId)
      set({ pollingIntervalId: null })
    }
  },

  stopLiveSync: () => {
    const { liveSyncIntervalId, projectEventSource } = get()
    if (liveSyncIntervalId) {
      clearInterval(liveSyncIntervalId)
    }
    projectEventSource?.close()
    set({ liveSyncIntervalId: null, projectEventSource: null })
  },

  refreshProjectData: async (projectId: string) => {
    try {
      const [bootstrap] = await Promise.all([
        rc6Api.getWorkspaceBootstrap(projectId),
        // Populate the writing/planning surfaces as soon as the lightweight
        // current Story Bible is available while a cold full bootstrap finishes.
        get().fetchStoryBible(projectId),
        get().fetchStoryRoom(projectId),
        get().fetchWorkspaceContext(projectId),
      ])
      set({
        selectedProject: bootstrap.project as unknown as Project,
        ...projectStateFromStoryBible(
          bootstrap.story_bible as StoryBible,
          bootstrap.story_health as StoryHealth,
        ),
        storyHealth: bootstrap.story_health as StoryHealth,
      })
      await Promise.all([
        get().fetchRuns(projectId),
        get().fetchOrchestrationIntelligence(projectId),
        // Questions are authoritative records. The Story Bible is a projection
        // and may still contain the pre-answer snapshot immediately after an
        // author decision, so refresh the source before updating the screen.
        get().fetchQuestions(projectId),
      ])
    } catch (error: unknown) {
      console.warn('[projectStore] Workspace bootstrap failed; using compatible endpoints', error)
      await Promise.all([
        get().fetchStoryBible(projectId),
        get().fetchStoryRoom(projectId),
        get().fetchStoryHealth(projectId),
        get().fetchWorkspaceContext(projectId),
        get().fetchQuestions(projectId),
      ])
    }
  },

  startLiveSync: (projectId: string) => {
    get().stopLiveSync()
    void Promise.all([
      get().refreshProjectData(projectId),
      get().fetchOrchestrationIntelligence(projectId),
    ])
    if (typeof EventSource === 'undefined') return
    const source = new EventSource(projectEventUrl(projectId))
    source.addEventListener('project_update', (e: any) => {
      let eventType = ''
      try {
        const data = JSON.parse(e.data)
        if (data && data.event_type) {
          eventType = String(data.event_type)
          eventBus.publish(data.event_type, data.payload || {})
        }
      } catch (err) {
        console.error('Error parsing project_update SSE event:', err)
      }
      const refresh = eventType === 'narrative_analysis_started'
        ? Promise.resolve()
        : eventType === 'narrative_analysis_completed'
          ? Promise.all([
              get().fetchStoryHealth(projectId),
              get().fetchWorkspaceContext(projectId),
            ])
          : eventType.startsWith('canon_')
            ? Promise.all([
                get().fetchStoryBible(projectId),
                get().fetchStoryHealth(projectId),
                get().fetchWorkspaceContext(projectId),
              ])
            : Promise.all([
                get().refreshProjectData(projectId),
                get().fetchOrchestrationIntelligence(projectId),
              ])
      void refresh.then(() => {
        const run = get().currentRun
        if (!run || TERMINAL_STATUSES.has(run.status)) {
          set({ isRunningWorkflow: false, isRunningCycle: false, loading: false })
        }
      })
    })
    source.onerror = () => {
      if (get().selectedProject?.id !== projectId) source.close()
    }
    const liveSyncIntervalId = setInterval(() => {
      void Promise.all([
        get().fetchRuns(projectId),
        get().fetchOrchestrationIntelligence(projectId),
      ]).then(() => {
        const run = get().currentRun
        if (!run || TERMINAL_STATUSES.has(run.status)) {
          set({ isRunningWorkflow: false, isRunningCycle: false, loading: false })
        }
      })
    }, 4000)
    set({ projectEventSource: source, liveSyncIntervalId })
  },

  fetchStoryBible: async (projectId: string) => {
    try {
      const storyBible = await dataApi.getStoryBible(projectId) as StoryBible
      set(projectStateFromStoryBible(storyBible, get().storyHealth))
    } catch (error: unknown) {
      console.warn('[projectStore] Story Bible fetch failed', error)
    }
  },

  fetchStoryHealth: async (projectId: string) => {
    try {
      const storyHealth = await dataApi.getStoryHealth(projectId) as StoryHealth
      set({ storyHealth })
    } catch (error: unknown) {
      console.warn('[projectStore] Story Health fetch failed', error)
    }
  },

  fetchWorkspaceContext: async (projectId: string) => {
    try {
      const workspaceContext = await projectsApi.getWorkspaceContext(projectId)
      set({ workspaceContext })
    } catch (error: unknown) {
      console.warn('[projectStore] Workspace Context fetch failed', error)
    }
  },

  runStoryAudit: async (projectId: string) => {
    set({ intelligenceActionId: 'audit', operationFailure: null, error: null })
    try {
      const report = await dataApi.runStoryAudit(projectId) as StoryAuditReport
      await get().refreshProjectData(projectId)
      set((state) => ({
        storyAudits: [
          report,
          ...state.storyAudits.filter((item) => item.report_id !== report.report_id),
        ],
        intelligenceActionId: null,
        operationFailure: null,
        error: null,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run story audit'
      set({ error: message, operationFailure: authorFailure('Story audit', error, 'story-health', () => get().runStoryAudit(projectId)), intelligenceActionId: null })
    }
  },

  previewChangeImpact: async (
    projectId,
    changeType,
    target,
    proposedChange = {},
  ) => {
    set({ intelligenceActionId: 'impact', operationFailure: null, error: null })
    try {
      const impact = await dataApi.previewChangeImpact(projectId, {
        change_type: changeType,
        target,
        proposed_change: proposedChange,
      }) as ChangeImpact
      set((state) => ({
        changeImpacts: [
          impact,
          ...state.changeImpacts.filter((item) => item.impact_id !== impact.impact_id),
        ],
        intelligenceActionId: null,
        operationFailure: null,
        error: null,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to preview change impact'
      set({ error: message, operationFailure: authorFailure('Change impact preview', error, 'story-health', () => get().previewChangeImpact(projectId, changeType, target, proposedChange)), intelligenceActionId: null })
    }
  },

  updateChangeImpactStatus: async (projectId, impactId, status) => {
    set({ intelligenceActionId: impactId, operationFailure: null, error: null })
    try {
      const impact = await dataApi.updateChangeImpactStatus(
        projectId,
        impactId,
        status,
      ) as ChangeImpact
      set((state) => ({
        changeImpacts: state.changeImpacts.map((item) => (
          item.impact_id === impactId ? impact : item
        )),
        intelligenceActionId: null,
        operationFailure: null,
        error: null,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to record impact decision'
      set({ error: message, operationFailure: authorFailure('Change impact decision', error, 'story-health', () => get().updateChangeImpactStatus(projectId, impactId, status)), intelligenceActionId: null })
    }
  },

  fetchProjects: async (includeLifecycle = false) => {
    set({ loading: true, error: null })
    try {
      const projects = await projectsApi.getAll(
        includeLifecycle ? { includeArchived: true, includeTrashed: true } : undefined
      )
      set({ projects, loading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch projects'
      set({ error: message, loading: false })
    }
  },

  fetchProject: async (id: string) => {
    set({ loading: true, error: null })
    try {
      const project = await projectsApi.getById(id)
      set({ selectedProject: project, loading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch project'
      set({ error: message, loading: false })
    }
  },

  createProject: async (data: Record<string, unknown>) => {
    set({ loading: true, error: null })
    try {
      const project = await projectsApi.create(data)
      set((state) => ({
        selectedProject: project,
        projects: [project as Project, ...state.projects.filter((item) => item.id !== project.id)],
        loading: false,
        newProjectTitle: '',
        newProjectPremise: '',
        newProjectIdeaDump: '',
        newProjectGenre: '',
        newProjectTone: '',
        newProjectThemes: '',
        newProjectInspirations: '',
        newProjectCharacterNotes: '',
        newProjectWorldNotes: '',
        newProjectPlotNotes: '',
        newProjectNotes: '',
        selectedTab: 'chat', // Auto-navigate to chat tab
      }))
      return project as Project
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create project'
      set({ error: message, loading: false })
      return null
    }
  },

  deleteProject: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      await projectsApi.deleteProject(projectId)
      const projects = await projectsApi.getAll({ includeArchived: true, includeTrashed: true })
      const nextProject = projects.find(
        (project: Project) => project.id !== projectId && !['archived', 'trashed'].includes(project.status)
      ) ?? null
      set({
        projects,
        selectedProject: nextProject,
        loading: false,
        selectedTab: nextProject ? get().selectedTab : 'workflow',
      })
      if (nextProject) {
        get().setSelectedProject(nextProject)
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete project'
      set({ error: message, loading: false })
    }
  },

  archiveProject: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      await projectsApi.archive(projectId)
      await get().fetchProjects(true)
      set({ loading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to archive project'
      set({ error: message, loading: false })
    }
  },

  unarchiveProject: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      await projectsApi.unarchive(projectId)
      await get().fetchProjects(true)
      set({ loading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to unarchive project'
      set({ error: message, loading: false })
    }
  },

  restoreProject: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      await projectsApi.restore(projectId)
      await get().fetchProjects(true)
      set({ loading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to restore project'
      set({ error: message, loading: false })
    }
  },

  purgeProject: async (projectId: string, confirmationTitle: string) => {
    set({ loading: true, error: null })
    try {
      await projectsApi.purge(projectId, confirmationTitle)
      await get().fetchProjects(true)
      set({ loading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to permanently delete project'
      set({ error: message, loading: false })
    }
  },

  duplicateProject: async (projectId: string, mode = 'shell') => {
    set({ loading: true, error: null })
    try {
      const project = await projectsApi.duplicate(projectId, mode)
      await get().fetchProjects(true)
      set({ loading: false })
      return project as Project
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to duplicate project'
      set({ error: message, loading: false })
      return null
    }
  },

  fetchRuns: async (projectId: string) => {
    try {
      const runs = await workflowApi.getRuns(projectId)
      const sorted = Array.isArray(runs) ? runs : []
      const latestRun = sorted[0] ?? null
      set({ runs: sorted, currentRun: latestRun })
      return sorted
    } catch (error: unknown) {
      console.warn('[projectStore] Run status refresh failed; keeping the last known status', error)
      return get().runs
    }
  },

  fetchOutputs: async (projectId: string, runId?: string) => {
    try {
      const outputs = await workflowApi.getOutputs(projectId, runId)
      console.log('[projectStore] Outputs loaded:', outputs?.length ?? 0)
      set({ outputs: Array.isArray(outputs) ? outputs : [] })
    } catch (error: unknown) {
      console.warn('[projectStore] Outputs fetch failed, using empty list', error)
      set({ outputs: [] })
    }
  },

  fetchQuestions: async (projectId: string) => {
    try {
      const questions = await dataApi.getQuestions(projectId)
      console.log('[projectStore] Questions loaded:', questions?.length ?? 0)
      set({ questions: Array.isArray(questions) ? questions : [] })
    } catch (error: unknown) {
      console.warn('[projectStore] Questions fetch failed, using empty list', error)
      set({ questions: [] })
    }
  },

  fetchOutline: async (projectId: string) => {
    try {
      const outline = await dataApi.getOutline(projectId)
      console.log('[projectStore] Outline loaded')
      const hasContent =
        Boolean(outline?.premise) ||
        (outline?.themes?.length ?? 0) > 0 ||
        (outline?.acts?.length ?? 0) > 0 ||
        (outline?.chapters?.length ?? 0) > 0
      set({ outline: hasContent ? outline : null })
    } catch (error: unknown) {
      console.warn('[projectStore] Outline fetch failed', error)
      set({ outline: null })
    }
  },

  fetchTimeline: async (projectId: string) => {
    try {
      const messages = await projectsApi.getTimeline(projectId)
      console.log('[projectStore] Timeline messages loaded:', messages?.length ?? 0)
      set({ timelineMessages: Array.isArray(messages) ? messages : [] })
    } catch (error: unknown) {
      console.warn('[projectStore] Timeline fetch failed, using empty list', error)
      set({ timelineMessages: [] })
    }
  },

  fetchCycles: async (projectId: string) => {
    try {
      const cycles = await workflowApi.getCycles(projectId)
      console.log('[projectStore] Cycles loaded:', cycles?.length ?? 0)
      set({ cycles: Array.isArray(cycles) ? cycles : [] })
    } catch (error: unknown) {
      console.warn('[projectStore] Cycles fetch failed, using empty list', error)
      set({ cycles: [] })
    }
  },

  fetchNarrativeIntelligence: async (projectId: string) => {
    try {
      const [
        characterBibles,
        narrativeWorldBible,
        plotThreads,
        continuityReports,
        scenes,
        sceneDrafts,
        relationships,
        themeRegistry,
        foreshadowing,
      ] = await Promise.all([
        dataApi.getCharacterBibles(projectId),
        dataApi.getNarrativeWorld(projectId),
        dataApi.getPlotThreads(projectId),
        dataApi.getContinuity(projectId),
        dataApi.getScenes(projectId),
        dataApi.getSceneDrafts(projectId),
        dataApi.getRelationships(projectId),
        dataApi.getThemes(projectId),
        dataApi.getForeshadowing(projectId),
      ])
      set({
        characterBibles: Array.isArray(characterBibles) ? characterBibles : [],
        narrativeWorldBible: narrativeWorldBible ?? null,
        plotThreads: Array.isArray(plotThreads) ? plotThreads : [],
        continuityReports: Array.isArray(continuityReports) ? continuityReports : [],
        scenes: Array.isArray(scenes) ? scenes : [],
        sceneDrafts: Array.isArray(sceneDrafts) ? sceneDrafts : [],
        relationships: Array.isArray(relationships) ? relationships : [],
        themeRegistry: themeRegistry ?? null,
        foreshadowing: Array.isArray(foreshadowing) ? foreshadowing : [],
      })
    } catch (error: unknown) {
      console.warn('[projectStore] Narrative intelligence fetch failed', error)
    }
  },

  fetchStudioArtifacts: async (projectId: string) => {
    try {
      const [
        discussionMessages,
        storyVision,
        storyArcs,
        powerSystem,
        characterJourneys,
        mysteries,
        aiInsights,
        factions,
      ] = await Promise.all([
        dataApi.getDiscussion(projectId),
        dataApi.getStoryVision(projectId),
        dataApi.getArcs(projectId),
        dataApi.getPowerSystem(projectId),
        dataApi.getCharacterJourneys(projectId),
        dataApi.getMysteries(projectId),
        dataApi.getAIInsights(projectId),
        dataApi.getFactions(projectId),
      ])
      set({
        discussionMessages: Array.isArray(discussionMessages) ? discussionMessages : [],
        storyVision: storyVision ?? null,
        storyArcs: Array.isArray(storyArcs) ? storyArcs : [],
        powerSystem: powerSystem ?? null,
        characterJourneys: Array.isArray(characterJourneys) ? characterJourneys : [],
        mysteries: Array.isArray(mysteries) ? mysteries : [],
        aiInsights: aiInsights ?? null,
        factions: Array.isArray(factions) ? factions : [],
      })
    } catch (error: unknown) {
      console.warn('[projectStore] Studio artifacts fetch failed', error)
    }
  },

  fetchOrchestrationIntelligence: async (projectId: string) => {
    try {
      const [orchestrationRun, contextPacket, cognitionEvents, observabilityEvents] = await Promise.all([
        dataApi.getLatestOrchestration(projectId),
        dataApi.getLatestContext(projectId),
        dataApi.getCognition(projectId),
        dataApi.getObservability(projectId),
      ])
      set({
        orchestrationRun: orchestrationRun?.id ? orchestrationRun : null,
        contextPacket: contextPacket?.cycle_number ? contextPacket : null,
        cognitionEvents: Array.isArray(cognitionEvents) ? cognitionEvents : [],
        observabilityEvents: Array.isArray(observabilityEvents) ? observabilityEvents : [],
      })
    } catch (error: unknown) {
      console.warn('[projectStore] Orchestration intelligence fetch failed', error)
    }
  },

  draftScenes: async (projectId: string, arcId: string) => {
    set({ isDraftingScenes: true, error: null })
    try {
      await dataApi.draftScenes(projectId, arcId)
      await get().refreshProjectData(projectId)
      set({ isDraftingScenes: false, operationFailure: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to draft scenes'
      set({
        error: message,
        operationFailure: authorFailure(
          'Scene planning', error, 'drafting', () => get().draftScenes(projectId, arcId),
        ),
        isDraftingScenes: false,
      })
    }
  },

  generateSceneDraft: async (projectId: string, sceneId: string, options = {}) => {
    if (get().draftActionId === sceneId) return
    set({ draftActionId: sceneId, operationFailure: null, error: null })
    try {
      await dataApi.generateSceneDraft(projectId, sceneId, options)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate scene draft'
      set({
        error: message,
        operationFailure: authorFailure(
          'Draft generation', error, 'drafting',
          () => get().generateSceneDraft(projectId, sceneId, options),
        ),
        draftActionId: null,
      })
    }
  },

  generateChapterDraft: async (projectId: string, chapterPlanId: string) => {
    set({ draftActionId: chapterPlanId, operationFailure: null, error: null })
    try {
      await dataApi.generateChapterDraft(projectId, chapterPlanId)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to assemble chapter draft'
      set({
        error: message,
        operationFailure: authorFailure(
          'Chapter assembly', error, 'drafting',
          () => get().generateChapterDraft(projectId, chapterPlanId),
        ),
        draftActionId: null,
      })
    }
  },

  updateDraftStatus: async (projectId, draftType, draftId, status, reason = '') => {
    set({ draftActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.updateDraftStatus(projectId, draftType, draftId, status, reason)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update draft status'
      set({
        error: message,
        operationFailure: authorFailure(
          status === 'approved' ? 'Draft approval' : 'Draft status change',
          error,
          draftType === 'scene' ? 'drafting' : 'editorial',
          () => get().updateDraftStatus(projectId, draftType, draftId, status, reason),
        ),
        draftActionId: null,
      })
    }
  },

  regenerateDraft: async (projectId, draftType, draftId, changeReason, operation = 'rewrite') => {
    if (get().draftActionId === draftId) return
    set({ draftActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.regenerateDraft(projectId, draftType, draftId, changeReason, operation)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to regenerate draft'
      set({
        error: message,
        operationFailure: authorFailure(
          'Draft revision', error, 'drafting',
          () => get().regenerateDraft(projectId, draftType, draftId, changeReason, operation),
        ),
        draftActionId: null,
      })
    }
  },

  rollbackDraft: async (projectId, draftType, draftId) => {
    set({ draftActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.rollbackDraft(projectId, draftType, draftId)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to roll back draft'
      set({
        error: message,
        operationFailure: authorFailure(
          'Draft restore', error, draftType === 'scene' ? 'drafting' : 'editorial',
          () => get().rollbackDraft(projectId, draftType, draftId),
        ),
        draftActionId: null,
      })
    }
  },

  setSceneDraftFavorite: async (projectId, draftId, favorite) => {
    set({ draftActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.setSceneDraftFavorite(projectId, draftId, favorite)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update favorite'
      set({
        error: message,
        operationFailure: authorFailure(
          favorite ? 'Favorite draft' : 'Remove draft favorite', error, 'drafting',
          () => get().setSceneDraftFavorite(projectId, draftId, favorite),
        ),
        draftActionId: null,
      })
    }
  },

  createWritersRoom: async (projectId, draftId, instruction = '') => {
    if (get().draftActionId === draftId) return
    set({ draftActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.createWritersRoom(projectId, draftId, instruction)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create Writer’s Room options'
      set({
        error: message,
        operationFailure: authorFailure(
          'Writer’s Room alternatives', error, 'drafting',
          () => get().createWritersRoom(projectId, draftId, instruction),
        ),
        draftActionId: null,
      })
    }
  },

  mergeSceneDrafts: async (projectId, leftDraftId, rightDraftId, mergedText) => {
    const actionId = `${leftDraftId}:${rightDraftId}`
    set({ draftActionId: actionId, operationFailure: null, error: null })
    try {
      await dataApi.mergeSceneDrafts(projectId, leftDraftId, rightDraftId, mergedText)
      await get().refreshProjectData(projectId)
      set({ draftActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to merge scene versions'
      set({
        error: message,
        operationFailure: authorFailure(
          'Draft merge', error, 'drafting',
          () => get().mergeSceneDrafts(projectId, leftDraftId, rightDraftId, mergedText),
        ),
        draftActionId: null,
      })
    }
  },

  fetchSceneParagraphs: async (projectId: string, sceneId: string) => {
    set({ isParagraphsLoading: true, error: null })
    try {
      const data = await dataApi.getSceneParagraphs(projectId, sceneId)
      set({ paragraphs: data, isParagraphsLoading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch paragraphs'
      set({ error: message, isParagraphsLoading: false })
    }
  },

  generateSceneParagraphs: async (projectId: string, sceneId: string, changeReason = '') => {
    set({ isParagraphsLoading: true, error: null })
    try {
      const res = await dataApi.generateSceneParagraphs(projectId, sceneId, changeReason)
      set({ paragraphs: res.paragraphs, isParagraphsLoading: false })
      await get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate paragraph skeletons'
      set({ error: message, isParagraphsLoading: false })
    }
  },

  updateParagraphSkeleton: async (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    updates: Record<string, any>,
    changeReason = '',
    createVersion = false,
  ) => {
    set({ isParagraphsLoading: true, error: null })
    try {
      const updated = await dataApi.updateParagraphSkeleton(projectId, sceneId, paragraphId, updates, changeReason, createVersion)
      const paragraphs = get().paragraphs.map((p) =>
        p.paragraph_id === paragraphId ? updated : p
      )
      set({ paragraphs, isParagraphsLoading: false })
      await get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update paragraph'
      set({ error: message, isParagraphsLoading: false })
    }
  },

  reorderParagraphSkeletons: async (
    projectId: string,
    sceneId: string,
    reorderPayload: { paragraph_id: string; order: number }[],
  ) => {
    const localOrdered = [...get().paragraphs]
    reorderPayload.forEach((item) => {
      const p = localOrdered.find((x) => x.paragraph_id === item.paragraph_id)
      if (p) p.order = item.order
    })
    localOrdered.sort((a, b) => a.order - b.order)
    set({ paragraphs: localOrdered })

    try {
      const res = await dataApi.reorderParagraphSkeletons(projectId, sceneId, reorderPayload)
      set({ paragraphs: res })
      await get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to reorder paragraphs'
      set({ error: message })
      await get().fetchSceneParagraphs(projectId, sceneId)
    }
  },

  lockParagraphSkeleton: async (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    isLocked: boolean,
  ) => {
    const paragraphs = get().paragraphs.map((p) =>
      p.paragraph_id === paragraphId ? { ...p, is_locked: isLocked } : p
    )
    set({ paragraphs })

    try {
      const updated = await dataApi.lockParagraphSkeleton(projectId, sceneId, paragraphId, isLocked)
      const fresh = get().paragraphs.map((p) =>
        p.paragraph_id === paragraphId ? updated : p
      )
      set({ paragraphs: fresh })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to lock paragraph'
      set({ error: message })
      await get().fetchSceneParagraphs(projectId, sceneId)
    }
  },

  deleteParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string) => {
    const paragraphs = get().paragraphs.filter((p) => p.paragraph_id !== paragraphId)
    set({ paragraphs })

    try {
      await dataApi.deleteParagraphSkeleton(projectId, sceneId, paragraphId)
      await get().fetchSceneParagraphs(projectId, sceneId)
      await get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to delete paragraph'
      set({ error: message })
      await get().fetchSceneParagraphs(projectId, sceneId)
    }
  },

  duplicateParagraphSkeleton: async (projectId: string, sceneId: string, paragraphId: string) => {
    set({ isParagraphsLoading: true, error: null })
    try {
      const duplicated = await dataApi.duplicateParagraphSkeleton(projectId, sceneId, paragraphId)
      set((state) => ({
        paragraphs: [...state.paragraphs, duplicated].sort(
          (left, right) => left.order - right.order,
        ),
        isParagraphsLoading: false,
      }))
      await get().fetchSceneParagraphs(projectId, sceneId)
      void get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to duplicate paragraph'
      set({ error: message, isParagraphsLoading: false })
    }
  },

  approveParagraphSkeleton: async (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    approvalState: string,
  ) => {
    const paragraphs = get().paragraphs.map((p) =>
      p.paragraph_id === paragraphId ? { ...p, approval_state: approvalState as any } : p
    )
    set({ paragraphs })

    try {
      const updated = await dataApi.approveParagraphSkeleton(projectId, sceneId, paragraphId, approvalState)
      const fresh = get().paragraphs.map((p) =>
        p.paragraph_id === paragraphId ? updated : p
      )
      set({ paragraphs: fresh })
      await get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to approve paragraph'
      set({ error: message })
      await get().fetchSceneParagraphs(projectId, sceneId)
    }
  },

  regenerateParagraphSkeleton: async (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    changeReason = '',
  ) => {
    set({ isParagraphsLoading: true, error: null })
    try {
      const updated = await dataApi.regenerateParagraphSkeleton(projectId, sceneId, paragraphId, changeReason)
      const paragraphs = get().paragraphs.map((p) =>
        p.paragraph_id === paragraphId ? updated : p
      )
      set({ paragraphs, isParagraphsLoading: false })
      await get().refreshProjectData(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to regenerate paragraph'
      set({ error: message, isParagraphsLoading: false })
    }
  },

  getParagraphHistory: async (projectId: string, sceneId: string, paragraphId: string) => {
    try {
      return await dataApi.getParagraphHistory(projectId, sceneId, paragraphId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to get paragraph history'
      set({ error: message })
      return []
    }
  },

  fetchParagraphContent: async (projectId: string, sceneId: string, paragraphId: string) => {
    set({ isParagraphContentLoading: true })
    try {
      const content = await dataApi.getParagraphContent(projectId, sceneId, paragraphId)
      set((state) => ({
        paragraphContents: { ...state.paragraphContents, [paragraphId]: content },
        isParagraphContentLoading: false,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to load paragraph content'
      set({ error: message, isParagraphContentLoading: false })
    }
  },

  fetchParagraphSuggestions: async (projectId: string, sceneId: string, paragraphId: string) => {
    set({ isSuggestionsLoading: true })
    try {
      const suggestions = await dataApi.getParagraphSuggestions(projectId, sceneId, paragraphId)
      set({ suggestions, isSuggestionsLoading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to fetch suggestions'
      set({ error: message, isSuggestionsLoading: false })
    }
  },

  triggerAiEdit: async (projectId: string, sceneId: string, paragraphId: string, mode: string, prompt: string) => {
    set({ isSuggestionsLoading: true })
    try {
      await dataApi.aiEditParagraph(projectId, sceneId, paragraphId, mode, prompt)
      // Re-fetch suggestions list to get the new suggestion
      const suggestions = await dataApi.getParagraphSuggestions(projectId, sceneId, paragraphId)
      set({ suggestions, isSuggestionsLoading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate AI suggestion'
      set({ error: message, isSuggestionsLoading: false })
    }
  },

  acceptParagraphSuggestion: async (projectId: string, sceneId: string, paragraphId: string, suggestionId: string) => {
    set({ isParagraphContentLoading: true, isSuggestionsLoading: true })
    try {
      await dataApi.acceptParagraphSuggestion(projectId, sceneId, paragraphId, suggestionId)
      
      // Reload authoritative prose content
      const content = await dataApi.getParagraphContent(projectId, sceneId, paragraphId)
      
      // Re-fetch suggestions list
      const suggestions = await dataApi.getParagraphSuggestions(projectId, sceneId, paragraphId)
      
      // Reload scene paragraphs (to sync skeleton metadata like version, etc.)
      const response = await dataApi.getSceneParagraphs(projectId, sceneId)
      
      set((state) => ({
        paragraphContents: { ...state.paragraphContents, [paragraphId]: content },
        paragraphs: response.paragraphs || state.paragraphs,
        suggestions,
        isParagraphContentLoading: false,
        isSuggestionsLoading: false,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to accept AI suggestion'
      set({ error: message, isParagraphContentLoading: false, isSuggestionsLoading: false })
    }
  },

  rejectParagraphSuggestion: async (projectId: string, sceneId: string, paragraphId: string, suggestionId: string) => {
    set({ isSuggestionsLoading: true })
    try {
      await dataApi.rejectParagraphSuggestion(projectId, sceneId, paragraphId, suggestionId)
      // Re-fetch suggestions list to keep in sync
      const suggestions = await dataApi.getParagraphSuggestions(projectId, sceneId, paragraphId)
      set({ suggestions, isSuggestionsLoading: false })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to reject AI suggestion'
      set({ error: message, isSuggestionsLoading: false })
    }
  },

  fetchVersionHistory: async (projectId: string, sceneId: string, paragraphId: string) => {
    set({ isVersionHistoryLoading: true })
    try {
      const versions = await dataApi.getParagraphHistory(projectId, sceneId, paragraphId)
      set((state) => ({
        versionHistory: { ...state.versionHistory, [paragraphId]: versions },
        isVersionHistoryLoading: false,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to load version history'
      set({ error: message, isVersionHistoryLoading: false })
    }
  },

  restoreVersion: async (projectId: string, sceneId: string, paragraphId: string, versionId: string) => {
    set({ isVersionHistoryLoading: true, isParagraphContentLoading: true })
    try {
      const updated = await dataApi.restoreParagraphVersion(projectId, sceneId, paragraphId, versionId)
      // Reload content to reflect restored prose
      const content = await dataApi.getParagraphContent(projectId, sceneId, paragraphId)
      // Reload versions
      const versions = await dataApi.getParagraphHistory(projectId, sceneId, paragraphId)
      // Sync skeleton list
      const response = await dataApi.getSceneParagraphs(projectId, sceneId)
      set((state) => ({
        paragraphContents: { ...state.paragraphContents, [paragraphId]: content },
        versionHistory: { ...state.versionHistory, [paragraphId]: versions },
        paragraphs: response.paragraphs || state.paragraphs,
        isVersionHistoryLoading: false,
        isParagraphContentLoading: false,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to restore version'
      set({ error: message, isVersionHistoryLoading: false, isParagraphContentLoading: false })
    }
  },

  fetchParagraphComments: async (projectId: string, sceneId: string, paragraphId: string) => {
    set({ isCommentsLoading: true })
    try {
      const comments = await dataApi.getParagraphComments(projectId, sceneId, paragraphId)
      set((state) => ({
        paragraphComments: { ...state.paragraphComments, [paragraphId]: comments },
        isCommentsLoading: false,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to load comments'
      set({ error: message, isCommentsLoading: false })
    }
  },

  addParagraphComment: async (projectId: string, sceneId: string, paragraphId: string, content: string) => {
    try {
      await dataApi.addParagraphComment(projectId, sceneId, paragraphId, content)
      const comments = await dataApi.getParagraphComments(projectId, sceneId, paragraphId)
      set((state) => ({
        paragraphComments: { ...state.paragraphComments, [paragraphId]: comments },
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to add comment'
      set({ error: message })
    }
  },

  replyParagraphComment: async (projectId: string, sceneId: string, paragraphId: string, commentId: string, content: string) => {
    try {
      await dataApi.replyParagraphComment(projectId, sceneId, paragraphId, commentId, content)
      const comments = await dataApi.getParagraphComments(projectId, sceneId, paragraphId)
      set((state) => ({
        paragraphComments: { ...state.paragraphComments, [paragraphId]: comments },
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to reply to comment'
      set({ error: message })
    }
  },

  resolveParagraphComment: async (projectId: string, sceneId: string, paragraphId: string, commentId: string) => {
    try {
      await dataApi.resolveParagraphComment(projectId, sceneId, paragraphId, commentId)
      const comments = await dataApi.getParagraphComments(projectId, sceneId, paragraphId)
      set((state) => ({
        paragraphComments: { ...state.paragraphComments, [paragraphId]: comments },
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to resolve comment'
      set({ error: message })
    }
  },

  requestEditorialReview: async (projectId, subjectType, subjectId) => {

    set({ editorialActionId: subjectId, operationFailure: null, error: null })
    try {
      await dataApi.requestEditorialReview(projectId, subjectType, subjectId)
      await get().refreshProjectData(projectId)
      set({ editorialActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run editorial review'
      set({
        error: message,
        operationFailure: authorFailure(
          'Editorial review', error, 'editorial',
          () => get().requestEditorialReview(projectId, subjectType, subjectId),
        ),
        editorialActionId: null,
      })
    }
  },

  requestDialogueReview: async (projectId, draftType, draftId) => {
    set({ editorialActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.requestDialogueReview(projectId, draftType, draftId)
      await get().refreshProjectData(projectId)
      set({ editorialActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run dialogue review'
      set({
        error: message,
        operationFailure: authorFailure(
          'Dialogue review', error, 'editorial',
          () => get().requestDialogueReview(projectId, draftType, draftId),
        ),
        editorialActionId: null,
      })
    }
  },

  createRevisionBranch: async (projectId, draftType, draftId, title = '', revisionPass = 'development') => {
    set({ editorialActionId: draftId, operationFailure: null, error: null })
    try {
      await dataApi.createRevisionBranch(projectId, {
        source_draft_type: draftType,
        source_draft_id: draftId,
        title,
        revision_pass: revisionPass,
      })
      await get().refreshProjectData(projectId)
      set({ editorialActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create revision branch'
      set({
        error: message,
        operationFailure: authorFailure(
          'Revision setup', error, 'editorial',
          () => get().createRevisionBranch(projectId, draftType, draftId, title, revisionPass),
        ),
        editorialActionId: null,
      })
    }
  },

  generateRevision: async (projectId, branchId, changeReason, revisionPass = 'development') => {
    set({ editorialActionId: branchId, operationFailure: null, error: null })
    try {
      await dataApi.generateRevision(projectId, branchId, changeReason, revisionPass)
      await get().refreshProjectData(projectId)
      set({ editorialActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to generate revision'
      set({
        error: message,
        operationFailure: authorFailure(
          'Revision generation', error, 'editorial',
          () => get().generateRevision(projectId, branchId, changeReason, revisionPass),
        ),
        editorialActionId: null,
      })
    }
  },

  updateRevisionBranchStatus: async (projectId, branchId, status, reason = '') => {
    set({ editorialActionId: branchId, operationFailure: null, error: null })
    try {
      await dataApi.updateRevisionBranchStatus(projectId, branchId, status, reason)
      await get().refreshProjectData(projectId)
      set({ editorialActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update revision branch'
      set({
        error: message,
        operationFailure: authorFailure(
          'Revision status change', error, 'editorial',
          () => get().updateRevisionBranchStatus(projectId, branchId, status, reason),
        ),
        editorialActionId: null,
      })
    }
  },

  compareRevision: async (projectId, branchId) => {
    set({ editorialActionId: branchId, operationFailure: null, error: null })
    try {
      const comparison = await dataApi.compareRevision(projectId, branchId)
      set((current) => ({
        revisionComparisons: {
          ...current.revisionComparisons,
          [branchId]: comparison,
        },
        editorialActionId: null,
      }))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to compare revision'
      set({ error: message, editorialActionId: null })
    }
  },

  applyRevision: async (projectId, branchId) => {
    set({ editorialActionId: branchId, operationFailure: null, error: null })
    try {
      await dataApi.applyRevision(projectId, branchId)
      await get().refreshProjectData(projectId)
      set({ editorialActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to use revision as a draft'
      set({
        error: message,
        operationFailure: authorFailure(
          'Revision approval', error, 'editorial',
          () => get().applyRevision(projectId, branchId),
        ),
        editorialActionId: null,
      })
    }
  },

  createManuscript: async (projectId, title = '') => {
    set({ manuscriptActionId: 'create', operationFailure: null, error: null })
    try {
      await dataApi.createManuscript(projectId, title)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to create manuscript'
      set({
        error: message,
        operationFailure: authorFailure(
          'Manuscript creation', error, 'manuscript', () => get().createManuscript(projectId, title),
        ),
        manuscriptActionId: null,
      })
    }
  },

  assembleManuscript: async (projectId, manuscriptId, chapterDraftIds) => {
    set({ manuscriptActionId: manuscriptId, operationFailure: null, error: null })
    try {
      await dataApi.assembleManuscript(projectId, manuscriptId, chapterDraftIds)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to assemble manuscript'
      set({
        error: message,
        operationFailure: authorFailure(
          'Manuscript assembly', error, 'manuscript',
          () => get().assembleManuscript(projectId, manuscriptId, chapterDraftIds),
        ),
        manuscriptActionId: null,
      })
    }
  },

  reviewManuscript: async (projectId, manuscriptId) => {
    set({ manuscriptActionId: manuscriptId, operationFailure: null, error: null })
    try {
      await dataApi.reviewManuscript(projectId, manuscriptId)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to review manuscript'
      set({
        error: message,
        operationFailure: authorFailure(
          'Manuscript review', error, 'manuscript', () => get().reviewManuscript(projectId, manuscriptId),
        ),
        manuscriptActionId: null,
      })
    }
  },

  updateManuscriptStatus: async (projectId, manuscriptId, status) => {
    set({ manuscriptActionId: manuscriptId, operationFailure: null, error: null })
    try {
      await dataApi.updateManuscriptStatus(projectId, manuscriptId, status)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update manuscript'
      set({
        error: message,
        operationFailure: authorFailure(
          status === 'approved' ? 'Manuscript approval' : 'Manuscript status change',
          error, 'manuscript', () => get().updateManuscriptStatus(projectId, manuscriptId, status),
        ),
        manuscriptActionId: null,
      })
    }
  },

  rollbackManuscript: async (projectId, manuscriptId, versionId) => {
    set({ manuscriptActionId: manuscriptId, operationFailure: null, error: null })
    try {
      await dataApi.rollbackManuscript(projectId, manuscriptId, versionId)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to roll back manuscript'
      set({
        error: message,
        operationFailure: authorFailure(
          'Manuscript restore', error, 'manuscript',
          () => get().rollbackManuscript(projectId, manuscriptId, versionId),
        ),
        manuscriptActionId: null,
      })
    }
  },

  validateCanon: async (projectId) => {
    set({ manuscriptActionId: 'canon', operationFailure: null, error: null })
    try {
      await dataApi.validateCanon(projectId)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to validate canon'
      set({
        error: message,
        operationFailure: authorFailure(
          'Canon validation', error, 'canon', () => get().validateCanon(projectId),
        ),
        manuscriptActionId: null,
      })
    }
  },

  reviewCanon: async (projectId) => {
    set({ manuscriptActionId: 'canon', operationFailure: null, error: null })
    try {
      await dataApi.reviewCanon(projectId)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to review canon'
      set({
        error: message,
        operationFailure: authorFailure(
          'Canon review', error, 'canon', () => get().reviewCanon(projectId),
        ),
        manuscriptActionId: null,
      })
    }
  },

  updateCanonConflictStatus: async (projectId, conflictId, status) => {
    set({ manuscriptActionId: 'canon', operationFailure: null, error: null })
    try {
      await dataApi.updateCanonConflictStatus(projectId, conflictId, status)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update canon conflict'
      set({
        error: message,
        operationFailure: authorFailure(
          'Canon conflict update', error, 'canon',
          () => get().updateCanonConflictStatus(projectId, conflictId, status),
        ),
        manuscriptActionId: null,
      })
    }
  },

  updateCanonRecordActive: async (projectId, canonId, active) => {
    set({ manuscriptActionId: 'canon', operationFailure: null, error: null })
    try {
      await dataApi.updateCanonRecordActive(projectId, canonId, active)
      await get().refreshProjectData(projectId)
      set({ manuscriptActionId: null, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update canon authority'
      set({
        error: message,
        operationFailure: authorFailure(
          active ? 'Canon activation' : 'Canon deactivation', error, 'canon',
          () => get().updateCanonRecordActive(projectId, canonId, active),
        ),
        manuscriptActionId: null,
      })
    }
  },

  pollRunStatus: (projectId: string) => {
    void get().refreshProjectData(projectId)
    if (!get().projectEventSource) get().startLiveSync(projectId)
  },

  runWorkflow: async (projectId: string) => {
    get().stopPolling()
    set({ isRunningWorkflow: true, loading: true, error: null, selectedTab: 'workflow' })

    try {
      console.log('[projectStore] Workflow started for project:', projectId)
      const run = await workflowApi.run(projectId)
      set({ currentRun: run, loading: false, operationFailure: null, error: null })
      get().pollRunStatus(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run workflow'
      console.error('[projectStore] Workflow start failed:', message)
      set({ error: message, operationFailure: authorFailure('Project workflow', error, 'workflow', () => get().runWorkflow(projectId)), isRunningWorkflow: false, loading: false })
    }
  },

  runDiscussionCycle: async (projectId: string) => {
    get().stopPolling()
    set({ isRunningCycle: true, loading: true, error: null, selectedTab: 'workflow' })

    try {
      console.log('[projectStore] Discussion cycle started for project:', projectId)
      const run = await workflowApi.runCycle(projectId)
      set({ currentRun: run, loading: false, operationFailure: null, error: null })
      get().pollRunStatus(projectId)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run discussion cycle'
      console.error('[projectStore] Discussion cycle start failed:', message)
      set({ error: message, operationFailure: authorFailure('Writers’ Room cycle', error, 'discussion', () => get().runDiscussionCycle(projectId)), isRunningCycle: false, loading: false })
    }
  },

  sendMessage: async (projectId: string, content: string) => {
    set({ isSendingMessage: true, error: null })
    try {
      await projectsApi.addMessage(projectId, { content })
      set({ newChatMessage: '', isSendingMessage: false, operationFailure: null, error: null })
      await get().refreshProjectData(projectId)
      await get().fetchProjects() // To update updated_at for sorting
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to send message'
      set({ error: message, operationFailure: authorFailure('Author message', error, 'discussion', () => get().sendMessage(projectId, content)), isSendingMessage: false })
    }
  },

  recordDiscussionDecision: async (projectId: string, messageId: string, action: string, note = '') => {
    try {
      await dataApi.recordDiscussionDecision(projectId, messageId, { action, note })
      await get().refreshProjectData(projectId)
      set({ operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to record discussion decision'
      set({ error: message, operationFailure: authorFailure('Discussion decision', error, 'discussion', () => get().recordDiscussionDecision(projectId, messageId, action, note)) })
    }
  },

  submitAnswers: async (projectId: string, questionId: string, answer: string) => {
    set({ loading: true, error: null })
    try {
      await workflowApi.submitAnswer(projectId, { question_id: questionId, answer })
      await get().refreshProjectData(projectId)
      set({ loading: false, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to submit answer'
      set({ error: message, operationFailure: authorFailure('Question answer', error, 'questions', () => get().submitAnswers(projectId, questionId, answer)), loading: false })
    }
  },

  updateStoryVision: async (projectId: string, data: Record<string, unknown>) => {
    set({ loading: true, error: null })
    try {
      await dataApi.updateStoryVision(projectId, data)
      await get().refreshProjectData(projectId)
      set({ loading: false, operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update Story Vision'
      set({ error: message, operationFailure: authorFailure('Story Vision update', error, 'story-vision', () => get().updateStoryVision(projectId, data)), loading: false })
    }
  },

  fetchStoryRoom: async (projectId: string) => {
    try {
      const storyRoom = await dataApi.getStoryRoom(projectId)
      set({ storyRoom })
    } catch (error: unknown) {
      console.warn('[projectStore] Story Room fetch failed', error)
      set({ storyRoom: null })
    }
  },

  activateArc: async (projectId: string, arcId: string) => {
    try {
      await dataApi.activateArc(projectId, arcId)
      await get().refreshProjectData(projectId)
      set({ operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to activate arc'
      set({ error: message, operationFailure: authorFailure('Arc activation', error, 'arcs', () => get().activateArc(projectId, arcId)) })
    }
  },

  updateArcChecklist: async (projectId: string, itemId: string, status: string) => {
    try {
      const updated = await dataApi.updateArcChecklist(projectId, itemId, { status })
      if (updated?.development?.arc_id) {
        set((state) => ({
          arcDevelopmentReports: [
            ...state.arcDevelopmentReports.filter((report) => report.arc_id !== updated.development.arc_id),
            updated.development,
          ],
        }))
      }
      await get().refreshProjectData(projectId)
      set({ operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update checklist'
      set({ error: message, operationFailure: authorFailure('Arc checklist update', error, 'arc-development', () => get().updateArcChecklist(projectId, itemId, status)) })
    }
  },

  updatePlanningStatus: async (projectId: string, planType: 'scene' | 'chapter', planId: string, status: string) => {
    try {
      await dataApi.updatePlanningStatus(projectId, planType, planId, status)
      await get().refreshProjectData(projectId)
      set({ operationFailure: null, error: null })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to update planning approval'
      set({ error: message, operationFailure: authorFailure('Planning approval', error, 'drafting', () => get().updatePlanningStatus(projectId, planType, planId, status)) })
    }
  },

  setSelectedProject: (project) => {
    get().stopPolling()
    get().stopLiveSync()
    set({
      selectedProject: project,
      currentRun: null,
      runs: [],
      outputs: [],
      questions: [],
      outline: null,
      timelineMessages: [],
      cycles: [],
      characterBibles: [],
      narrativeWorldBible: null,
      plotThreads: [],
      continuityReports: [],
      scenes: [],
      sceneDrafts: [],
      chapterDrafts: [],
      relationships: [],
      themeRegistry: null,
      foreshadowing: [],
      discussionMessages: [],
      storyVision: null,
      storyArcs: [],
      powerSystem: null,
      characterJourneys: [],
      mysteries: [],
      aiInsights: null,
      factions: [],
      storyBible: null,
      storyTimeline: [],
      readinessItems: [],
      readinessReports: [],
      characterProgressions: [],
      knowledgeEntries: [],
      artifactRegistry: [],
      arcChecklists: [],
      arcDependencies: [],
      arcDevelopmentReports: [],
      chapterPlans: [],
      powerProgressions: [],
      knowledgeEvolutions: [],
      artifactEvolutions: [],
      foreshadowChains: [],
      storyRoom: null,
      editorialReports: [],
      editorialScores: [],
      revisionBranches: [],
      revisionVersions: [],
      revisionComparisons: {},
      manuscripts: [],
      manuscriptVersions: [],
      manuscriptReports: [],
      canonRecords: [],
      canonConflicts: [],
      chapterIntelligence: [],
      storyAudits: [],
      storyHealth: null,
      changeImpacts: [],
      orchestrationRun: null,
      contextPacket: null,
      cognitionEvents: [],
      observabilityEvents: [],
      isRunningWorkflow: false,
      isRunningCycle: false,
      isDraftingScenes: false,
      draftActionId: null,
      editorialActionId: null,
      manuscriptActionId: null,
      intelligenceActionId: null,
      paragraphs: [],
      isParagraphsLoading: false,
    })
    if (project) {
      get().startLiveSync(project.id)
    }
  },

  setSelectedTab: (tab) => set({ selectedTab: tab }),
  setNewProjectTitle: (value) => set({ newProjectTitle: value }),
  setNewProjectPremise: (value) => set({ newProjectPremise: value }),
  setNewProjectIdeaDump: (value) => set({ newProjectIdeaDump: value }),
  setNewProjectGenre: (value) => set({ newProjectGenre: value }),
  setNewProjectTone: (value) => set({ newProjectTone: value }),
  setNewProjectThemes: (value) => set({ newProjectThemes: value }),
  setNewProjectInspirations: (value) => set({ newProjectInspirations: value }),
  setNewProjectCharacterNotes: (value) => set({ newProjectCharacterNotes: value }),
  setNewProjectWorldNotes: (value) => set({ newProjectWorldNotes: value }),
  setNewProjectPlotNotes: (value) => set({ newProjectPlotNotes: value }),
  setNewProjectNotes: (value) => set({ newProjectNotes: value }),
  setNewChatMessage: (value) => set({ newChatMessage: value }),
}))
