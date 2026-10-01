import { useEffect, useMemo, useState } from 'react'
import { GitCompare, Loader2, MessageSquareText, PenTool, ScanText } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { numberedTitle } from '@/lib/storyLabels'
import type {
  ChapterPlan,
  ChapterDraft,
  EditorialReport,
  EditorialScore,
  RevisionBranch,
  RevisionComparison,
  RevisionVersion,
  SceneDraft,
  ScenePlanV2,
  StoryArc,
} from '@/types'

const REVISION_PASSES = [
  ['development', 'Development edit'],
  ['line', 'Line edit'],
  ['copy', 'Copy edit'],
  ['style', 'Style pass'],
  ['continuity', 'Continuity pass'],
  ['dialogue', 'Dialogue pass'],
  ['emotion', 'Emotion pass'],
  ['description', 'Description pass'],
  ['consistency', 'Consistency pass'],
  ['grammar', 'Grammar pass'],
] as const

const authorRevisionStatus = (status: string) => ({
  draft: 'Needs review',
  review: 'Ready for your decision',
  approved: 'Kept for use',
  rejected: 'Kept original',
  archived: 'Archived',
} as Record<string, string>)[status] || status

function scoreTone(score: number) {
  if (score >= 80) return 'bg-emerald-100 text-emerald-800'
  if (score >= 60) return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
}


function ScoreCard({ score, identity }: { score: EditorialScore; identity: string }) {
  return (
    <article className="rounded-md border p-3" data-testid="editorial-score-card">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold">{score.score_type.replaceAll('_', ' ')}</p>
          <p className="text-xs text-muted-foreground">{identity}</p>
        </div>
        <span className={`rounded px-2 py-1 text-sm font-bold ${scoreTone(score.score)}`}>{score.score}</span>
      </div>
      <div className="mt-3 grid gap-1 text-xs sm:grid-cols-2">
        {Object.entries(score.dimensions).map(([name, value]) => (
          <p key={name} className="rounded bg-muted/40 px-2 py-1">
            {name.replaceAll('_', ' ')}: <strong>{value}</strong>
          </p>
        ))}
      </div>
    </article>
  )
}


