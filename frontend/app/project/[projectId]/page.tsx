"use client"

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  BookOpen,
  Brain,
  CircleHelp,
  ClipboardCheck,
  Compass,
  Clock3,
  GitBranch,
  Globe2,
  Landmark,
  Lightbulb,
  Link2,
  ListTree,
  Loader2,
  MessageSquare,
  Network,
  PenLine,
  Play,
  Send,
  Settings,
  Search,
  Shield,
  Sparkles,
  Eye,
  FileSearch,
  Activity,
  Users,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import WorkflowFlow from '@/components/WorkflowFlow'
import OrchestrationInspector from '@/components/OrchestrationInspector'
import RelationshipGraph from '@/components/RelationshipGraph'
import ReadinessDashboard from '@/components/ReadinessDashboard'
import ArcBoard from '@/components/ArcBoard'
import KnowledgeView from '@/components/KnowledgeView'
import TimelineV2 from '@/components/TimelineV2'
import ArcDevelopmentWorkspace from '@/components/ArcDevelopmentWorkspace'
import DraftingWorkspace from '@/components/DraftingWorkspace'
import StoryRoom from '@/components/StoryRoom'
import EditorialWorkspace from '@/components/EditorialWorkspace'
import ManuscriptWorkspace from '@/components/ManuscriptWorkspace'
import CanonDashboard from '@/components/CanonDashboard'
import StoryHealthDashboard from '@/components/StoryHealthDashboard'
import Dashboard from '@/components/Dashboard'
import InteractiveNarrativeStudio from '@/components/InteractiveNarrativeStudio'
import WorkspaceIntelligenceBanner from '@/components/WorkspaceIntelligenceBanner'
import NarrativeProductionPipeline from '@/components/NarrativeProductionPipeline'
import NarrativeCritiquePanel from '@/components/NarrativeCritiquePanel'
import WorkspaceCompanion from '@/components/WorkspaceCompanion'
import StoryStudioPanel from '@/components/StoryStudioPanel'
import WritingWorkspace from '@/components/WritingWorkspace'
import PageGuidance from '@/components/PageGuidance'
import ActionableEmptyState from '@/components/ActionableEmptyState'
import KnowledgeSuggestionsPanel from '@/components/KnowledgeSuggestionsPanel'
import DecisionHistoryPanel from '@/components/DecisionHistoryPanel'
import StartYourNovel from '@/components/StartYourNovel'
import OperationFailureBanner from '@/components/OperationFailureBanner'
import ProjectBackupPanel from '@/components/ProjectBackupPanel'
import { ExplainabilityTimelineView, ProjectTimelineView } from '@/components/ProjectTimelines'
import { dataApi, rc6Api } from '@/lib/api'
import type { ApplicationKnowledge, WritingState } from '@/types'
import { useProjectStore, normalizeAgentName } from '@/store/projectStore'

const storyTeamRoleLabels: Record<string, string> = {
  storydevelopmentagent: 'Story development',
  pacingagent: 'Pacing review',
  readinessagent: 'Planning readiness',
  relationshipagent: 'Relationships',
  arcarchitectagent: 'Story arcs',
  story_architect: 'Story structure',
  narrativedirectoragent: 'Narrative direction',
  powersystemagent: 'Power system',
  knowledgeagent: 'Character knowledge',
}

function storyTeamRole(agentName?: string): string {
  const normalized = normalizeAgentName(agentName)
  if (storyTeamRoleLabels[normalized]) return storyTeamRoleLabels[normalized]
  return normalized
    .replace(/_?agent$/i, '')
    .replace(/_/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/^./, (letter) => letter.toUpperCase()) || 'Story team'
}

function activityOutcome(output: { content?: string; metadata?: Record<string, unknown> }): string {
  if (output.content?.trim()) return output.content
  const artifacts = output.metadata?.artifacts_created
  if (artifacts && typeof artifacts === 'object') {
    const entries = Object.entries(artifacts as Record<string, unknown>)
      .filter(([, count]) => Number(count) > 0)
      .map(([name, count]) => `${Number(count)} ${name.replace(/_/g, ' ')}`)
    if (entries.length) return `Completed this planning task and saved ${entries.join(', ')}.`
  }
  return 'Completed the review; no current planning records needed to change.'
}

const sections = [
  ['story-studio', 'Story Studio', MessageSquare],
  ['writing', 'Writing', BookOpen],
  ['vision', 'Story Vision', BookOpen],
  ['story-room', 'Story Room', MessageSquare],
  ['story-health', 'Story Health', Activity],
  ['guide', 'Creation Guide', Compass],
  ['discussion', 'Discussion Room', MessageSquare],
  ['characters', 'Characters', Users],
  ['world', 'World', Globe2],
  ['power', 'Power System', Shield],
  ['factions', 'Factions', Landmark],
  ['relationships', 'Relationships', Network],
  ['threads', 'Plot Threads', GitBranch],
  ['themes', 'Themes', Sparkles],
  ['mysteries', 'Mysteries', Lightbulb],
  ['readiness', 'Readiness', ClipboardCheck],
  ['knowledge', 'Knowledge', Eye],
  ['knowledge-graph', 'Knowledge Graph', Network],
  ['timeline', 'Timeline', Clock3],
  ['arcs', 'Arcs', ListTree],
  ['arc-development', 'Arc Development', ClipboardCheck],
  ['questions', 'Questions', CircleHelp],
  ['insights', 'AI Insights', Brain],
  ['drafting', 'Drafting', PenLine],
  ['editorial', 'Editorial', FileSearch],
  ['manuscript', 'Manuscript', BookOpen],
  ['canon', 'Canon', Shield],
  ['canon-queue', 'Canon Queue', ClipboardCheck],
  ['project-timeline', 'Project Timeline', Clock3],
  ['explainability-timeline', 'Story Health History', Activity],
  ['workflow', 'Workflow', Play],
  ['settings', 'Settings', Settings],
] as const

const navItems = [
  { id: 'dashboard', label: 'Dashboard', Icon: Activity },
  { id: 'story-studio', label: 'Story Studio', Icon: MessageSquare },
  { id: 'writing', label: 'Writing', Icon: PenLine },
  { id: 'assistant', label: 'AI Guidance', Icon: Brain },
  { id: 'toolbox', label: 'Toolbox', Icon: ListTree },
  { id: 'settings', label: 'Settings', Icon: Settings },
]

const sectionDefinitions = new Map<string, { label: string; Icon: typeof Activity }>(
  sections.map(([id, label, Icon]) => [id, { label, Icon }]),
)
const workspaceDestinations = new Set(['dashboard', ...sections.map(([id]) => id)])


function TraceLine({ item }: { item?: Record<string, unknown> | null }) {
  void item
  return null
}

function ListBlock({ title, values }: { title: string; values?: unknown }) {
  const items = asArray(values)
  return (
    <div className="min-w-0 rounded-md border p-3">
      <h3 className="truncate text-sm font-semibold">{title}</h3>
      <div className="mt-2 flex flex-wrap gap-2 text-sm">
        {items.length === 0 ? <span className="text-muted-foreground">None yet</span> : items.map((value, index) => (
          <span key={index} className="max-w-full break-words rounded bg-muted px-2 py-1">{formatValue(value)}</span>
        ))}
      </div>
    </div>
  )
}

