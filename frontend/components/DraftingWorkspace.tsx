import { useMemo, useState } from 'react'
import {
  Archive,
  Check,
  GitCompare,
  History,
  Layers,
  Loader2,
  RefreshCw,
  RotateCcw,
  Star,
  WandSparkles,
  X,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { dataApi } from '@/lib/api'
import { numberedTitle } from '@/lib/storyLabels'
import { useProjectStore } from '@/store/projectStore'
import ParagraphSkeletonsBoard from './ParagraphSkeletonsBoard'
import WritingDashboard from './WritingDashboard'
import type {
  ChapterDraft,
  ChapterPlan,
  ContinuityReport,
  EditorialReport,
  EditorialScore,
  SceneDraft,
  SceneDraftComparison,
  ScenePlanV2,
  StoryArc,
} from '@/types'


type DraftType = 'scene' | 'chapter'

const WRITING_OPERATIONS = [
  ['rewrite', 'Rewrite', 'A fresh approach that preserves the approved plan.'],
  ['expand', 'Expand', 'Add meaningful beats, texture and room for emotion.'],
  ['condense', 'Condense', 'Tighten the scene without losing essential events.'],
  ['dialogue', 'Improve dialogue', 'Sharpen voices, subtext and conversational tension.'],
  ['pacing', 'Improve pacing', 'Strengthen momentum and remove dragging beats.'],
  ['emotion', 'Improve emotion', 'Show feeling through action, detail and subtext.'],
  ['tension', 'Improve tension', 'Increase pressure, obstacles and consequential choices.'],
  ['description', 'Improve description', 'Make setting and sensory detail more purposeful.'],
  ['action', 'Improve action', 'Clarify physical goals, cause and consequence.'],
  ['humor', 'Improve humor', 'Add character-appropriate levity without breaking tone.'],
  ['mystery', 'Improve mystery', 'Strengthen questions, clues and controlled ambiguity.'],
  ['horror', 'Improve horror', 'Deepen unease, anticipation and sensory threat.'],
  ['romance', 'Improve romance', 'Strengthen chemistry, vulnerability and restraint.'],
  ['world_detail', 'Improve world detail', 'Reveal the world through story-relevant detail.'],
  ['internal_thoughts', 'Improve inner thoughts', 'Clarify viewpoint without over-explaining.'],
  ['transitions', 'Improve transitions', 'Connect beats and the next scene more naturally.'],
] as const


function statusTone(status: string) {
  if (status === 'approved' || status === 'PASS') return 'bg-emerald-100 text-emerald-800'
  if (status === 'rejected' || status === 'FAIL') return 'bg-red-100 text-red-800'
  if (status === 'review' || status === 'WARNING') return 'bg-amber-100 text-amber-800'
  return 'bg-muted text-muted-foreground'
}


function DraftCard({
  draft,
  type,
  title,
  report,
  busy,
  onStatus,
  onRegenerate,
  onRollback,
  onFavorite,
  onNavigate,
  onWritersRoom,
  editorialStatus,
}: {
  draft: SceneDraft | ChapterDraft
  type: DraftType
  title: string
  report?: ContinuityReport
  busy: boolean
  onStatus: (type: DraftType, draftId: string, status: string, reason?: string) => void
  onRegenerate: (type: DraftType, draftId: string, reason: string, operation?: string) => void
  onRollback: (type: DraftType, draftId: string) => void
  onFavorite?: (draftId: string, favorite: boolean) => void
  onNavigate?: (target: string) => void
  onWritersRoom?: (draftId: string, instruction?: string) => void
  editorialStatus?: {
    editorial: boolean
    dialogue: boolean
    score?: number
  }
}) {
  const [operation, setOperation] = useState('rewrite')
  const [showExplanation, setShowExplanation] = useState(false)
  const requestReason = (action: 'reject' | 'regenerate') => {
    const reason = window.prompt(
      action === 'reject' ? 'Why is this draft being rejected?' : 'What should change in the new version?',
    )?.trim()
    if (!reason) return
    if (action === 'reject') onStatus(type, draft.draft_id, 'rejected', reason)
    else onRegenerate(type, draft.draft_id, reason, operation)
  }
  return (
    <article className="rounded-md border p-3 text-sm" data-testid={`${type}-draft-card`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold">{title}</p>
          <p className="text-xs text-muted-foreground">
            {'version_label' in draft && draft.version_label ? draft.version_label : `Version ${draft.version_number}`}
            {' · '}{draft.active ? 'active' : 'history'} · {draft.generated_by}
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          <span className={`rounded px-2 py-1 text-xs font-semibold ${statusTone(draft.status)}`}>
            {draft.status.toUpperCase()}
          </span>
          <span className={`rounded px-2 py-1 text-xs font-semibold ${statusTone(report?.result || draft.validation_result || '')}`}>
            {report?.result || draft.validation_result || 'NOT VALIDATED'}
          </span>
          {'exploratory' in draft && draft.exploratory ? (
            <span className="rounded bg-violet-100 px-2 py-1 text-xs font-semibold text-violet-800">EXPLORATORY</span>
          ) : null}
          {type === 'scene' && onFavorite ? (
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              disabled={busy}
              aria-label={('favorite' in draft && draft.favorite) ? 'Remove draft from favorites' : 'Favorite this draft'}
              onClick={() => onFavorite(draft.draft_id, !('favorite' in draft && draft.favorite))}
            >
              <Star className={`h-4 w-4 ${('favorite' in draft && draft.favorite) ? 'fill-amber-400 text-amber-500' : ''}`} />
            </Button>
          ) : null}
        </div>
      </div>
      <p className="mt-3 max-h-32 overflow-y-auto whitespace-pre-wrap rounded bg-muted/30 p-2">
        {draft.generated_text}
      </p>
      {report?.warnings?.length ? (
        <p className="mt-2 text-xs text-amber-800">{report.warnings.join(' ')}</p>
      ) : null}
      {draft.review_reason ? (
        <p className="mt-2 text-xs text-muted-foreground">Review note: {draft.review_reason}</p>
      ) : null}
      {type === 'scene' && 'canon_proposal_ids' in draft && draft.canon_proposal_ids?.length ? (
        <div className="mt-2 rounded border border-violet-200 bg-violet-50 p-2 text-xs text-violet-950">
          <strong>{draft.canon_proposal_ids.length} new story fact{draft.canon_proposal_ids.length === 1 ? '' : 's'} need your decision.</strong>{' '}
          Official Canon stays unchanged until you approve or reject them.
          {onNavigate ? (
            <Button className="ml-2 h-7" size="sm" variant="outline" onClick={() => onNavigate('canon-queue')}>
              Open Canon Queue
            </Button>
          ) : null}
        </div>
      ) : null}
      {type === 'scene' && 'why' in draft && draft.why ? (
        <div className="mt-2 rounded border bg-background p-2 text-xs">
          <button
            type="button"
            className="font-semibold text-primary underline-offset-2 hover:underline"
            aria-expanded={showExplanation}
            onClick={() => setShowExplanation((value) => !value)}
          >
            {showExplanation ? 'Hide AI explanation' : 'Why this draft?'}
          </button>
          {showExplanation ? (
            <dl className="mt-2 grid gap-2 sm:grid-cols-2">
              <div><dt className="font-semibold">Why</dt><dd className="text-muted-foreground">{draft.why}</dd></div>
              <div><dt className="font-semibold">Expected impact</dt><dd className="text-muted-foreground">{draft.expected_impact || 'Preserve the plan while improving the reading experience.'}</dd></div>
              <div><dt className="font-semibold">Change scope</dt><dd className="text-muted-foreground">{draft.estimated_change_scope || 'medium'}</dd></div>
              <div><dt className="font-semibold">What stays unchanged</dt><dd className="text-muted-foreground">{draft.preserved_elements?.join(', ') || 'Approved planning and canon'}</dd></div>
              {draft.scene_goal ? <div><dt className="font-semibold">Scene goal</dt><dd className="text-muted-foreground">{draft.scene_goal}</dd></div> : null}
              {draft.scene_trouble ? <div><dt className="font-semibold">Real trouble</dt><dd className="text-muted-foreground">{draft.scene_trouble}</dd></div> : null}
              {draft.scene_stakes ? <div><dt className="font-semibold">Stakes</dt><dd className="text-muted-foreground">{draft.scene_stakes}</dd></div> : null}
              {draft.distinct_progression ? <div><dt className="font-semibold">What newly changes</dt><dd className="text-muted-foreground">{draft.distinct_progression}</dd></div> : null}
              {draft.connection_from_previous ? <div><dt className="font-semibold">Connection from previous scene</dt><dd className="text-muted-foreground">{draft.connection_from_previous}</dd></div> : null}
              {draft.handoff_to_next ? <div><dt className="font-semibold">Handoff to next scene</dt><dd className="text-muted-foreground">{draft.handoff_to_next}</dd></div> : null}
              <div className="sm:col-span-2"><dt className="font-semibold">Narrative areas</dt><dd className="text-muted-foreground">{draft.affected_narrative_areas?.join(', ') || 'continuity'}</dd></div>
            </dl>
          ) : null}
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {draft.active && draft.status === 'draft' ? (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => onStatus(type, draft.draft_id, 'review')}>
            Review
          </Button>
        ) : null}
        {draft.active && draft.status === 'review' ? (
          <>
            <Button size="sm" disabled={busy} onClick={() => onStatus(type, draft.draft_id, 'approved')}>
              <Check className="mr-1 h-3.5 w-3.5" /> Approve
            </Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => requestReason('reject')}>
              <X className="mr-1 h-3.5 w-3.5" /> Reject
            </Button>
          </>
        ) : null}
        {draft.active && draft.status !== 'archived' ? (
          <>
            <label className="sr-only" htmlFor={`operation-${draft.draft_id}`}>Writing operation</label>
            <select
              id={`operation-${draft.draft_id}`}
              className="h-9 max-w-44 rounded-md border bg-background px-2 text-xs"
              value={operation}
              onChange={(event) => setOperation(event.target.value)}
              disabled={busy}
              title={WRITING_OPERATIONS.find(([value]) => value === operation)?.[2]}
            >
              {WRITING_OPERATIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => requestReason('regenerate')}>
              <RefreshCw className="mr-1 h-3.5 w-3.5" /> Create alternative
            </Button>
          </>
        ) : null}
        {type === 'scene' && draft.active && draft.status !== 'archived' && onWritersRoom ? (
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            title="Create emotional, action-focused, and mystery-focused alternatives. You choose the winner."
            onClick={() => {
              const instruction = window.prompt(
                'Anything all three Writer’s Room options should preserve or explore?',
              )
              if (instruction !== null) onWritersRoom(draft.draft_id, instruction.trim())
            }}
          >
            <WandSparkles className="mr-1 h-3.5 w-3.5" /> Explore 3 directions
          </Button>
        ) : null}
        {draft.active && ['draft', 'review', 'approved', 'rejected'].includes(draft.status) ? (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => onStatus(type, draft.draft_id, 'archived')}>
            <Archive className="mr-1 h-3.5 w-3.5" /> Archive
          </Button>
        ) : null}
        {!draft.active && draft.status !== 'archived' ? (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => onRollback(type, draft.draft_id)}>
            <RotateCcw className="mr-1 h-3.5 w-3.5" /> Roll Back
          </Button>
        ) : null}
        {busy ? <Loader2 className="h-4 w-4 animate-spin self-center" /> : null}
      </div>
      {draft.status === 'approved' && editorialStatus ? (
        <div className="mt-3 flex flex-wrap gap-1 text-xs">
          <span className={`rounded px-2 py-1 ${editorialStatus.editorial ? 'bg-emerald-100 text-emerald-800' : 'bg-muted'}`}>
            editorial {editorialStatus.editorial ? 'reviewed' : 'pending'}
          </span>
          <span className={`rounded px-2 py-1 ${editorialStatus.dialogue ? 'bg-emerald-100 text-emerald-800' : 'bg-muted'}`}>
            dialogue {editorialStatus.dialogue ? 'reviewed' : 'pending'}
          </span>
          {editorialStatus.score !== undefined ? (
            <span className="rounded bg-blue-100 px-2 py-1 text-blue-800">score {editorialStatus.score}</span>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}


export default function DraftingWorkspace({
  arcs,
  chapters,
  scenes,
  sceneDrafts,
  chapterDrafts,
  continuityReports,
  editorialReports = [],
  editorialScores = [],
  draftableArcIds,
  fixedArcId,
  busyId,
  onGenerateScene,
  onGenerateChapter,
  onPlanStatus,
  onStatus,
  onRegenerate,
  onRollback,
  onFavorite,
  onNavigate,
  onWritersRoom,
  onMerge,
}: {
  arcs: StoryArc[]
  chapters: ChapterPlan[]
  scenes: ScenePlanV2[]
  sceneDrafts: SceneDraft[]
  chapterDrafts: ChapterDraft[]
  continuityReports: ContinuityReport[]
  editorialReports?: EditorialReport[]
  editorialScores?: EditorialScore[]
  draftableArcIds: string[]
  fixedArcId?: string
  busyId?: string | null
  onGenerateScene: (sceneId: string, options?: { allowExploratory?: boolean }) => void
  onGenerateChapter: (chapterPlanId: string) => void
  onPlanStatus: (type: 'scene' | 'chapter', planId: string, status: string) => void | Promise<void>
  onStatus: (type: DraftType, draftId: string, status: string, reason?: string) => void
  onRegenerate: (type: DraftType, draftId: string, reason: string, operation?: string) => void
  onRollback: (type: DraftType, draftId: string) => void
  onFavorite?: (draftId: string, favorite: boolean) => void
  onNavigate?: (target: string) => void
  onWritersRoom?: (draftId: string, instruction?: string) => void
  onMerge?: (leftDraftId: string, rightDraftId: string, mergedText: string) => void
}) {
  const {
    selectedProject,
    paragraphs,
    isParagraphsLoading,
    fetchSceneParagraphs,
    generateSceneParagraphs,
    updateParagraphSkeleton,
    reorderParagraphSkeletons,
    lockParagraphSkeleton,
    deleteParagraphSkeleton,
    duplicateParagraphSkeleton,
    approveParagraphSkeleton,
    regenerateParagraphSkeleton,
    getParagraphHistory,
  } = useProjectStore()

  const defaultArcId = fixedArcId || arcs.find((arc) => arc.focus_role === 'current')?.arc_id || arcs[0]?.arc_id || ''
  const [selectedArcId, setSelectedArcId] = useState(defaultArcId)
  const [selectedSceneForPlanning, setSelectedSceneForPlanning] = useState<ScenePlanV2 | null>(null)
  const [comparison, setComparison] = useState<SceneDraftComparison | null>(null)
  const [comparisonBusy, setComparisonBusy] = useState(false)
  const [mergeText, setMergeText] = useState('')
  const [sceneSearch, setSceneSearch] = useState('')
  const [chapterFilter, setChapterFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [scenePage, setScenePage] = useState(1)
  const [chapterPage, setChapterPage] = useState(1)
  const [expandedScenes, setExpandedScenes] = useState<Set<string>>(new Set())

  const generateAndRevealScene = (sceneId: string, allowExploratory: boolean) => {
    setExpandedScenes((current) => new Set(current).add(sceneId))
    onGenerateScene(sceneId, { allowExploratory })
  }
  const arcId = fixedArcId || selectedArcId || defaultArcId
  const arc = arcs.find((item) => item.arc_id === arcId)
  const arcChapters = chapters
    .filter((item) => item.arc_id === arcId)
    .sort((left, right) => left.chapter_number - right.chapter_number)
  const chapterIds = new Set(arcChapters.map((item) => item.chapter_plan_id))
  const chapterNumberById = new Map(arcChapters.map((item) => [item.chapter_plan_id, item.chapter_number]))
  const arcScenes = scenes
    .filter((item) => item.arc_id === arcId || Boolean(item.chapter_plan_id && chapterIds.has(item.chapter_plan_id)))
    .sort((left, right) => (
      (chapterNumberById.get(left.chapter_plan_id ?? '') || 0) - (chapterNumberById.get(right.chapter_plan_id ?? '') || 0)
      || left.order - right.order
    ))
  const filteredScenes = arcScenes.filter((scene) => {
    const versions = sceneDrafts.filter((draft) => draft.scene_id === scene.scene_id)
    const activeStatus = versions.find((draft) => draft.active)?.status || (versions.length ? 'history' : 'not_started')
    const haystack = `${scene.title} ${scene.purpose || ''} ${scene.conflict || ''}`.toLowerCase()
    return (!sceneSearch || haystack.includes(sceneSearch.toLowerCase()))
      && (chapterFilter === 'all' || scene.chapter_plan_id === chapterFilter)
      && (statusFilter === 'all' || activeStatus === statusFilter)
  })
  const scenePageSize = 20
  const scenePageCount = Math.max(1, Math.ceil(filteredScenes.length / scenePageSize))
  const visibleScenes = filteredScenes.slice((scenePage - 1) * scenePageSize, scenePage * scenePageSize)
  const chapterPageSize = 20
  const visibleChapters = arcChapters.slice((chapterPage - 1) * chapterPageSize, chapterPage * chapterPageSize)
  const isDraftable = draftableArcIds.includes(arcId)
  const latestReports = useMemo(() => {
    const result = new Map<string, ContinuityReport>()
    continuityReports.forEach((report) => {
      if (report.subject_id && !result.has(report.subject_id)) result.set(report.subject_id, report)
    })
    return result
  }, [continuityReports])

  if (!arc) return <p className="text-sm text-muted-foreground">Create an arc before drafting.</p>

  // ── Paragraph Planning Board view ──────────────────────────────────────────
  if (selectedSceneForPlanning && selectedProject) {
    const projectId = selectedProject.id ?? ''
    return (
      <ParagraphSkeletonsBoard
        projectId={projectId}
        sceneId={selectedSceneForPlanning.scene_id}
        sceneTitle={selectedSceneForPlanning.title}
        paragraphs={paragraphs}
        isParagraphsLoading={isParagraphsLoading}
        onGoBack={() => setSelectedSceneForPlanning(null)}
        fetchSceneParagraphs={fetchSceneParagraphs}
        generateSceneParagraphs={generateSceneParagraphs}
        updateParagraphSkeleton={updateParagraphSkeleton}
        reorderParagraphSkeletons={reorderParagraphSkeletons}
        lockParagraphSkeleton={lockParagraphSkeleton}
        deleteParagraphSkeleton={deleteParagraphSkeleton}
        duplicateParagraphSkeleton={duplicateParagraphSkeleton}
        approveParagraphSkeleton={approveParagraphSkeleton}
        regenerateParagraphSkeleton={regenerateParagraphSkeleton}
        getParagraphHistory={getParagraphHistory}
      />
    )
  }

  return (
    <div className="space-y-4" data-testid="drafting-workspace">
      {selectedProject?.id ? (
        <WritingDashboard
          projectId={selectedProject.id}
          refreshKey={`${sceneDrafts.length}:${sceneDrafts.map((item) => `${item.draft_id}:${item.status}:${item.active}`).join('|')}:${chapters.map((item) => `${item.chapter_plan_id}:${item.status}`).join('|')}:${scenes.map((item) => `${item.scene_id}:${item.status}`).join('|')}`}
          busyId={busyId}
          onNavigate={onNavigate}
          onGenerate={generateAndRevealScene}
        />
      ) : null}
      {!fixedArcId ? (
        <label className="block max-w-md text-sm">
          <span className="mb-1 block font-medium">Drafting arc</span>
          <select
            className="h-10 w-full rounded-md border bg-background px-3"
            value={arcId}
            onChange={(event) => setSelectedArcId(event.target.value)}
          >
            {arcs.map((item) => <option key={item.arc_id} value={item.arc_id}>{item.title}</option>)}
          </select>
        </label>
      ) : null}
      <div className={`rounded-md border p-3 text-sm ${isDraftable ? 'border-emerald-300 bg-emerald-50 text-emerald-900' : 'border-amber-300 bg-amber-50 text-amber-900'}`}>
        <strong>{isDraftable ? 'Drafting gates satisfied. This arc is ready for approval-quality drafting.' : 'Planning checks still protect final approval.'}</strong>{' '}
        {isDraftable
          ? 'Your draft can move through review, revision and approval.'
          : 'You may create an exploratory version now; it cannot be approved until the listed planning checks are resolved.'}
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold">Scene Drafts</h3>
          <span className="text-xs text-muted-foreground">{arcScenes.length} planned scenes</span>
        </div>
        <div className="grid gap-2 rounded-lg border bg-muted/20 p-3 md:grid-cols-[minmax(12rem,1fr)_auto_auto]" data-testid="drafting-filters">
          <Input
            value={sceneSearch}
            onChange={(event) => { setSceneSearch(event.target.value); setScenePage(1) }}
            placeholder="Search scene title, goal, or conflict"
            aria-label="Search scene drafts"
          />
          <select className="rounded-md border bg-background px-3 text-sm" value={chapterFilter} onChange={(event) => { setChapterFilter(event.target.value); setScenePage(1) }} aria-label="Filter scene drafts by chapter">
            <option value="all">All chapters</option>
            {arcChapters.map((chapter) => <option key={chapter.chapter_plan_id} value={chapter.chapter_plan_id}>{numberedTitle('chapter', chapter.chapter_number, chapter.title)}</option>)}
          </select>
          <select className="rounded-md border bg-background px-3 text-sm" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setScenePage(1) }} aria-label="Filter scene drafts by status">
            <option value="all">All statuses</option><option value="not_started">Not started</option><option value="draft">Draft</option><option value="review">Review</option><option value="approved">Approved</option><option value="rejected">Rejected</option>
          </select>
        </div>
        <p className="text-xs text-muted-foreground">Showing {visibleScenes.length} of {filteredScenes.length} matching scenes. Open a scene to load its prose and versions.</p>
        {visibleScenes.map((scene) => {
          const versions = sceneDrafts
            .filter((draft) => draft.scene_id === scene.scene_id)
            .sort((left, right) => right.version_number - left.version_number)
          const expanded = expandedScenes.has(scene.scene_id)
          const chapter = arcChapters.find((item) => item.chapter_plan_id === scene.chapter_plan_id)
          return (
            <div key={scene.scene_id} className="rounded-md border bg-muted/10 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">{numberedTitle('chapter', chapter?.chapter_number || '—', chapter?.title)} · {numberedTitle('scene', scene.order, scene.title)}</p>
                  <p className="text-xs text-muted-foreground">
                    Scene {scene.order} · Plan {scene.status} · {versions.length} version{versions.length === 1 ? '' : 's'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {scene.status !== 'approved' ? (
                    <Button size="sm" variant="outline" onClick={() => void onPlanStatus('scene', scene.scene_id, 'approved')}>
                      Approve scene plan
                    </Button>
                  ) : <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800">Scene plan approved</span>}
                  <Button size="sm" variant="ghost" aria-expanded={expanded} onClick={() => setExpandedScenes((current) => { const next = new Set(current); expanded ? next.delete(scene.scene_id) : next.add(scene.scene_id); return next })}>
                    {expanded ? 'Collapse' : 'Open scene'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedSceneForPlanning(scene)}
                    data-testid={`plan-paragraphs-btn-${scene.scene_id}`}
                  >
                    <Layers className="mr-1.5 h-3.5 w-3.5" />
                    Plan Paragraphs
                  </Button>
                  <Button
                    size="sm"
                    disabled={busyId === scene.scene_id}
                    aria-label={isDraftable && scene.status === 'approved' ? 'Generate Scene' : undefined}
                    onClick={() => generateAndRevealScene(scene.scene_id, !isDraftable || scene.status !== 'approved')}
                  >
                    {busyId === scene.scene_id ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin motion-reduce:animate-none" /> : null}
                    {busyId === scene.scene_id ? 'Writing scene…' : versions.length ? 'New Version' : (isDraftable && scene.status === 'approved' ? 'Generate Draft' : 'Generate Exploratory Draft')}
                  </Button>
                </div>
              </div>
              {expanded ? <div className="mt-3 space-y-2" data-testid="expanded-scene-drafts">
                {versions.map((draft) => (
                  <DraftCard
                    key={draft.draft_id}
                    draft={draft}
                    type="scene"
                    title={scene.title}
                    report={latestReports.get(draft.draft_id)}
                    busy={busyId === draft.draft_id}
                    onStatus={onStatus}
                    onRegenerate={onRegenerate}
                    onRollback={onRollback}
                    onFavorite={onFavorite}
                    onNavigate={onNavigate}
                    onWritersRoom={onWritersRoom}
                    editorialStatus={{
                      editorial: editorialReports.some((report) => report.subject_id === draft.draft_id && report.report_type === 'editorial'),
                      dialogue: editorialReports.some((report) => report.subject_id === draft.draft_id && report.report_type === 'dialogue'),
                      score: editorialScores.find((score) => score.subject_id === draft.draft_id)?.score,
                    }}
                  />
                ))}
                {versions.length >= 2 && selectedProject?.id ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={comparisonBusy}
                    onClick={() => {
                      setComparisonBusy(true)
                      void dataApi.compareSceneDrafts(
                        selectedProject.id!,
                        versions[1].draft_id,
                        versions[0].draft_id,
                      ).then((result) => {
                        const next = result as SceneDraftComparison
                        setComparison(next)
                        setMergeText(next.right.text)
                      })
                        .finally(() => setComparisonBusy(false))
                    }}
                  >
                    {comparisonBusy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <GitCompare className="mr-1.5 h-4 w-4" />}
                    Compare latest versions
                  </Button>
                ) : null}
                {!versions.length ? <p className="text-sm text-muted-foreground">No generated versions.</p> : null}
              </div> : versions[0] ? <p className="mt-2 text-xs text-muted-foreground">Active status: {versions.find((draft) => draft.active)?.status || 'history'} · Latest {versions[0].version_label || `version ${versions[0].version_number}`}</p> : null}
            </div>
          )
        })}
        {!visibleScenes.length ? <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No scenes match these filters.</p> : null}
        {scenePageCount > 1 ? <div className="flex items-center justify-between"><Button size="sm" variant="outline" disabled={scenePage === 1} onClick={() => setScenePage((value) => Math.max(1, value - 1))}>Previous scenes</Button><span className="text-xs">Page {scenePage} of {scenePageCount}</span><Button size="sm" variant="outline" disabled={scenePage === scenePageCount} onClick={() => setScenePage((value) => Math.min(scenePageCount, value + 1))}>Next scenes</Button></div> : null}
      </section>

      {comparison ? (
        <section className="rounded-xl border bg-background p-4" aria-live="polite" data-testid="scene-version-comparison">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold">Draft comparison</h3>
              <p className="mt-1 text-sm text-muted-foreground">{comparison.summary}</p>
            </div>
            <Button size="sm" variant="ghost" onClick={() => setComparison(null)}>Close</Button>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            {[comparison.left, comparison.right].map((item) => (
              <article key={item.draft_id} className="rounded-lg border p-3">
                <p className="font-semibold">{item.label} · {item.word_count} words</p>
                <p className="mt-2 max-h-72 overflow-y-auto whitespace-pre-wrap text-sm leading-6">{item.text}</p>
              </article>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Comparison never changes either version. Favorite one, restore it, or create another focused alternative.
          </p>
          {onMerge ? (
            <div className="mt-4 rounded-lg border bg-muted/20 p-3">
              <label className="text-sm font-semibold" htmlFor="scene-merge-text">
                Author-controlled merge
              </label>
              <p className="mt-1 text-xs text-muted-foreground">
                Start from the newer version, combine only what you want, then save it as another protected review version.
              </p>
              <textarea
                id="scene-merge-text"
                className="mt-2 min-h-48 w-full rounded-md border bg-background p-3 text-sm leading-6"
                value={mergeText}
                onChange={(event) => setMergeText(event.target.value)}
              />
              <Button
                className="mt-2"
                size="sm"
                disabled={!mergeText.trim()}
                onClick={() => onMerge(comparison.left.draft_id, comparison.right.draft_id, mergeText)}
              >
                Save merged review version
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold">Chapter Drafts</h3>
          <History className="h-4 w-4 text-muted-foreground" />
        </div>
        {visibleChapters.map((chapter) => {
          const chapterScenes = arcScenes.filter((scene) => scene.chapter_plan_id === chapter.chapter_plan_id)
          const scenesApproved = chapterScenes.length > 0 && chapterScenes.every((scene) => (
            sceneDrafts.some((draft) => draft.scene_id === scene.scene_id && draft.active && draft.status === 'approved')
          ))
          const versions = chapterDrafts
            .filter((draft) => draft.chapter_plan_id === chapter.chapter_plan_id)
            .sort((left, right) => right.version_number - left.version_number)
          return (
            <div key={chapter.chapter_plan_id} className="rounded-md border bg-muted/10 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium">{numberedTitle('chapter', chapter.chapter_number, chapter.title)}</p>
                  <p className="text-xs text-muted-foreground">
                    {scenesApproved ? 'All planned scenes approved' : 'Waiting for approved scene drafts'}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {chapter.status !== 'approved' ? (
                    <Button size="sm" variant="outline" onClick={() => void onPlanStatus('chapter', chapter.chapter_plan_id, 'approved')}>
                      Approve chapter plan
                    </Button>
                  ) : <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800">Chapter plan approved</span>}
                  <Button
                    size="sm"
                    disabled={!isDraftable || chapter.status !== 'approved' || !scenesApproved || busyId === chapter.chapter_plan_id}
                    onClick={() => onGenerateChapter(chapter.chapter_plan_id)}
                  >
                    {busyId === chapter.chapter_plan_id ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : null}
                    Assemble Chapter
                  </Button>
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {versions.map((draft) => (
                  <DraftCard
                    key={draft.draft_id}
                    draft={draft}
                    type="chapter"
                    title={numberedTitle('chapter', chapter.chapter_number, chapter.title)}
                    report={latestReports.get(draft.draft_id)}
                    busy={busyId === draft.draft_id}
                    onStatus={onStatus}
                    onRegenerate={onRegenerate}
                    onRollback={onRollback}
                    editorialStatus={{
                      editorial: editorialReports.some((report) => report.subject_id === draft.draft_id && report.report_type === 'editorial'),
                      dialogue: editorialReports.some((report) => report.subject_id === draft.draft_id && report.report_type === 'dialogue'),
                      score: editorialScores.find((score) => score.subject_id === draft.draft_id)?.score,
                    }}
                  />
                ))}
                {!versions.length ? <p className="text-sm text-muted-foreground">No assembled versions.</p> : null}
              </div>
            </div>
          )
        })}
        {arcChapters.length > chapterPageSize ? <div className="flex items-center justify-between"><Button size="sm" variant="outline" disabled={chapterPage === 1} onClick={() => setChapterPage((value) => Math.max(1, value - 1))}>Previous chapters</Button><span className="text-xs">Chapter page {chapterPage} of {Math.ceil(arcChapters.length / chapterPageSize)}</span><Button size="sm" variant="outline" disabled={chapterPage >= Math.ceil(arcChapters.length / chapterPageSize)} onClick={() => setChapterPage((value) => value + 1)}>Next chapters</Button></div> : null}
      </section>
    </div>
  )
}
