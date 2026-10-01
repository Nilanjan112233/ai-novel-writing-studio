import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import DraftingWorkspace from '@/components/DraftingWorkspace'
import { numberedTitle } from '@/lib/storyLabels'
import type {
  ArcChecklistItem,
  ArcDependency,
  ArcDevelopmentReport,
  ArtifactRegistryEntry,
  ChapterPlan,
  ChapterDraft,
  CharacterProgression,
  ContinuityReport,
  EvolutionEvent,
  KnowledgeEntry,
  PowerProgression,
  ScenePlanV2,
  SceneDraft,
  StoryArc,
} from '@/types'


function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="min-w-0 rounded-md border p-3">
      <h3 className="mb-2 font-semibold">{title}</h3>
      {children}
    </section>
  )
}


export default function ArcDevelopmentWorkspace({
  arcs,
  reports,
  checklists,
  dependencies,
  chapters,
  scenes,
  characterProgressions,
  powerProgressions,
  knowledge,
  knowledgeEvolutions,
  foreshadowChains,
  artifacts,
  artifactEvolutions,
  onActivate,
  onChecklistStatus,
  sceneDrafts = [],
  chapterDrafts = [],
  continuityReports = [],
  draftableArcIds = [],
  draftActionId = null,
  onGenerateScene = () => undefined,
  onGenerateChapter = () => undefined,
  onPlanStatus = () => undefined,
  onDraftStatus = () => undefined,
  onRegenerateDraft = () => undefined,
  onRollbackDraft = () => undefined,
}: {
  arcs: StoryArc[]
  reports: ArcDevelopmentReport[]
  checklists: ArcChecklistItem[]
  dependencies: ArcDependency[]
  chapters: ChapterPlan[]
  scenes: ScenePlanV2[]
  characterProgressions: CharacterProgression[]
  powerProgressions: PowerProgression[]
  knowledge: KnowledgeEntry[]
  knowledgeEvolutions: EvolutionEvent[]
  foreshadowChains: EvolutionEvent[]
  artifacts: ArtifactRegistryEntry[]
  artifactEvolutions: EvolutionEvent[]
  onActivate: (arcId: string) => void
  onChecklistStatus: (itemId: string, status: string) => void | Promise<void>
  sceneDrafts?: SceneDraft[]
  chapterDrafts?: ChapterDraft[]
  continuityReports?: ContinuityReport[]
  draftableArcIds?: string[]
  draftActionId?: string | null
  onGenerateScene?: (sceneId: string, options?: { allowExploratory?: boolean }) => void
  onGenerateChapter?: (chapterPlanId: string) => void
  onPlanStatus?: (type: 'scene' | 'chapter', planId: string, status: string) => void | Promise<void>
  onDraftStatus?: (type: 'scene' | 'chapter', draftId: string, status: string, reason?: string) => void
  onRegenerateDraft?: (type: 'scene' | 'chapter', draftId: string, reason: string, operation?: string) => void
  onRollbackDraft?: (type: 'scene' | 'chapter', draftId: string) => void
}) {
  const defaultArc = arcs.find((arc) => arc.focus_role === 'current') || arcs[0]
  const [selectedArcId, setSelectedArcId] = useState(defaultArc?.arc_id || '')
  const [workspaceTab, setWorkspaceTab] = useState<'planning' | 'drafting'>('planning')
  const selectedArc = arcs.find((arc) => arc.arc_id === selectedArcId) || defaultArc
  const arcId = selectedArc?.arc_id || ''
  const report = reports.find((item) => item.arc_id === arcId)
  const arcChecklist = checklists.filter((item) => item.arc_id === arcId)
  const arcDependencies = dependencies.filter((item) => item.arc_id === arcId)
  const arcChapters = chapters.filter((item) => item.arc_id === arcId)
  const chapterIds = new Set(arcChapters.map((item) => item.chapter_plan_id))
  const arcScenes = scenes.filter(
    (item) => item.arc_id === arcId || (item.chapter_plan_id && chapterIds.has(item.chapter_plan_id)),
  )
  const dimensions = useMemo(
    () => Object.entries(report?.dimensions || {}).sort((left, right) => right[1].weight - left[1].weight),
    [report],
  )
  const supportedReviewItems = arcChecklist.filter((item) => {
    if (['approved', 'completed', 'waived'].includes(item.status)) return false
    if (item.source !== 'system') return false
    return Boolean(report?.dimensions?.[item.dimension]?.data_complete)
  })

  const approveSupportedItems = async () => {
    for (const item of supportedReviewItems) {
      await onChecklistStatus(item.item_id, 'approved')
    }
  }

  if (!selectedArc) {
    return <p className="text-sm text-muted-foreground">Create an arc to begin development.</p>
  }

  return (
    <div className="space-y-4" data-testid="arc-development-workspace">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="min-w-[260px] text-sm">
          <span className="mb-1 block font-medium">Focused arc</span>
          <select
            value={selectedArc.arc_id}
            onChange={(event) => setSelectedArcId(event.target.value)}
            className="h-10 w-full rounded-md border bg-background px-3"
            data-testid="arc-development-selector"
          >
            {arcs.map((arc) => (
              <option key={arc.arc_id} value={arc.arc_id}>{arc.title}</option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-muted px-2 py-1 text-xs font-semibold">
            {(report?.development_status || selectedArc.development_status || 'idea').toUpperCase()}
          </span>
          <span className="rounded bg-muted px-2 py-1 text-xs">
            {(report?.focus_role || selectedArc.focus_role || 'future').toUpperCase()}
          </span>
          {selectedArc.focus_role !== 'current' ? (
            <Button size="sm" onClick={() => onActivate(selectedArc.arc_id)}>Make Current</Button>
          ) : null}
        </div>
      </div>

      <section className="rounded-lg border border-primary/25 bg-primary/5 p-4" aria-label="Arc review guidance">
        <p className="font-semibold">Review this arc before NovelForge plans scenes</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Make this the current arc, then confirm the planning items that match your intent. This approval applies only to the arc plan; it does not approve canon or prose.
        </p>
        {supportedReviewItems.length > 0 ? (
          <Button className="mt-3" variant="outline" onClick={() => void approveSupportedItems()}>
            Confirm {supportedReviewItems.length} supported planning item{supportedReviewItems.length === 1 ? '' : 's'}
          </Button>
        ) : null}
      </section>

      <div className="flex gap-2 border-b pb-2" role="tablist" aria-label="Arc workspace">
        <Button
          size="sm"
          variant={workspaceTab === 'planning' ? 'default' : 'outline'}
          onClick={() => setWorkspaceTab('planning')}
          role="tab"
          aria-selected={workspaceTab === 'planning'}
        >
          Development
        </Button>
        <Button
          size="sm"
          variant={workspaceTab === 'drafting' ? 'default' : 'outline'}
          onClick={() => setWorkspaceTab('drafting')}
          role="tab"
          aria-selected={workspaceTab === 'drafting'}
          data-testid="arc-drafting-tab"
        >
          Drafting
        </Button>
      </div>

      <div className={workspaceTab === 'planning' ? 'space-y-4' : 'hidden'}>
      <div className="grid gap-3 lg:grid-cols-[240px_1fr]">
        <Card title="Maturity">
          <div className="text-center">
            <p className="text-5xl font-semibold" data-testid="arc-maturity-score">
              {report?.maturity_score ?? selectedArc.arc_maturity_score ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">
              optional depth target {report?.maturity_threshold ?? selectedArc.maturity_threshold ?? 85}
            </p>
            {report?.draftable && (report.maturity_score ?? 0) < (report.maturity_threshold ?? 85) ? (
              <p className="mt-1 text-xs text-muted-foreground">Core planning is approved. Optional details can still deepen this arc.</p>
            ) : null}
            <p className={`mt-2 text-sm font-semibold ${report?.draftable ? 'text-emerald-700' : 'text-amber-700'}`}>
              {report?.draftable ? 'DRAFTABLE' : 'DEVELOPING'}
            </p>
          </div>
        </Card>
        <Card title="Maturity Dimensions">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {dimensions.map(([name, dimension]) => (
              <div key={name} className="rounded bg-muted/50 p-2 text-sm">
                <div className="flex justify-between gap-2">
                  <span>{name.replaceAll('_', ' ')}</span>
                  <strong>{dimension.score}</strong>
                </div>
                <div className="mt-1 h-1.5 rounded bg-muted">
                  <div className="h-1.5 rounded bg-primary" style={{ width: `${dimension.score}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card title="Checklist And Blockers">
          <div className="space-y-2" data-testid="arc-development-checklist">
            {arcChecklist.map((item) => (
              <div key={item.item_id} className="flex flex-wrap items-center justify-between gap-2 rounded bg-muted/40 p-2 text-sm">
                <div className="min-w-0">
                  <p className="font-medium">{item.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.priority} · {item.dimension.replaceAll('_', ' ')} · {item.status === 'missing' && report?.dimensions?.[item.dimension]?.data_complete ? 'supported by the current plan' : item.status}
                  </p>
                </div>
                {!['approved', 'completed', 'waived'].includes(item.status) ? (
                  <Button size="sm" variant="outline" onClick={() => onChecklistStatus(item.item_id, 'approved')}>
                    Approve
                  </Button>
                ) : null}
              </div>
            ))}
            {report?.blockers?.length ? (
              <div className="rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
                {report.blockers.map((blocker) => <p key={blocker}>{blocker}</p>)}
              </div>
            ) : null}
          </div>
        </Card>
        <Card title="Dependencies">
          <div className="space-y-2" data-testid="arc-development-dependencies">
            {arcDependencies.length === 0 ? <p className="text-sm text-muted-foreground">No blocking dependencies.</p> : arcDependencies.map((dependency) => (
              <div key={dependency.dependency_id} className="rounded bg-muted/40 p-2 text-sm">
                <p className="font-medium">{dependency.dependency_type.replaceAll('_', ' ')}</p>
                <p className="break-words text-xs text-muted-foreground">
                  {dependency.target_id} · {dependency.status} · {dependency.validation_reason || 'Not evaluated'}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <Card title={`Chapter Plans (${arcChapters.length})`}>
          <div className="space-y-2" data-testid="arc-chapter-plans">
            {arcChapters.map((chapter) => (
              <div key={chapter.chapter_plan_id} className="rounded bg-muted/40 p-2 text-sm">
                <p className="font-medium">{numberedTitle('chapter', chapter.chapter_number, chapter.title)}</p>
                <p className="mt-1 break-words">{chapter.purpose}</p>
                <p className="text-xs text-muted-foreground">{chapter.status} · {chapter.conflict || 'Conflict open'}</p>
              </div>
            ))}
          </div>
        </Card>
        <Card title={`Scene Plans (${arcScenes.length})`}>
          <div className="space-y-2" data-testid="arc-scene-plans">
            {arcScenes.map((scene) => (
              <div key={scene.scene_id} className="rounded bg-muted/40 p-2 text-sm">
                <p className="font-medium">{scene.title}</p>
                <p className="mt-1 break-words">{scene.purpose}</p>
                <p className="text-xs text-muted-foreground">{scene.status} · Outcome: {scene.outcome || 'Open'}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Card title="Character Progression">
          {characterProgressions.filter((item) => item.arc_id === arcId).map((item) => (
            <p key={item.character} className="mb-2 text-sm">
              <strong>{item.character}</strong>: {item.arc_start_state || item.current_state} → {item.arc_midpoint_state || '?'} → {item.arc_end_state || item.desired_state}
            </p>
          ))}
        </Card>
        <Card title="Power Progression">
          {powerProgressions.filter((item) => item.arc_id === arcId).map((item) => (
            <p key={item.character} className="mb-2 text-sm">
              <strong>{item.character}</strong>: {item.starting_power} → {item.ending_power}
            </p>
          ))}
        </Card>
        <Card title="Knowledge Evolution">
          <p className="text-sm">{knowledge.filter((item) => item.arc_id === arcId).length} knowledge entries</p>
          <p className="text-sm">{knowledgeEvolutions.filter((item) => item.arc_id === arcId).length} evolution events</p>
        </Card>
        <Card title="Foreshadow Chains">
          <p className="text-sm">{foreshadowChains.filter((item) => item.arc_id === arcId).length} foreshadowing links</p>
        </Card>
        <Card title="Artifacts">
          <p className="text-sm">{artifacts.filter((item) => item.arc_ids?.includes(arcId)).length} linked artifacts</p>
          <p className="text-sm">{artifactEvolutions.filter((item) => item.arc_id === arcId).length} evolution events</p>
        </Card>
        <Card title="Readiness">
          <p className="text-sm font-semibold">{report?.readiness_status || selectedArc.readiness_status}</p>
          <p className="text-xs text-muted-foreground">
            Future arcs do not block this arc.
          </p>
        </Card>
      </div>
      </div>
      {workspaceTab === 'drafting' ? (
        <DraftingWorkspace
          arcs={arcs}
          chapters={chapters}
          scenes={scenes}
          sceneDrafts={sceneDrafts}
          chapterDrafts={chapterDrafts}
          continuityReports={continuityReports}
          draftableArcIds={draftableArcIds}
          fixedArcId={arcId}
          busyId={draftActionId}
          onGenerateScene={onGenerateScene}
          onGenerateChapter={onGenerateChapter}
          onPlanStatus={onPlanStatus}
          onStatus={onDraftStatus}
          onRegenerate={onRegenerateDraft}
          onRollback={onRollbackDraft}
        />
      ) : null}
    </div>
  )
}