export default function ProjectWorkspacePage() {
  const params = useParams<{ projectId: string }>()
  const projectId = params.projectId
  const [section, setSectionState] = useState<string>('dashboard')
  const setSection = useCallback((target: string) => {
    const destination = workspaceDestinations.has(target) ? target : 'dashboard'
    setSectionState(destination)
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href)
      url.searchParams.set('section', destination)
      window.history.pushState({ section: destination }, '', url)
    }
  }, [])
  const [toolboxOpen, setToolboxOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [companionLayout, setCompanionLayout] = useState<{ open: boolean; dock: 'left' | 'right' }>({ open: false, dock: 'right' })
  const [assistantInitialTab, setAssistantInitialTab] = useState<'assistant' | 'intelligence'>('assistant')
  const [developerMode, setDeveloperMode] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)
  const [commandQuery, setCommandQuery] = useState('')
  const [applicationKnowledge, setApplicationKnowledge] = useState<ApplicationKnowledge | null>(null)
  const [writingState, setWritingState] = useState<WritingState | null>(null)
  const [editorialFocusDraftId, setEditorialFocusDraftId] = useState<string | null>(null)
  const [recentSections, setRecentSections] = useState<string[]>([])
  const [customAnswers, setCustomAnswers] = useState<Record<string, string>>({})
  const [proposalAction, setProposalAction] = useState<{ messageId: string; action: string; note: string } | null>(null)
  const [storyKnowledgeCandidates, setStoryKnowledgeCandidates] = useState<any[]>([])
  const [editingVision, setEditingVision] = useState(false)
  const [visionDraft, setVisionDraft] = useState({
    premise: '',
    genre: '',
    themes: '',
    target_length: '',
    inspirations: '',
    audience: '',
    narrative_goals: '',
  })
  const handleCompanionOpenChange = useCallback((open: boolean, dock: 'left' | 'right') => {
    setCompanionLayout((current) => (
      current.open === open && current.dock === dock ? current : { open, dock }
    ))
  }, [])

  useEffect(() => {
    const handleHistoryNavigation = () => {
      const requested = new URLSearchParams(window.location.search).get('section') || 'dashboard'
      setSectionState(workspaceDestinations.has(requested) ? requested : 'dashboard')
    }
    handleHistoryNavigation()
    window.addEventListener('popstate', handleHistoryNavigation)
    return () => window.removeEventListener('popstate', handleHistoryNavigation)
  }, [])

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      const editing = target?.matches('input, textarea, [contenteditable="true"]')
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && section !== 'drafting' && !editing) {
        event.preventDefault()
        setCommandOpen(true)
      }
      if (event.key === 'Escape') setCommandOpen(false)
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [section])

  useEffect(() => {
    setToolboxOpen(window.innerWidth >= 1024)
  }, [])
  useEffect(() => {
    let active = true
    dataApi.getApplicationKnowledge(projectId).then((value) => active && setApplicationKnowledge(value)).catch(() => undefined)
    return () => { active = false }
  }, [projectId])
  useEffect(() => {
    let active = true
    dataApi.getWritingState(projectId).then((value) => active && setWritingState(value as WritingState)).catch(() => active && setWritingState(null))
    return () => { active = false }
  }, [projectId])
  useEffect(() => {
    const storageKey = `novelforge:recent-sections:${projectId}`
    setRecentSections((current) => {
      const previous = current.length ? current : (() => {
        try {
          return JSON.parse(window.localStorage.getItem(storageKey) || '[]') as string[]
        } catch {
          return []
        }
      })()
      const next = [section, ...previous.filter((item) => item !== section)].slice(0, 4)
      window.localStorage.setItem(storageKey, JSON.stringify(next))
      return next
    })
  }, [projectId, section])
  const {
    selectedProject,
    currentRun,
    outputs,
    questions,
    timelineMessages,
    cycles,
    storyTimeline,
    characterBibles,
    narrativeWorldBible,
    plotThreads,
    relationships,
    themeRegistry,
    scenes,
    sceneDrafts,
    chapterDrafts,
    continuityReports,
    discussionMessages,
    storyVision,
    storyArcs,
    readinessItems,
    readinessReports,
    characterProgressions,
    knowledgeEntries,
    artifactRegistry,
    arcChecklists,
    arcDependencies,
    arcDevelopmentReports,
    chapterPlans,
    powerProgressions,
    knowledgeEvolutions,
    artifactEvolutions,
    foreshadowChains,
    storyRoom,
    editorialReports,
    editorialScores,
    revisionBranches,
    revisionVersions,
    revisionComparisons,
    manuscripts,
    manuscriptVersions,
    manuscriptReports,
    canonRecords,
    canonConflicts,
    chapterIntelligence,
    storyAudits,
    storyHealth,
    changeImpacts,
    powerSystem,
    characterJourneys,
    mysteries,
    aiInsights,
    factions,
    orchestrationRun,
    cognitionEvents,
    newChatMessage,
    isSendingMessage,
    isRunningCycle,
    isRunningWorkflow,
    draftActionId,
    editorialActionId,
    manuscriptActionId,
    intelligenceActionId,
    operationFailure,
    fetchProject,
    refreshProjectData,
    setSelectedProject,
    stopLiveSync,
    sendMessage,
    recordDiscussionDecision,
    runDiscussionCycle,
    runWorkflow,
    generateSceneDraft,
    generateChapterDraft,
    updatePlanningStatus,
    updateDraftStatus,
    regenerateDraft,
    rollbackDraft,
    setSceneDraftFavorite,
    createWritersRoom,
    mergeSceneDrafts,
    requestEditorialReview,
    requestDialogueReview,
    createRevisionBranch,
    generateRevision,
    updateRevisionBranchStatus,
    compareRevision,
    applyRevision,
    createManuscript,
    assembleManuscript,
    reviewManuscript,
    updateManuscriptStatus,
    rollbackManuscript,
    validateCanon,
    reviewCanon,
    updateCanonConflictStatus,
    updateCanonRecordActive,
    dismissOperationFailure,
    retryOperationFailure,
    runStoryAudit,
    previewChangeImpact,
    updateChangeImpactStatus,
    submitAnswers,
    updateStoryVision,
    activateArc,
    updateArcChecklist,
    setNewChatMessage,
    stopPolling,
  } = useProjectStore()

  useEffect(() => {
    let mounted = true
    const load = async () => {
      await fetchProject(projectId)
      const project = useProjectStore.getState().selectedProject
      if (mounted && project) {
        setSelectedProject(project)
        // RC6 boots the related Story Bible, health, completeness, companion,
        // and project projections from one source so the first author-facing
        // render cannot mix stale snapshots from separate requests.
        await refreshProjectData(projectId)
      }
    }
    void load()
    return () => {
      mounted = false
      stopPolling()
      stopLiveSync()
    }
  }, [projectId, fetchProject, refreshProjectData, setSelectedProject, stopPolling, stopLiveSync])

  useEffect(() => {
    void rc6Api.touchProject(projectId)
  }, [projectId])

  const refreshAuthorWorkspace = useCallback(async () => {
    await Promise.all([
      refreshProjectData(projectId),
      dataApi.getStoryKnowledgeCandidates(projectId).then((value) => setStoryKnowledgeCandidates(Array.isArray(value) ? value : [])).catch(() => undefined),
    ])
  }, [projectId, refreshProjectData])

  useEffect(() => {
    void dataApi.getStoryKnowledgeCandidates(projectId)
      .then((value) => setStoryKnowledgeCandidates(Array.isArray(value) ? value : []))
      .catch(() => setStoryKnowledgeCandidates([]))
  }, [projectId])

  useEffect(() => {
    setVisionDraft({
      premise: storyVision?.premise || selectedProject?.premise || selectedProject?.idea_dump || '',
      genre: storyVision?.genre || selectedProject?.genre || '',
      themes: (storyVision?.themes || []).join(', '),
      target_length: storyVision?.target_length || '',
      inspirations: (storyVision?.inspirations || []).join(', '),
      audience: storyVision?.audience || '',
      narrative_goals: (storyVision?.narrative_goals || []).join(', '),
    })
  }, [storyVision, selectedProject])

  const totalEstimated = useMemo(() => storyArcs.reduce((sum, arc) => {
    const range = arc.chapter_range
    const rangeSize = range?.length === 2 && range[0] && range[1]
      ? Number(range[1]) - Number(range[0]) + 1
      : 0
    return sum + Number(arc.estimated_chapters || rangeSize || 0)
  }, 0), [storyArcs])
  const activeWorkflowGroup = useMemo(() => (
    Object.entries(applicationKnowledge?.groups || {}).find(([, ids]) => ids.includes(section))?.[0]
    || 'Shape the Story'
  ), [applicationKnowledge, section])
  const runIsActive = currentRun?.status === 'running' || currentRun?.status === 'queued'
  const busy = isRunningCycle || isRunningWorkflow || runIsActive
  const runStatusLabel = useMemo(() => {
    if (!currentRun) return null
    if (currentRun.status === 'running' || currentRun.status === 'queued') {
      return `Story team working · ${String(currentRun.metadata?.author_phase || 'Preparing the next story task')}`
    }
    if (currentRun.status === 'waiting_for_user') return 'Waiting for an important story choice'
    if (currentRun.status === 'failed') return 'Development needs attention'
    if (currentRun.status === 'interrupted') return 'Development stopped safely; completed work was kept'
    if (currentRun.status === 'completed') return 'Story development finished'
    return null
  }, [currentRun])

  const renderSection = () => {
    switch (section) {
      case 'story-studio':
        return <Panel title="Story Studio" testId="story-studio-workspace"><StoryStudioPanel projectId={projectId} onNavigate={setSection} onChanged={refreshAuthorWorkspace} /></Panel>
      case 'writing':
        return <Panel title="Writing" testId="writing-workspace-panel"><WritingWorkspace projectId={projectId} onNavigate={setSection} onEditChapter={(draftId) => { setEditorialFocusDraftId(draftId); setSection('editorial') }} /></Panel>
      case 'vision':
        return (
          <Panel title="Story Vision" testId="story-vision-panel">
            {editingVision ? (
              <div className="space-y-3">
                <Textarea value={visionDraft.premise} onChange={(event) => setVisionDraft({ ...visionDraft, premise: event.target.value })} placeholder="Premise" />
                <div className="grid gap-3 md:grid-cols-2">
                  {(['genre', 'themes', 'target_length', 'inspirations', 'audience', 'narrative_goals'] as const).map((field) => (
                    <label key={field} className="min-w-0 text-sm">
                      <span className="mb-1 block font-medium">{field.replaceAll('_', ' ')}</span>
                      <input
                        value={visionDraft[field]}
                        onChange={(event) => setVisionDraft({ ...visionDraft, [field]: event.target.value })}
                        className="h-10 w-full min-w-0 rounded-md border bg-background px-3"
                      />
                    </label>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={async () => {
                    await updateStoryVision(projectId, {
                      premise: visionDraft.premise,
                      genre: visionDraft.genre,
                      themes: splitValues(visionDraft.themes),
                      target_length: visionDraft.target_length,
                      inspirations: splitValues(visionDraft.inspirations),
                      audience: visionDraft.audience,
                      narrative_goals: splitValues(visionDraft.narrative_goals),
                    })
                    setEditingVision(false)
                  }}>Save</Button>
                  <Button variant="outline" onClick={() => setEditingVision(false)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="min-w-0 flex-1 break-words text-sm">{storyVision?.premise || selectedProject?.idea_dump || 'No persisted premise.'}</p>
                  <Button size="sm" variant="outline" onClick={() => setEditingVision(true)}>Edit</Button>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <ListBlock title="Themes" values={storyVision?.themes} />
                  <ListBlock title="Inspirations" values={storyVision?.inspirations} />
                  <ListBlock title="Narrative Goals" values={storyVision?.narrative_goals} />
                  <div className="rounded-md border p-3 text-sm">
                    <p><span className="font-medium">Genre:</span> {storyVision?.genre || selectedProject?.genre || 'Not set'}</p>
                    <p><span className="font-medium">Target length:</span> {storyVision?.target_length || 'Not set'}</p>
                    <p><span className="font-medium">Audience:</span> {storyVision?.audience || 'Not set'}</p>
                  </div>
                </div>
                <TraceLine item={storyVision as unknown as Record<string, unknown>} />
              </>
            )}
          </Panel>
        )
      case 'discussion': {
        const discussionItems = [...(discussionMessages.length ? discussionMessages : timelineMessages)].sort((left, right) => {
          const leftCycle = 'cycle' in left ? left.cycle : left.cycle_number
          const rightCycle = 'cycle' in right ? right.cycle : right.cycle_number
          if (rightCycle !== leftCycle) return rightCycle - leftCycle
          const leftTime = new Date(('created_at' in left ? left.created_at : left.timestamp) || 0).getTime()
          const rightTime = new Date(('created_at' in right ? right.created_at : right.timestamp) || 0).getTime()
          return rightTime - leftTime
        })
        return (
          <Panel title="Discussion Room" testId="discussion-room-panel">
            <div className="max-h-[56vh] space-y-3 overflow-y-auto pr-1">
              {discussionItems.map((message) => {
                const author = 'author' in message ? message.author : message.agent_name || (message.role === 'user' ? 'User' : 'System')
                const content = ('summary' in message ? message.summary : message.content) || ''
                const summary = content.length > 280 ? `${content.slice(0, 280)}...` : content
                const canAct = 'author' in message && message.role !== 'user'
                return (
                <div key={message.id} className="min-w-0 rounded-md border p-3 text-sm" data-testid="proposal-card">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold">{author}</span>
                    <span className="text-xs text-muted-foreground">Story team update</span>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">Summary</p>
                      <p className="mt-1 whitespace-pre-wrap break-words">{summary}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">Reasoning</p>
                      <p className="mt-1 break-words text-muted-foreground">{'reasoning' in message ? message.reasoning : 'Project timeline update'}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">Concerns</p>
                      <p className="mt-1 break-words text-muted-foreground">{'concerns' in message && message.concerns?.length ? message.concerns.join(' ') : 'No persisted concerns.'}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">Recommendation</p>
                      <p className="mt-1 break-words text-muted-foreground">{'recommendation' in message && message.recommendation ? message.recommendation : 'No persisted recommendation.'}</p>
                    </div>
                  </div>
                  <TraceLine item={message as unknown as Record<string, unknown>} />
                  {canAct ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {['approve', 'reject', 'modify', 'discuss', 'expand'].map((action) => (
                        <Button
                          key={action}
                          size="sm"
                          variant={action === 'approve' ? 'default' : 'outline'}
                          onClick={() => {
                            if (action === 'approve') {
                              void recordDiscussionDecision(projectId, message.id, action)
                            } else {
                              setProposalAction({ messageId: message.id, action, note: '' })
                            }
                          }}
                          disabled={'decision_status' in message && message.decision_status === 'approved'}
                          data-testid={`proposal-${action}`}
                        >
                          {action.charAt(0).toUpperCase() + action.slice(1)}
                        </Button>
                      ))}
                    </div>
                  ) : null}
                  {proposalAction?.messageId === message.id ? (
                    <div className="mt-3 min-w-0 rounded-md border p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">{proposalAction.action}</p>
                      <Textarea
                        value={proposalAction.note}
                        onChange={(event) => setProposalAction({ ...proposalAction, note: event.target.value })}
                        placeholder={proposalAction.action === 'modify' ? 'Write the revised proposal...' : 'Add context or a reason...'}
                        rows={3}
                        className="mt-2"
                      />
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          disabled={['reject', 'modify'].includes(proposalAction.action) && !proposalAction.note.trim()}
                          onClick={async () => {
                            await recordDiscussionDecision(projectId, message.id, proposalAction.action, proposalAction.note.trim())
                            setProposalAction(null)
                          }}
                        >
                          Confirm
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setProposalAction(null)}>Cancel</Button>
                      </div>
                    </div>
                  ) : null}
                </div>
                )
              })}
            </div>
            <div className="mt-4 flex min-w-0 gap-2">
              <Textarea
                value={newChatMessage}
                onChange={(event) => setNewChatMessage(event.target.value)}
                placeholder="Intervene in the writers room..."
                className="min-w-0"
                rows={3}
                disabled={busy || isSendingMessage}
              />
              <Button size="icon" aria-label="Send" onClick={() => newChatMessage.trim() && sendMessage(projectId, newChatMessage)} disabled={busy || isSendingMessage || !newChatMessage.trim()} data-testid="send-message">
                {isSendingMessage ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
              <Button size="icon" aria-label="Run discussion cycle" onClick={() => runDiscussionCycle(projectId)} disabled={busy} data-testid="workspace-run-discussion-cycle">
                {isRunningCycle ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              </Button>
            </div>
          </Panel>
        )
      }
      case 'story-room':
        return (
          <Panel title="Story Room" testId="story-room-panel">
            <StoryRoom room={storyRoom} />
          </Panel>
        )
      case 'story-health':
        return (
          <Panel title="Story Health Dashboard" testId="story-health-panel">
            <StoryHealthDashboard
              health={storyHealth}
              audits={storyAudits}
              chapters={chapterIntelligence}
              impacts={changeImpacts}
              busyId={intelligenceActionId}
              onAudit={() => void runStoryAudit(projectId)}
              onPreviewImpact={(changeType, target) => void previewChangeImpact(
                projectId,
                changeType,
                target,
              )}
              onImpactStatus={(impactId, status) => void updateChangeImpactStatus(
                projectId,
                impactId,
                status,
              )}
            />
            <div className="mt-5"><NarrativeCritiquePanel projectId={projectId} onNavigate={(target) => setSection(target)} /></div>
          </Panel>
        )
      case 'guide':
        return (
          <div className="space-y-6">
            <StartYourNovel
              projectId={projectId}
              autoOpen
              onNavigate={(target) => { setSection(target); setToolboxOpen(false) }}
              onChanged={refreshAuthorWorkspace}
            />
            <NarrativeProductionPipeline projectId={projectId} showGuide onNavigate={(target) => { setSection(target); setToolboxOpen(false) }} />
          </div>
        )
      case 'characters':
        return (
          <Panel title="Character Journey" testId="characters-panel">
            {characterBibles.filter((item) => item.authority_status !== 'candidate').length === 0 ? (
              <ActionableEmptyState
                projectId={projectId}
                area="character"
                label="Character"
                description="Start with a protagonist. You can enter a rough idea, ask AI for options, or import notes you already have."
                onGuide={() => setSection('guide')}
                onCreated={refreshAuthorWorkspace}
              />
            ) : <div className="grid gap-3 lg:grid-cols-2">
              {characterBibles.filter((item) => item.authority_status !== 'candidate').map((character, index) => {
                const journey = characterJourneys.find((item) => item.character_name === character.name)
                return (
                <div key={`${character.name}-${index}`} className="min-w-0 rounded-md border p-3 text-sm">
                  <h3 className="truncate font-semibold">{character.name}</h3>
                  <p className="text-muted-foreground">{character.role || character.current_status || 'Status not set'}</p>
                  <p className="mt-2 break-words">{character.description || journey?.growth || character.current_arc_state || 'No persisted description.'}</p>
                  <ListBlock title="Goals" values={character.goals} />
                  <ListBlock title="Fears" values={character.fears} />
                  <ListBlock title="Future Payoffs" values={character.future_payoffs || journey?.future_plans} />
                  <ListBlock
                    title="Arc Progression"
                    values={characterProgressions
                      .filter((item) => item.character === character.name)
                      .map((item) => `${storyArcs.find((arc) => arc.arc_id === item.arc_id)?.title || item.arc_id}: ${item.current_state} -> ${item.desired_state}`)}
                  />
                  <TraceLine item={character as unknown as Record<string, unknown>} />
                </div>
                )
              })}
            </div>}
            <KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['character']} onChanged={refreshAuthorWorkspace} />
          </Panel>
        )
      case 'world':
        return (
          <Panel title="World" testId="world-panel">
            {!narrativeWorldBible || Object.keys(narrativeWorldBible).length === 0 ? (
              <ActionableEmptyState
                projectId={projectId}
                area="world"
                label="World detail"
                description="Describe only what you know today. The world can grow and every choice remains editable."
                onGuide={() => setSection('guide')}
                onCreated={refreshAuthorWorkspace}
              />
            ) : <div className="grid gap-3 lg:grid-cols-2">
              <ListBlock title="World Rules" values={narrativeWorldBible?.world_rules} />
              <ListBlock title="Locations" values={asArray(narrativeWorldBible?.locations).map((item) => formatNamedValue(item, 'Location'))} />
              <ListBlock title="Religions" values={asArray(narrativeWorldBible?.religion || narrativeWorldBible?.religions).map((item) => formatNamedValue(item, 'Religion'))} />
              <ListBlock title="Historical Events" values={asArray(narrativeWorldBible?.history || narrativeWorldBible?.historical_events).map((item) => formatNamedValue(item, 'Event'))} />
            </div>}
            <KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['world_fact']} onChanged={refreshAuthorWorkspace} />
          </Panel>
        )
      case 'power':
        return (
          <Panel title="Power System" testId="power-system-panel">
            {!powerSystem || Object.keys(powerSystem).length === 0 ? (
              <ActionableEmptyState
                projectId={projectId}
                area="power"
                label="Power rule"
                description="Capture the rules, limits, and costs that keep extraordinary abilities believable."
                onGuide={() => setSection('guide')}
                onCreated={refreshAuthorWorkspace}
              />
            ) : <div className="grid gap-3 lg:grid-cols-2">
              <ListBlock title="Ranks" values={powerSystem?.ranks} />
              <ListBlock title="Levels" values={powerSystem?.levels} />
              <ListBlock title="Skills" values={powerSystem?.skills} />
              <ListBlock title="Classes" values={powerSystem?.classes} />
              <ListBlock title="Evolution Paths" values={powerSystem?.evolution_paths} />
              <ListBlock title="Limitations" values={powerSystem?.limitations} />
              <ListBlock title="Resources" values={powerSystem?.resources} />
              <ListBlock title="Costs" values={powerSystem?.costs} />
            </div>}
            {powerSystem && Object.keys(powerSystem).length > 0 ? <p className="mt-3 break-words text-sm">{powerSystem?.cultivation || powerSystem?.progression_logic || 'No progression logic recorded yet.'}</p> : null}
          </Panel>
        )
      case 'factions':
        return factions.length === 0 ? <Panel title="Factions" testId="factions-panel"><ActionableEmptyState projectId={projectId} area="faction" label="Faction" description="Create a group whose goals, loyalties, or conflicts shape the story." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /></Panel> : <CollectionPanel title="Factions" testId="factions-panel" items={factions.map((faction) => ({ title: faction.name, body: faction.goals?.join(' ') || faction.agenda, footer: [faction.leader && `Leader: ${faction.leader}`, faction.influence && `Influence: ${faction.influence}`].filter(Boolean).join(' · '), trace: faction }))} />
      case 'relationships':
        return (
          <Panel title="Relationships" testId="relationships-panel">
            {relationships.filter((item) => item.authority_status !== 'candidate').length === 0 ? <ActionableEmptyState projectId={projectId} area="relationship" label="Relationship" description="Record a friendship, rivalry, family bond, debt, or changing alliance." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /> : <RelationshipGraph relationships={relationships.filter((item) => item.authority_status !== 'candidate')} />}
            <KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['relationship']} onChanged={refreshAuthorWorkspace} />
          </Panel>
        )
      case 'threads':
        return <Panel title="Plot Threads" testId="threads-panel">{plotThreads.filter((item) => item.authority_status !== 'candidate').length === 0 ? <ActionableEmptyState projectId={projectId} area="plot_thread" label="Plot thread" description="Track a promise, problem, mystery, or subplot so it is developed and resolved." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /> : <CollectionPanel title="Plot Threads" testId="threads-collection" items={plotThreads.filter((item) => item.authority_status !== 'candidate').map((thread) => ({ title: thread.title, body: thread.description, footer: `Status: ${thread.status}` }))} />}<KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['plot_thread']} onChanged={refreshAuthorWorkspace} /></Panel>
      case 'themes':
        return (
          <Panel title="Themes" testId="themes-panel">
            {asArray(themeRegistry?.themes).length + asArray(themeRegistry?.motifs).length + asArray(themeRegistry?.symbols).length === 0 ? (
              <ActionableEmptyState projectId={projectId} area="theme" label="Theme" description="Name the idea or question your novel keeps exploring. It can change as the draft develops." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} />
            ) : <div className="grid gap-3 md:grid-cols-3">
              <ListBlock title="Themes" values={themeRegistry?.themes} />
              <ListBlock title="Motifs" values={themeRegistry?.motifs} />
              <ListBlock title="Symbols" values={themeRegistry?.symbols} />
            </div>}
          </Panel>
        )
      case 'mysteries':
        return <Panel title="Mystery Registry" testId="mysteries-panel">{mysteries.filter((item) => item.authority_status !== 'candidate').length === 0 ? <ActionableEmptyState projectId={projectId} area="mystery" label="Mystery" description="Write the question readers should want answered. You can decide the answer later." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /> : <CollectionPanel title="Mystery Registry" testId="mysteries-collection" items={mysteries.filter((item) => item.authority_status !== 'candidate').map((mystery) => ({ title: mystery.question || mystery.setup || 'Untitled mystery', body: mystery.truth || mystery.expected_payoff, footer: `${mystery.status || (mystery.resolved ? 'resolved' : 'open')} · Reveal: ${mystery.reveal_target || 'not scheduled'}`, trace: mystery }))} />}<KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['mystery']} onChanged={refreshAuthorWorkspace} /></Panel>
      case 'readiness':
        return (
          <Panel title="Story Readiness" testId="readiness-panel">
            <ReadinessDashboard items={readinessItems} reports={readinessReports} arcs={storyArcs} />
          </Panel>
        )
      case 'knowledge':
        return (
          <Panel title="Knowledge Layers" testId="knowledge-panel">
            <KnowledgeView entries={knowledgeEntries} />
            <KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['knowledge_change', 'artifact', 'author_intention']} onChanged={refreshAuthorWorkspace} />
            <div className="mt-4">
              <CollectionPanel
                title="Approved Canon"
                testId="knowledge-approved-canon"
                items={canonRecords.filter((record) => record.active !== false).map((record) => ({
                  title: record.subject || `${record.canon_type}: ${record.field}`,
                  body: record.value || record.fact,
                  footer: record.source ? `Source: ${record.source}` : 'Approved story knowledge',
                }))}
                bare
              />
            </div>
            <div className="mt-4">
              <CollectionPanel
                title="Linked Artifacts"
                testId="knowledge-artifacts"
                items={artifactRegistry.map((artifact) => ({
                  title: artifact.item,
                  body: artifact.power,
                  footer: `Owner: ${artifact.owner || 'unassigned'} · Hidden: ${artifact.hidden_power || 'none recorded'}`,
                }))}
                bare
              />
            </div>
          </Panel>
        )
      case 'knowledge-graph':
        return (
          <InteractiveNarrativeStudio
            projectId={projectId}
            characters={characterBibles}
            activeSurface={section}
            initialTab="graph"
            onNavigate={(target) => setSection(target)}
            onRefresh={refreshAuthorWorkspace}
          />
        )
      case 'timeline':
        return (
          <Panel title="Timeline V2" testId="story-timeline-panel">
            {storyTimeline.filter((item) => item.authority_status !== 'candidate').length === 0 ? <ActionableEmptyState projectId={projectId} area="timeline" label="Story event" description="Record what happens and when. Exact dates are optional." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /> : <TimelineV2 entries={storyTimeline.filter((item) => item.authority_status !== 'candidate')} arcs={storyArcs} />}
            <KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['timeline_event']} onChanged={refreshAuthorWorkspace} />
          </Panel>
        )
      case 'arcs':
        return (
          <Panel title={`Arc Board (${totalEstimated || 0} planned chapters)`} testId="arcs-panel">
            {storyArcs.length === 0 ? <ActionableEmptyState projectId={projectId} area="arc" label="Arc" description="Describe the first meaningful stretch of the story—from a new problem to a changed situation." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /> : <ArcBoard arcs={storyArcs} />}
            <KnowledgeSuggestionsPanel projectId={projectId} candidates={storyKnowledgeCandidates} types={['arc']} onChanged={refreshAuthorWorkspace} />
          </Panel>
        )
      case 'arc-development':
        return (
          <Panel title="Arc Development Workspace" testId="arc-development-panel">
            <ArcDevelopmentWorkspace
              arcs={storyArcs}
              reports={arcDevelopmentReports}
              checklists={arcChecklists}
              dependencies={arcDependencies}
              chapters={chapterPlans}
              scenes={scenes}
              characterProgressions={characterProgressions}
              powerProgressions={powerProgressions}
              knowledge={knowledgeEntries}
              knowledgeEvolutions={knowledgeEvolutions}
              foreshadowChains={foreshadowChains}
              artifacts={artifactRegistry}
              artifactEvolutions={artifactEvolutions}
              onActivate={(arcId) => void activateArc(projectId, arcId)}
              onChecklistStatus={(itemId, status) => updateArcChecklist(projectId, itemId, status)}
              sceneDrafts={sceneDrafts}
              chapterDrafts={chapterDrafts}
              continuityReports={continuityReports}
              draftableArcIds={arcDevelopmentReports.filter((report) => report.draftable).map((report) => report.arc_id)}
              draftActionId={draftActionId}
              onGenerateScene={(sceneId, options) => void generateSceneDraft(projectId, sceneId, options)}
              onGenerateChapter={(chapterPlanId) => void generateChapterDraft(projectId, chapterPlanId)}
              onPlanStatus={(type, planId, status) => updatePlanningStatus(projectId, type, planId, status)}
              onDraftStatus={(type, draftId, status, reason) => void updateDraftStatus(projectId, type, draftId, status, reason)}
              onRegenerateDraft={(type, draftId, reason, operation) => void regenerateDraft(projectId, type, draftId, reason, operation)}
              onRollbackDraft={(type, draftId) => void rollbackDraft(projectId, type, draftId)}
            />
          </Panel>
        )
      case 'questions':
        return (
          <Panel title="Questions" testId="questions-panel">
            <div className="space-y-3">
              {questions.length === 0 ? <ActionableEmptyState projectId={projectId} area="mystery" label="Story question" description="When the story needs your judgment, questions appear here. You can also record an unresolved idea now." onGuide={() => setSection('guide')} onCreated={refreshAuthorWorkspace} /> : questions.map((question) => (
                <div key={question.id} className="min-w-0 rounded-md border p-3 text-sm" data-testid="question-item">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="whitespace-pre-wrap break-words font-semibold">{question.text}</p>
                    {!question.answered ? <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${question.blocking ? 'bg-amber-100 text-amber-800' : 'bg-muted text-muted-foreground'}`}>{question.blocking ? 'Required to continue' : 'Optional idea'}</span> : null}
                  </div>
                  {!question.answered && !question.blocking ? <p className="mt-1 text-xs text-muted-foreground">You can answer this later. It does not stop story development.</p> : null}
                  {question.answered ? <p className="text-muted-foreground">Answered: {question.answer}</p> : (
                    <div className="mt-3 space-y-3">
                      <div className="flex min-w-0 flex-wrap gap-2">
                        {question.choices.map((choice) => (
                          <Button key={choice} size="sm" variant="outline" className="h-auto min-h-9 max-w-full whitespace-normal text-left" data-testid="answer-choice" onClick={() => submitAnswers(projectId, question.id, choice)}>
                            {choice}
                          </Button>
                        ))}
                        {question.default_recommendation || question.choices[0] ? (
                          <Button size="sm" data-testid="use-default-answer" onClick={() => submitAnswers(projectId, question.id, question.default_recommendation || question.choices[0])}>
                            Use Default
                          </Button>
                        ) : null}
                        <Button size="sm" variant="outline" onClick={() => sendMessage(projectId, `Discuss this question further: ${question.text}`)}>
                          Discuss
                        </Button>
                      </div>
                      <div className="flex min-w-0 flex-wrap gap-2">
                        <Textarea
                          value={customAnswers[question.id] || ''}
                          onChange={(event) => setCustomAnswers((current) => ({ ...current, [question.id]: event.target.value }))}
                          placeholder="Custom answer..."
                          className="min-h-10 min-w-[240px] flex-1"
                          rows={2}
                        />
                        <Button
                          variant="outline"
                          disabled={!customAnswers[question.id]?.trim()}
                          onClick={() => submitAnswers(projectId, question.id, customAnswers[question.id].trim())}
                        >
                          Submit
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <DecisionHistoryPanel projectId={projectId} onChanged={refreshAuthorWorkspace} />
            </div>
          </Panel>
        )
      case 'insights':
        return (
          <Panel title="AI Insights" testId="ai-insights-panel">
            <div className="grid gap-3 lg:grid-cols-2">
              <ListBlock title="Agent Concerns" values={aiInsights?.agent_concerns} />
              <ListBlock title="Missing Story Areas" values={aiInsights?.missing_story_areas} />
              <ListBlock title="Weak Characters" values={aiInsights?.weak_characters} />
              <ListBlock title="Weak Pacing" values={aiInsights?.weak_pacing} />
              <ListBlock title="Potential Contradictions" values={aiInsights?.potential_contradictions} />
              <ListBlock title="Suggested Improvements" values={aiInsights?.suggested_improvements} />
            </div>
            <TraceLine item={aiInsights as unknown as Record<string, unknown>} />
          </Panel>
        )
      case 'drafting':
        return (
          <Panel title="Controlled Drafting" testId="drafting-panel">
            {scenes.length === 0 && chapterPlans.length === 0 ? (
              <ActionableEmptyState
                projectId={projectId}
                area={storyArcs.length === 0 ? 'arc' : 'scene'}
                label={storyArcs.length === 0 ? 'Arc' : 'Scene'}
                description={storyArcs.length === 0 ? 'A short first arc gives the drafting workspace enough direction to help.' : 'Describe who is present, what they want, and what changes by the end of the scene.'}
                onGuide={() => setSection('guide')}
                onCreated={refreshAuthorWorkspace}
              />
            ) : <DraftingWorkspace
              arcs={storyArcs}
              chapters={chapterPlans}
              scenes={scenes}
              sceneDrafts={sceneDrafts}
              chapterDrafts={chapterDrafts}
              continuityReports={continuityReports}
              editorialReports={editorialReports}
              editorialScores={editorialScores}
              draftableArcIds={arcDevelopmentReports.filter((report) => report.draftable).map((report) => report.arc_id)}
              busyId={draftActionId}
              onGenerateScene={(sceneId, options) => void generateSceneDraft(projectId, sceneId, options)}
              onGenerateChapter={(chapterPlanId) => void generateChapterDraft(projectId, chapterPlanId)}
              onPlanStatus={(type, planId, status) => updatePlanningStatus(projectId, type, planId, status)}
              onStatus={(type, draftId, status, reason) => void updateDraftStatus(projectId, type, draftId, status, reason)}
              onRegenerate={(type, draftId, reason, operation) => void regenerateDraft(projectId, type, draftId, reason, operation)}
              onRollback={(type, draftId) => void rollbackDraft(projectId, type, draftId)}
              onFavorite={(draftId, favorite) => void setSceneDraftFavorite(projectId, draftId, favorite)}
              onNavigate={setSection}
              onWritersRoom={(draftId, instruction) => void createWritersRoom(projectId, draftId, instruction)}
              onMerge={(leftDraftId, rightDraftId, mergedText) => void mergeSceneDrafts(projectId, leftDraftId, rightDraftId, mergedText)}
            />}
          </Panel>
        )
      case 'editorial':
        return (
          <Panel title="Editorial Intelligence" testId="editorial-panel">
            <EditorialWorkspace
              arcs={storyArcs}
              chapters={chapterPlans}
              scenes={scenes}
              sceneDrafts={sceneDrafts}
              chapterDrafts={chapterDrafts}
              reports={editorialReports}
              scores={editorialScores}
              branches={revisionBranches}
              versions={revisionVersions}
              comparisons={revisionComparisons}
              focusDraftId={editorialFocusDraftId}
              busyId={editorialActionId}
              onReview={(subjectType, subjectId) => void requestEditorialReview(projectId, subjectType, subjectId)}
              onDialogue={(draftType, draftId) => void requestDialogueReview(projectId, draftType, draftId)}
              onCreateBranch={(draftType, draftId, title, revisionPass) => void createRevisionBranch(projectId, draftType, draftId, title, revisionPass)}
              onGenerateRevision={(branchId, reason, revisionPass) => void generateRevision(projectId, branchId, reason, revisionPass)}
              onBranchStatus={(branchId, status, reason) => void updateRevisionBranchStatus(projectId, branchId, status, reason)}
              onCompare={(branchId) => void compareRevision(projectId, branchId)}
              onApplyRevision={(branchId) => void applyRevision(projectId, branchId)}
            />
          </Panel>
        )
      case 'manuscript':
        return (
          <Panel title="Manuscript Workspace" testId="manuscript-panel">
            <ManuscriptWorkspace
              projectId={projectId}
              manuscripts={manuscripts}
              versions={manuscriptVersions}
              reports={manuscriptReports}
              chapterDrafts={chapterDrafts}
              busyId={manuscriptActionId}
              onCreate={(title) => void createManuscript(projectId, title)}
              onAssemble={(manuscriptId, chapterDraftIds) => void assembleManuscript(projectId, manuscriptId, chapterDraftIds)}
              onReview={(manuscriptId) => void reviewManuscript(projectId, manuscriptId)}
              onStatus={(manuscriptId, status) => void updateManuscriptStatus(projectId, manuscriptId, status)}
              onRollback={(manuscriptId, versionId) => void rollbackManuscript(projectId, manuscriptId, versionId)}
              onNavigate={setSection}
            />
          </Panel>
        )
      case 'canon':
        return (
          <Panel title="Canon Governance" testId="canon-panel">
            <CanonDashboard
              projectId={projectId}
              records={canonRecords}
              conflicts={canonConflicts}
              reports={manuscriptReports.filter((report) => report.report_type === 'canon_review')}
              busyId={manuscriptActionId}
              onValidate={() => void validateCanon(projectId)}
              onReview={() => void reviewCanon(projectId)}
              onConflictStatus={(conflictId, status) => void updateCanonConflictStatus(projectId, conflictId, status)}
              onRecordActive={(canonId, active) => void updateCanonRecordActive(projectId, canonId, active)}
              onOpenQueue={() => setSection('canon-queue')}
            />
          </Panel>
        )
      case 'canon-queue':
        return (
          <Panel title="Canon Proposal Queue" testId="canon-queue-panel">
            <InteractiveNarrativeStudio projectId={projectId} characters={characterBibles} activeSurface="canon-queue" initialTab="proposals" onNavigate={(target) => setSection(target)} onRefresh={refreshAuthorWorkspace} />
          </Panel>
        )
      case 'project-timeline':
        return <Panel title="Project Timeline" testId="project-timeline-panel"><ProjectTimelineView projectId={projectId} onNavigate={(target) => setSection(target)} /></Panel>
      case 'explainability-timeline':
        return <Panel title="Story Health History" testId="explainability-timeline-panel"><ExplainabilityTimelineView projectId={projectId} onNavigate={(target) => setSection(target)} /></Panel>
      case 'workflow':
        return (
          <Panel title="Project Activity" testId="workflow-panel">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border bg-sky-50/60 p-3" aria-live="polite"><p className="text-xs font-semibold uppercase tracking-wider text-sky-700">Current activity</p><p className="mt-1 font-semibold">{currentRun?.status === 'running' ? 'Your story team is working' : currentRun?.status === 'failed' ? 'The last task needs attention' : currentRun?.status === 'interrupted' ? 'Development stopped safely' : 'Ready for your next step'}</p><p className="mt-1 text-sm text-muted-foreground">{currentRun?.status === 'running' ? String(currentRun.metadata?.author_phase || 'Preparing the next story task') : currentRun?.status === 'failed' ? (currentRun.error || 'Completed work was saved. You can retry from the Dashboard.') : currentRun?.status === 'interrupted' ? 'Completed work was saved before NovelForge restarted.' : 'Start from the Dashboard when you want the story team to continue.'}</p>{currentRun?.metadata?.progress_total ? <p className="mt-2 text-xs font-medium">{String(currentRun.metadata.progress_completed || 0)} of {String(currentRun.metadata.progress_total)} tasks finished</p> : null}</div>
              <div className="rounded-lg border p-3"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent outcomes</p><p className="mt-1 text-2xl font-bold">{outputs.slice(-8).length}</p><p className="text-sm text-muted-foreground">story-team summaries ready to review</p></div>
                <div className="rounded-lg border p-3"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Where results go</p><p className="mt-1 text-sm">Saved results appear in their owning workspace and Project Timeline. Important canon changes still wait for your approval.</p></div>
            </div>
            {outputs.length ? <p className="mt-3 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-950">These are snapshots from the pass that produced them. Later author decisions or approvals may have changed the live story; each owning workspace shows the current authoritative state.</p> : null}
            <div className="mt-4 space-y-3">
              {!outputs.length ? <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">Project activity will appear here after the story team completes its first task.</p> : null}
              {outputs.slice(-8).map((output) => (
                <div key={output.id} className="rounded-md border p-3 text-sm" data-testid="agent-output">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-semibold">{storyTeamRole(output.agent_name)}</p>
                    <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">{String(output.metadata.status || 'completed') === 'completed' ? 'Saved snapshot' : 'Needs attention'}</span>
                  </div>
                    <p className="mt-2 whitespace-pre-wrap break-words">{activityOutcome(output)}</p>
                </div>
              ))}
            </div>
            <Button className="mt-4" size="sm" variant="outline" onClick={() => setDeveloperMode((value) => !value)} aria-expanded={developerMode}>{developerMode ? 'Hide Developer Mode' : 'Developer Mode'}</Button>
            {developerMode ? <div className="mt-4 rounded-lg border border-dashed p-3" data-testid="workflow-developer-details"><OrchestrationInspector plan={orchestrationRun} /><div className="mt-4"><WorkflowFlow currentRun={currentRun} cycles={cycles} outputs={outputs} selectedAgents={orchestrationRun?.selected_agents || []} /></div><div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4"><Metric label="Recent outputs" value={String(outputs.length)} /><Metric label="Story-team calls" value={String(orchestrationRun?.actual_agent_calls || 0)} /><Metric label="Estimated cost" value={`$${Number(orchestrationRun?.actual_cost_usd || 0).toFixed(4)}`} /><Metric label="Recorded activity" value={String(cognitionEvents.length)} /></div></div> : null}
          </Panel>
        )
      case 'settings':
        return (
          <Panel title="Settings" testId="workspace-settings-panel">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border p-4"><h3 className="font-semibold">AI connections</h3><p className="mt-2 text-sm text-muted-foreground">Connect and verify the AI service NovelForge uses for project work.</p></div>
              <div className="rounded-lg border p-4"><h3 className="font-semibold">Protected credentials</h3><p className="mt-2 text-sm text-muted-foreground">Stored credentials remain masked and are never returned to this workspace.</p></div>
              <div className="rounded-lg border p-4"><h3 className="font-semibold">Advanced controls</h3><p className="mt-2 text-sm text-muted-foreground">Provider routing and diagnostics stay inside the Settings page’s Developer Mode.</p></div>
            </div>
            <Button asChild className="mt-4"><a href="/settings"><Settings className="mr-2 h-4 w-4" />Open AI Connections & Settings</a></Button>
            <ProjectBackupPanel projectId={projectId} />
          </Panel>
        )
      default:
        return null
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-background text-foreground transition-colors duration-300">
      <div className="flex h-screen min-w-0 overflow-hidden">
        {/* Leftmost Navigation Sidebar */}
        <aside className="flex w-16 shrink-0 flex-col items-center border-r bg-card py-4">
          <div className="mb-8 flex flex-col items-center">
            <Link href="/projects" className="text-xs font-bold text-primary hover:underline">
              Projects
            </Link>
          </div>
          <nav className="flex flex-1 flex-col gap-4">
            {navItems.map(({ id, label, Icon }) => {
              const active = id === 'toolbox' 
                ? toolboxOpen 
                : id === 'assistant' 
                  ? assistantOpen 
                  : section === id && !toolboxOpen;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    if (id === 'toolbox') {
                      setToolboxOpen(!toolboxOpen);
                    } else if (id === 'assistant') {
                      setAssistantInitialTab('assistant')
                      setAssistantOpen(!assistantOpen);
                    } else {
                      setSection(id);
                    }
                  }}
                  title={label}
                  aria-label={label}
                  className={`flex h-12 w-12 items-center justify-center rounded-xl transition-all ${
                    active 
                      ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20 scale-105' 
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  }`}
                  data-testid={`nav-${id}`}
                >
                  <Icon className="h-5 w-5" />
                </button>
              );
            })}
          </nav>
          <div className="mt-auto">
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-violet-500 to-fuchsia-500 flex items-center justify-center text-xs font-semibold text-white">
              NF
            </div>
          </div>
        </aside>

        {/* Toolbox Drawer Panel (Slides open next to sidebar if toggled) */}
        {toolboxOpen && (
          <aside className="w-64 border-r bg-card flex flex-col shrink-0">
            <div className="p-4 border-b">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Toolbox</h2>
            </div>
            <nav className="flex-1 overflow-y-auto p-2">
              {recentSections.length > 1 ? (
                <div className="mb-3 border-b pb-3" data-testid="recent-destinations">
                  <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Recent</p>
                  {recentSections.slice(1).map((id) => {
                    const definition = sectionDefinitions.get(id)
                    if (!definition) return null
                    const RecentIcon = definition.Icon
                    return <button key={id} type="button" onClick={() => setSection(id)} className="mb-1 flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-xs text-muted-foreground hover:bg-accent/50"><RecentIcon className="h-3.5 w-3.5" /><span className="truncate">{definition.label}</span></button>
                  })}
                </div>
              ) : null}
              {(applicationKnowledge
                ? Object.entries(applicationKnowledge.groups).map(([group, ids]) => ({
                    group,
                    items: ids.map((id) => ({ id, definition: sectionDefinitions.get(id) })).filter((item) => item.definition),
                  })).filter((group) => group.items.length)
                : [{ group: 'Workspace', items: sections.map(([id, label, Icon]) => ({ id, definition: { label, Icon } })) }]
              ).map(({ group, items }) => {
                const groupContent = <div className="mb-3">
                  <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{group}</p>
                  {items.map(({ id, definition }) => {
                    const { label, Icon } = definition!
                    return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => {
                      setSection(id);
                    }}
                    className={`mb-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                      section === id 
                        ? 'bg-accent text-accent-foreground font-medium' 
                        : 'hover:bg-accent/50 text-muted-foreground'
                    }`}
                    data-testid={`section-${id}`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="truncate">{label}</span>
                  </button>
                    )
                  })}
                </div>
                if (group !== 'More Tools') return <div key={group}>{groupContent}</div>
                return (
                  <details key={group} className="rounded-lg border border-dashed" data-testid="advanced-tools">
                    <summary className="cursor-pointer list-none px-3 py-3 text-xs font-semibold text-muted-foreground">More tools and project details</summary>
                    {groupContent}
                  </details>
                )
              })}
            </nav>
          </aside>
        )}

        {/* Main Workspace Viewport */}
        <section data-testid="workspace-main-viewport" className={`flex-1 min-w-0 flex flex-col overflow-y-auto bg-background transition-[padding] duration-200 ${
          companionLayout.open
            ? companionLayout.dock === 'right'
              ? toolboxOpen ? 'workspace-companion-safe-right-constrained' : 'workspace-companion-safe-right'
              : toolboxOpen ? 'workspace-companion-safe-left-constrained' : 'workspace-companion-safe-left'
            : ''
        }`}>
          <header className="px-3 py-3 sm:px-6 sm:py-4 border-b flex items-center justify-between shrink-0 gap-2">
            <div className="min-w-0">
              <h1 className="min-w-0 text-base sm:text-xl font-bold flex items-center gap-2">
                <span className="truncate">{selectedProject?.project_name || selectedProject?.title || 'Project Workspace'}</span>
                <span className="hidden xl:inline-flex text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded-full border border-border">
                  Author-controlled story workspace
                </span>
              </h1>
              <p className="mt-1 truncate text-xs text-muted-foreground" data-testid="story-title-label">
                Novel: {selectedProject?.story_title || 'Untitled'}
              </p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground" data-testid="workspace-breadcrumb">
                Project / {activeWorkflowGroup} / {section === 'dashboard' ? 'Dashboard' : sectionDefinitions.get(section)?.label || 'Workspace'}
              </p>
              {runStatusLabel && (
                <p className="text-xs text-muted-foreground mt-0.5 truncate" data-testid="run-status">
                  {runStatusLabel}
                </p>
              )}
            </div>
            {/* Quick Actions in Header */}
            <div className="flex gap-2 shrink-0">
              <Button size="sm" variant="outline" onClick={() => runWorkflow(projectId)} disabled={busy} data-testid="run-workflow">
                {busy ? <Loader2 className="h-4 w-4 animate-spin sm:mr-2" /> : <Play className="h-4 w-4 sm:mr-2" />}
                <span className="hidden sm:inline">{runIsActive ? 'Developing Story' : 'Develop Story'}</span>
              </Button>
            </div>
          </header>

          <PageGuidance
            surface={applicationKnowledge?.surfaces[section === 'editor' ? 'drafting' : section] || {
              surface_id: section,
              label: section === 'dashboard' ? 'Dashboard' : sectionDefinitions.get(section)?.label || 'Workspace',
              group: activeWorkflowGroup,
              aliases: [],
              purpose: 'Understand this workspace, its current status, and the next useful author action.',
              why_it_matters: 'Each workspace supports one part of planning, writing, reviewing, or publishing your novel.',
              what_to_do: 'Review the current information and follow the highlighted next action.',
              what_happens_next: 'NovelForge will preserve your work and guide you to the next connected step.',
              actions: [],
            }}
            onNavigate={(target) => { setSection(target); setToolboxOpen(false) }}
            onAsk={() => { setAssistantInitialTab('assistant'); setAssistantOpen(true) }}
          />

          <OperationFailureBanner
            failure={operationFailure}
            developerMode={developerMode}
            onRetry={retryOperationFailure}
            onDismiss={dismissOperationFailure}
            onNavigate={(target) => { setSection(target); setToolboxOpen(false) }}
          />

          <WorkspaceIntelligenceBanner
            projectId={projectId}
            surface={section}
            onExplain={() => {
              setAssistantInitialTab('intelligence')
              setAssistantOpen(true)
            }}
            onNavigate={(target) => { setSection(target); setToolboxOpen(false) }}
          />

          <div className="flex-1 p-3 sm:p-6 overflow-y-auto">
            {section === 'dashboard' ? (
              <div className="space-y-6" data-testid="primary-project-dashboard">
                <Dashboard
                  project={selectedProject}
                  storyHealth={storyHealth}
                  storyRoom={storyRoom}
                  storyArcs={storyArcs}
                  questions={questions}
                  readinessReports={readinessReports}
                  aiInsights={aiInsights}
                  currentRun={currentRun}
                  hasScenePlan={scenes.length > 0}
                  activeDraftStatus={sceneDrafts.find((draft) => draft.active)?.status}
                  onRunCycle={() => runWorkflow(projectId)}
                  onNavigate={(s) => { setSection(s as typeof section); setToolboxOpen(false) }}
                  busy={busy}
                  writingState={writingState}
                  onProjectUpdated={(project) => setSelectedProject(project)}
                />
              </div>
            ) : (
              <div className="animate-in fade-in duration-200">
                {renderSection()}
              </div>
            )}
          </div>
        </section>

        {commandOpen ? (
          <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/50 px-4 pt-[12vh]" role="presentation" onMouseDown={(event) => {
            if (event.currentTarget === event.target) setCommandOpen(false)
          }}>
            <section className="w-full max-w-2xl overflow-hidden rounded-xl border bg-card shadow-2xl" role="dialog" aria-modal="true" aria-label="Navigate NovelForge">
              <div className="flex items-center gap-2 border-b p-3">
                <Search className="h-4 w-4 text-muted-foreground" />
                <Input
                  autoFocus
                  value={commandQuery}
                  onChange={(event) => setCommandQuery(event.target.value)}
                  placeholder="Go to Story Health, Canon Queue, Timeline…"
                  className="border-0 shadow-none focus-visible:ring-0"
                  data-testid="workspace-command-search"
                />
                <kbd className="rounded border bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">Esc</kbd>
              </div>
              <div className="max-h-[55vh] overflow-y-auto p-2">
                {(applicationKnowledge
                  ? Object.entries(applicationKnowledge.surfaces).map(([id, surface]) => ({ id, label: surface.label, purpose: surface.purpose }))
                  : [
                      { id: 'dashboard', label: 'Dashboard', purpose: 'Review project health and next actions.' },
                      ...sections.map(([id, label]) => ({ id, label, purpose: '' })),
                    ]
                )
                  .filter((item) => {
                    const term = commandQuery.trim().toLowerCase()
                    return !term || `${item.label} ${item.purpose}`.toLowerCase().includes(term)
                  })
                  .slice(0, 18)
                  .map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="flex w-full items-start justify-between gap-4 rounded-lg px-3 py-2.5 text-left hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      onClick={() => {
                        setSection(item.id)
                        setToolboxOpen(false)
                        setCommandOpen(false)
                        setCommandQuery('')
                      }}
                    >
                      <span><strong className="block text-sm">{item.label}</strong>{item.purpose ? <span className="mt-0.5 block line-clamp-1 text-xs text-muted-foreground">{item.purpose}</span> : null}</span>
                      <span className="text-xs text-muted-foreground">Open</span>
                    </button>
                  ))}
              </div>
            </section>
          </div>
        ) : null}

        {/* AI Assistant Persistent Side-Drawer Overlay (Right aligned) */}
        {assistantOpen && (
          <aside className="fixed inset-x-0 inset-y-0 z-40 flex min-w-0 flex-col overflow-hidden border-l bg-card shadow-2xl animate-in slide-in-from-right duration-200 sm:left-auto sm:right-0 sm:w-[min(92vw,30rem)]" data-testid="interactive-assistant-drawer">
            <div className="p-4 border-b flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">AI Narrative Companion</h2>
                <p className="text-xs text-muted-foreground">Ask, explore, and navigate the story</p>
              </div>
              <button type="button" aria-label="Close AI narrative companion" onClick={() => setAssistantOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
              <InteractiveNarrativeStudio
                projectId={projectId}
                characters={characterBibles}
                activeSurface={section}
                initialTab={assistantInitialTab}
                compact
                onNavigate={(target) => {
                  setSection(target)
                  setAssistantOpen(false)
                  setToolboxOpen(false)
                }}
                onRefresh={() => fetchProject(projectId)}
              />
            </div>
          </aside>
        )}
        <WorkspaceCompanion
          projectId={projectId}
          activeSurface={section}
          refreshKey={`${sceneDrafts.length}:${sceneDrafts.map((item) => `${item.draft_id}:${item.status}`).join('|')}:${revisionVersions.length}`}
          onNavigate={(target) => { setSection(target); setToolboxOpen(false) }}
          onAsk={() => { setAssistantInitialTab('assistant'); setAssistantOpen(true) }}
          onOpenChange={handleCompanionOpenChange}
          constrained={toolboxOpen}
        />
      </div>
    </main>
  )
}

function Panel({ title, testId, children }: { title: string; testId: string; children: ReactNode }) {
  return (
    <section className="min-w-0 rounded-md border bg-card p-4" data-testid={testId}>
      <h2 className="mb-4 truncate text-xl font-semibold">{title}</h2>
      {children}
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md bg-muted p-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="truncate font-medium">{value}</p>
    </div>
  )
}

function formatRecord(value: unknown) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 'None'
  const entries = Object.entries(value as Record<string, unknown>)
  return entries.length ? entries.map(([key, count]) => `${key} (${String(count)})`).join(', ') : 'None'
}

function splitValues(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function asArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  if (value === null || value === undefined || value === '') return []
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length > 1 && entries.every(([, item]) => typeof item === 'object' && item !== null)) {
      return entries.map(([name, item]) => ({ name, ...(item as Record<string, unknown>) }))
    }
  }
  return [value]
}

function formatNamedValue(value: unknown, fallback: string) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return formatValue(value) || fallback
  const item = value as Record<string, unknown>
  return formatValue(item.name || item.title || item.event || item.summary || item.status || value) || fallback
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.map(formatValue).filter(Boolean).join(', ')
  if (typeof value === 'object') {
    const item = value as Record<string, unknown>
    const primary = item.name || item.title || item.event || item.summary || item.description || item.status
    if (primary) return String(primary)
    return Object.entries(item)
      .slice(0, 4)
      .map(([key, entry]) => `${key.replaceAll('_', ' ')}: ${formatValue(entry)}`)
      .join(' · ')
  }
  return String(value)
}

function CollectionPanel({
  title,
  testId,
  items,
  bare = false,
}: {
  title: string
  testId: string
  items: Array<{ title: string; body?: unknown; footer?: unknown; trace?: unknown }>
  bare?: boolean
}) {
  const body = (
    <div className="space-y-3">
      {items.length === 0 ? <p className="text-sm text-muted-foreground">Nothing tracked yet.</p> : items.map((item, index) => (
        <div key={`${item.title}-${index}`} className="min-w-0 rounded-md border p-3 text-sm">
          <h3 className="truncate font-semibold">{item.title}</h3>
          {item.body ? <p className="mt-2 whitespace-pre-wrap break-words">{formatValue(item.body)}</p> : null}
          {item.footer ? <p className="mt-2 break-words text-xs text-muted-foreground">{formatValue(item.footer)}</p> : null}
          <TraceLine item={item.trace as Record<string, unknown>} />
        </div>
      ))}
    </div>
  )
  if (bare) return <div className="mb-4 min-w-0" data-testid={testId}><h3 className="mb-2 font-semibold">{title}</h3>{body}</div>
  return <Panel title={title} testId={testId}>{body}</Panel>
}