export default function EditorialWorkspace({
  arcs,
  chapters = [],
  scenes = [],
  sceneDrafts,
  chapterDrafts,
  reports,
  scores,
  branches,
  versions,
  comparisons,
  focusDraftId,
  busyId,
  onReview,
  onDialogue,
  onCreateBranch,
  onGenerateRevision,
  onBranchStatus,
  onCompare,
  onApplyRevision = () => undefined,
}: {
  arcs: StoryArc[]
  chapters?: ChapterPlan[]
  scenes?: ScenePlanV2[]
  sceneDrafts: SceneDraft[]
  chapterDrafts: ChapterDraft[]
  reports: EditorialReport[]
  scores: EditorialScore[]
  branches: RevisionBranch[]
  versions: RevisionVersion[]
  comparisons: Record<string, RevisionComparison>
  focusDraftId?: string | null
  busyId?: string | null
  onReview: (subjectType: 'scene' | 'chapter' | 'arc', subjectId: string) => void
  onDialogue: (draftType: 'scene' | 'chapter', draftId: string) => void
  onCreateBranch: (draftType: 'scene' | 'chapter', draftId: string, title?: string, revisionPass?: string) => void
  onGenerateRevision: (branchId: string, reason: string, revisionPass?: string) => void
  onBranchStatus: (branchId: string, status: string, reason?: string) => void
  onCompare: (branchId: string) => void
  onApplyRevision?: (branchId: string) => void
}) {
  const [newRevisionPass, setNewRevisionPass] = useState('development')
  const [search, setSearch] = useState('')
  const [chapterFilter, setChapterFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [passFilter, setPassFilter] = useState('all')
  const [detailLimit, setDetailLimit] = useState(30)
  useEffect(() => {
    if (focusDraftId) window.setTimeout(() => document.getElementById(`editorial-target-${focusDraftId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50)
  }, [focusDraftId])
  const chapterById = new Map(chapters.map((chapter) => [chapter.chapter_plan_id, chapter]))
  const sceneById = new Map(scenes.map((scene) => [scene.scene_id, scene]))
  const sceneDraftById = new Map(sceneDrafts.map((draft) => [draft.draft_id, draft]))
  const chapterDraftById = new Map(chapterDrafts.map((draft) => [draft.draft_id, draft]))
  const draftIdentity = (draft: SceneDraft | ChapterDraft, type?: 'scene' | 'chapter') => {
    const scene = ('scene_id' in draft || type === 'scene') ? sceneById.get((draft as SceneDraft).scene_id) : undefined
    const chapter = chapterById.get(scene?.chapter_plan_id || (draft as ChapterDraft).chapter_plan_id || '')
    const chapterNumber = Number((draft as ChapterDraft & { chapter_number?: number }).chapter_number || 0)
    const chapterLabel = chapter ? numberedTitle('chapter', chapter.chapter_number, chapter.title) : chapterNumber ? `Chapter ${chapterNumber}` : 'Chapter not linked'
    return `${chapterLabel} · ${scene ? numberedTitle('scene', scene.order, scene.title) : 'Chapter draft'} · ${'version_label' in draft && draft.version_label ? draft.version_label : `Version ${draft.version_number}`} · ${draft.status}`
  }
  const subjectIdentity = (subjectId: string, subjectType = '') => {
    const sceneDraft = sceneDraftById.get(subjectId)
    if (sceneDraft) return draftIdentity(sceneDraft, 'scene')
    const chapterDraft = chapterDraftById.get(subjectId)
    if (chapterDraft) return draftIdentity(chapterDraft, 'chapter')
    const arc = arcs.find((item) => item.arc_id === subjectId)
    return arc ? `Arc: ${arc.title}` : `${subjectType.replaceAll('_', ' ')} record`
  }
  const reviewableScenes = sceneDrafts.filter((draft) => draft.active && ['review', 'approved'].includes(draft.status))
  const reviewableChapters = chapterDrafts.filter((draft) => draft.active && ['review', 'approved'].includes(draft.status))
  const reviewTargets = [
    ...reviewableScenes.map((draft) => ({ type: 'scene' as const, draft })),
    ...reviewableChapters.map((draft) => ({ type: 'chapter' as const, draft })),
  ].filter(({ type, draft }) => {
    const scene = type === 'scene' ? sceneById.get((draft as SceneDraft).scene_id) : undefined
    const chapterId = scene?.chapter_plan_id || (draft as ChapterDraft).chapter_plan_id || ''
    const identity = draftIdentity(draft, type).toLowerCase()
    return (!focusDraftId || draft.draft_id === focusDraftId) && (!search || identity.includes(search.toLowerCase()))
      && (chapterFilter === 'all' || chapterId === chapterFilter)
      && (statusFilter === 'all' || draft.status === statusFilter)
  })
  const latestScores = useMemo(() => {
    const result = new Map<string, EditorialScore>()
    scores.forEach((score) => {
      const key = `${score.subject_type}:${score.subject_id}:${score.score_type}`
      if (!result.has(key)) result.set(key, score)
    })
    return [...result.values()]
  }, [scores])
  const review = (type: 'scene' | 'chapter' | 'arc', id: string) => {
    onReview(type, id)
  }
  const createBranch = (type: 'scene' | 'chapter', id: string) => {
    const title = window.prompt('Name this revised version (optional)')?.trim()
    if (title !== undefined) onCreateBranch(type, id, title, newRevisionPass)
  }
  const generate = (branchId: string) => {
    const reason = window.prompt('What should improve in this chapter?')?.trim()
    const branch = branches.find((item) => item.branch_id === branchId)
    if (reason) onGenerateRevision(branchId, reason, branch?.revision_pass || 'development')
  }
  const reject = (branchId: string) => {
    const reason = window.prompt('Why keep the original chapter?')?.trim()
    if (reason) onBranchStatus(branchId, 'rejected', reason)
  }

  return (
    <div className="space-y-5" data-testid="editorial-workspace">
      {focusDraftId ? <div className="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm"><strong>Editing a selected chapter.</strong> Your original chapter stays safe. Ask for improvements, review the changes, and choose which version to use.</div> : null}
      <div className="rounded-md border bg-muted/30 p-3 text-sm">
        <strong>Approved drafts remain authoritative.</strong>{' '}
        Your source draft is always protected.{' '}
        Review and revision create alternatives. A proposal enters Drafting as a new review version only after you approve and apply it.
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h3 className="font-semibold">Editorial Scores</h3>
          <span className="text-xs text-muted-foreground">{latestScores.length} current scores</span>
        </div>
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {latestScores.slice(0, detailLimit).map((score) => <ScoreCard key={score.score_id} score={score} identity={subjectIdentity(score.subject_id, score.subject_type)} />)}
          {!latestScores.length ? <p className="text-sm text-muted-foreground">No editorial scores yet.</p> : null}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="font-semibold">Suggest improvements</h3>
            <p className="text-xs text-muted-foreground">Choose what you want help with, then review the proposed changes before using them.</p>
          </div>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-medium">Focus of suggestions</span>
            <select className="h-9 rounded-md border bg-background px-3" value={newRevisionPass} onChange={(event) => setNewRevisionPass(event.target.value)}>
              {REVISION_PASSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        </div>
        <div className="grid gap-2 rounded-lg border bg-muted/20 p-3 md:grid-cols-2 xl:grid-cols-4" data-testid="editorial-filters">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search chapter or scene" aria-label="Search editorial targets" />
          <select value={chapterFilter} onChange={(event) => setChapterFilter(event.target.value)} className="rounded-md border bg-background px-3 text-sm" aria-label="Filter editorial targets by chapter"><option value="all">All chapters</option>{chapters.map((chapter) => <option key={chapter.chapter_plan_id} value={chapter.chapter_plan_id}>{numberedTitle('chapter', chapter.chapter_number, chapter.title)}</option>)}</select>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-md border bg-background px-3 text-sm" aria-label="Filter editorial targets by status"><option value="all">All statuses</option><option value="review">Review</option><option value="approved">Approved</option></select>
          <select value={passFilter} onChange={(event) => setPassFilter(event.target.value)} className="rounded-md border bg-background px-3 text-sm" aria-label="Filter suggested versions by pass"><option value="all">All suggested passes</option>{REVISION_PASSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
        </div>
        {reviewTargets.slice(0, detailLimit).map(({ type, draft }) => {
          const subjectReports = reports.filter((report) => report.subject_id === draft.draft_id)
          const hasEditorial = subjectReports.some((report) => report.report_type === 'editorial')
          const hasDialogue = subjectReports.some((report) => report.report_type === 'dialogue')
          return (
            <article key={draft.draft_id} id={`editorial-target-${draft.draft_id}`} className="rounded-md border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-semibold">{draftIdentity(draft, type)}</p>
                  <p className="text-xs text-muted-foreground">{draft.status === 'review' ? 'Ready for editorial review before final approval' : 'Approved source'}</p>
                </div>
                <div className="flex flex-wrap gap-1 text-xs">
                  <span className={`rounded px-2 py-1 ${hasEditorial ? 'bg-emerald-100 text-emerald-800' : 'bg-muted'}`}>
                    editorial {hasEditorial ? 'complete' : 'pending'}
                  </span>
                  <span className={`rounded px-2 py-1 ${hasDialogue ? 'bg-emerald-100 text-emerald-800' : 'bg-muted'}`}>
                    dialogue {hasDialogue ? 'complete' : 'pending'}
                  </span>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button aria-label="Editorial Review" size="sm" disabled={busyId === draft.draft_id} onClick={() => review(type, draft.draft_id)}>
                  <ScanText className="mr-1 h-3.5 w-3.5" /> Suggest improvements
                </Button>
                <Button aria-label="Dialogue Review" size="sm" variant="outline" disabled={busyId === draft.draft_id} onClick={() => onDialogue(type, draft.draft_id)}>
                  <MessageSquareText className="mr-1 h-3.5 w-3.5" /> Improve dialogue
                </Button>
                <Button size="sm" variant="outline" disabled={busyId === draft.draft_id} onClick={() => createBranch(type, draft.draft_id)}>
                  <PenTool className="mr-1 h-3.5 w-3.5" /> Create review version
                </Button>
                {busyId === draft.draft_id ? <Loader2 className="h-4 w-4 animate-spin self-center" /> : null}
              </div>
            </article>
          )
        })}
        {arcs.filter((arc) => arc.development_status === 'draftable' || arc.development_status === 'active').map((arc) => (
          <Button key={arc.arc_id} variant="outline" disabled={busyId === arc.arc_id} onClick={() => review('arc', arc.arc_id)}>
            Review Arc: {arc.title}
          </Button>
        ))}
      </section>

      <section>
        <h3 className="mb-3 font-semibold">Findings And Recommendations</h3>
        <div className="grid gap-3 lg:grid-cols-2">
          {reports.slice(0, detailLimit).map((report) => (
            <article key={report.report_id} className="rounded-md border p-3 text-sm" data-testid="editorial-report-card">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold">{report.report_type} · {subjectIdentity(report.subject_id, report.subject_type)}</p>
                  <p className="text-xs text-muted-foreground">AI editorial review</p>
                </div>
                <span className={`rounded px-2 py-1 font-bold ${scoreTone(report.score)}`}>{report.score}</span>
              </div>
              {(report.blockers || []).length ? (
                <div className="mt-2 rounded bg-red-50 p-2 text-red-900">Blockers: {(report.blockers || []).join(' ')}</div>
              ) : null}
              <div className="mt-2 space-y-1">
                {(report.findings || []).slice(0, 5).map((finding, index) => (
                  <p key={`${report.report_id}-${index}`} className="rounded bg-muted/40 p-2">
                    <strong>{finding.category}</strong>: {finding.message}
                  </p>
                ))}
              </div>
              {(report.recommendations || []).length ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Recommendation: {(report.recommendations || []).join(' ')}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="font-semibold">Review suggested changes</h3>
        {branches.filter((branch) => passFilter === 'all' || (branch.revision_pass || 'development') === passFilter).slice(0, detailLimit).map((branch) => {
          const branchVersions = versions
            .filter((version) => version.branch_id === branch.branch_id)
            .sort((left, right) => right.version_number - left.version_number)
          const comparison = comparisons[branch.branch_id]
          return (
            <article key={branch.branch_id} className="rounded-md border p-3 text-sm" data-testid="revision-branch-card">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold">{branch.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {subjectIdentity(branch.source_draft_id, branch.source_draft_type)} · {(branch.revision_pass || 'development').replaceAll('_', ' ')} · {authorRevisionStatus(branch.status)} · {branchVersions.length} suggested versions
                  </p>
                </div>
                <span className="rounded bg-muted px-2 py-1 text-xs">{authorRevisionStatus(branch.status)}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {['draft', 'review'].includes(branch.status) ? (
                  <Button aria-label="Generate Proposal" size="sm" disabled={busyId === branch.branch_id} onClick={() => generate(branch.branch_id)}>
                    Generate suggested revision
                  </Button>
                ) : null}
                {branch.status === 'draft' && branchVersions.length ? (
                  <Button size="sm" variant="outline" onClick={() => onBranchStatus(branch.branch_id, 'review')}>Review suggested version</Button>
                ) : null}
                {branch.status === 'review' ? (
                  <>
                    <Button aria-label="Approve Branch" size="sm" onClick={() => onBranchStatus(branch.branch_id, 'approved')}>Keep this revision</Button>
                    <Button size="sm" variant="outline" onClick={() => reject(branch.branch_id)}>Reject</Button>
                  </>
                ) : null}
                {branch.status === 'approved' && branchVersions.length ? (
                  <Button size="sm" onClick={() => onApplyRevision(branch.branch_id)}>
                    Use revised version
                  </Button>
                ) : null}
                {branchVersions.length ? (
                  <Button size="sm" variant="outline" onClick={() => onCompare(branch.branch_id)}>
                    <GitCompare className="mr-1 h-3.5 w-3.5" /> Compare
                  </Button>
                ) : null}
                {branch.status !== 'archived' ? (
                  <Button size="sm" variant="outline" onClick={() => onBranchStatus(branch.branch_id, 'archived')}>Archive</Button>
                ) : null}
                {busyId === branch.branch_id ? <Loader2 className="h-4 w-4 animate-spin self-center" /> : null}
              </div>
              {branchVersions[0] ? (
                <div className="mt-3 rounded bg-muted/30 p-2">
                  <p className="max-h-32 overflow-y-auto whitespace-pre-wrap">{branchVersions[0].generated_text}</p>
                  <dl className="mt-3 grid gap-2 border-t pt-3 text-xs sm:grid-cols-2">
                    <div><dt className="font-semibold">Summary</dt><dd className="text-muted-foreground">{branchVersions[0].summary || 'Focused revision proposal'}</dd></div>
                    <div><dt className="font-semibold">Reason</dt><dd className="text-muted-foreground">{branchVersions[0].reason || branchVersions[0].change_reason}</dd></div>
                    <div><dt className="font-semibold">Affected elements</dt><dd className="text-muted-foreground">{branchVersions[0].affected_elements?.join(', ') || 'Specified editorial findings'}</dd></div>
                    <div><dt className="font-semibold">Estimated improvement</dt><dd className="text-muted-foreground">{branchVersions[0].estimated_improvement || 'medium'}</dd></div>
                    <div className="sm:col-span-2"><dt className="font-semibold">What stays unchanged</dt><dd className="text-muted-foreground">{branchVersions[0].what_stays_unchanged?.join(', ') || 'Approved planning, canon and required events'}</dd></div>
                  </dl>
                </div>
              ) : null}
              {comparison ? (
                <div className="mt-3 grid gap-3 lg:grid-cols-2" data-testid="revision-comparison">
                  <div className="rounded border p-2">
                    <p className="mb-1 text-xs font-semibold">Approved source · {comparison.source_word_count} words</p>
                    <p className="max-h-48 overflow-y-auto whitespace-pre-wrap">{comparison.source_text}</p>
                  </div>
                  <div className="rounded border p-2">
                    <p className="mb-1 text-xs font-semibold">
                      Revision v{comparison.version_number} · {comparison.revision_word_count} words · {Math.round(comparison.similarity * 100)}% similar
                    </p>
                    <p className="max-h-48 overflow-y-auto whitespace-pre-wrap">{comparison.revision_text}</p>
                  </div>
                </div>
              ) : null}
            </article>
          )
        })}
        {!branches.length ? <p className="text-sm text-muted-foreground">No suggested versions yet. Create one from an approved chapter above.</p> : null}
      </section>
      {(latestScores.length > detailLimit || reports.length > detailLimit || branches.length > detailLimit) ? <Button variant="outline" onClick={() => setDetailLimit((value) => value + 30)}>Load 30 more editorial records</Button> : null}
    </div>
  )
}
