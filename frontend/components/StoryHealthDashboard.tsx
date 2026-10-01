"use client"

import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Loader2, Search, Network } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { EvidenceList } from '@/components/AuthorValue'
import type {
  ChangeImpact,
  ChapterIntelligence,
  StoryAuditReport,
  StoryHealth,
} from '@/types'


const changeTypes = [
  'character_removal',
  'character_addition',
  'timeline_change',
  'arc_change',
  'ending_change',
  'mystery_change',
  'artifact_change',
  'relationship_change',
]

const intelligenceDomains = [
  ['all', 'All findings'],
  ['character', 'Characters'],
  ['canon', 'Canon'],
  ['timeline', 'Timeline'],
  ['plot', 'Plot threads'],
  ['pacing', 'Pacing'],
  ['continuity', 'Continuity'],
  ['balance', 'Balance'],
] as const

export default function StoryHealthDashboard({
  health,
  audits,
  chapters,
  impacts,
  busyId,
  onAudit,
  onPreviewImpact,
  onImpactStatus,
}: {
  health: StoryHealth | null
  audits: StoryAuditReport[]
  chapters: ChapterIntelligence[]
  impacts: ChangeImpact[]
  busyId: string | null
  onAudit: () => void
  onPreviewImpact: (changeType: string, target: Record<string, unknown>) => void
  onImpactStatus: (impactId: string, status: 'approved' | 'rejected') => void
}) {
  const [changeType, setChangeType] = useState('character_removal')
  const [target, setTarget] = useState('')
  const [activeDomain, setActiveDomain] = useState<string>('all')
  const latestAudit = audits[0]
  const latestImpact = impacts[0]
  const metrics = health?.metrics
  const intelligenceFindings = (health?.findings || []).filter(
    (finding) => activeDomain === 'all' || finding.domain === activeDomain,
  )
  const dimensions = health?.dimension_scores || {}
  const notEnoughStory = health?.evaluation_status === 'not_enough_story'
  const metricCards = metrics ? [
    ['Approved chapters', metrics.total_chapters],
    ['Approved chapter words', metrics.total_words.toLocaleString()],
    ['Open mysteries', metrics.open_mysteries],
    ['Unresolved promises', metrics.unresolved_promises],
    ['Canon conflicts', metrics.canon_conflicts],
    ['Continuity warnings', metrics.continuity_warnings],
    ['Pacing warnings', metrics.pacing_warnings],
    ['Editorial blockers', metrics.editorial_blockers],
  ] : []

  return (
    <div className="space-y-5" data-testid="story-health-dashboard">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Story Consistency</p>
          <div className="mt-1 flex items-center gap-3">
            <span className="text-4xl font-semibold" data-testid="story-health-score">
              {notEnoughStory ? '--' : (health?.story_health_score ?? '--')}
            </span>
            <span className={`rounded px-2 py-1 text-xs font-semibold ${
              health?.status === 'healthy'
                ? 'bg-emerald-100 text-emerald-800'
                : health?.status === 'watch'
                  ? 'bg-amber-100 text-amber-800'
                  : 'bg-rose-100 text-rose-800'
            }`}>
              {notEnoughStory ? 'not evaluated' : (health?.status?.replaceAll('_', ' ') || 'calculating')}
            </span>
          </div>
        </div>
        <Button onClick={onAudit} disabled={busyId !== null} data-testid="run-story-audit">
          {busyId === 'audit'
            ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            : <Search className="mr-2 h-4 w-4" />}
          Run Story Audit
        </Button>
      </div>
      <p className="rounded-lg border border-sky-100 bg-sky-50/60 p-3 text-sm text-sky-950">
        {notEnoughStory
          ? 'There is not enough developed story material to judge consistency yet. Develop the story first; NovelForge will evaluate it as connected planning and writing appear.'
          : 'This score measures narrative consistency—not how much you have written. Content completeness, draft progress, revision progress, and publication readiness are tracked separately in the production milestones.'}
      </p>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="Story context metrics, not scored progress">
        {metricCards.map(([label, value]) => (
          <div key={String(label)} className="rounded-md border p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <section className="rounded-md border p-4" data-testid="narrative-intelligence-platform">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5 text-sky-600" />
              <h3 className="font-semibold">Narrative Intelligence</h3>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              One analysis graph powers Story Health, Canon, Timeline, Characters, Plot Threads, and the Story Bible.
            </p>
          </div>
          <p className="max-w-sm text-right text-xs text-muted-foreground">Scores update after approved story changes and always retain their supporting evidence.</p>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {intelligenceDomains.slice(1).map(([domain, label]) => (
            <button
              key={domain}
              type="button"
              onClick={() => setActiveDomain(domain)}
              className={`rounded-md border p-3 text-left transition-colors ${activeDomain === domain ? 'border-sky-500 bg-sky-50' : 'hover:bg-muted/60'}`}
              data-testid={`health-${domain}`}
            >
              <p className="text-xs font-semibold uppercase text-muted-foreground">{label} Health</p>
              <p className="mt-1 text-2xl font-semibold">{notEnoughStory ? '--' : (dimensions[domain] ?? '--')}</p>
            </button>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Intelligence domains">
          {intelligenceDomains.map(([domain, label]) => (
            <Button key={domain} size="sm" variant={activeDomain === domain ? 'default' : 'outline'} onClick={() => setActiveDomain(domain)} role="tab" aria-selected={activeDomain === domain}>
              {label}
            </Button>
          ))}
        </div>
        <div className="mt-3 grid gap-3 lg:grid-cols-2" data-testid="narrative-findings">
          {intelligenceFindings.slice(0, 50).map((finding) => (
            <article key={finding.finding_id} className="rounded-md border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">{finding.category.replaceAll('_', ' ')}</p>
                <span className={`rounded px-2 py-1 text-xs font-semibold ${finding.severity === 'critical' || finding.severity === 'high' ? 'bg-rose-100 text-rose-800' : finding.severity === 'medium' || finding.severity === 'warning' ? 'bg-amber-100 text-amber-800' : 'bg-sky-100 text-sky-800'}`}>
                  {finding.severity}
                </span>
              </div>
              <div className="mt-2 space-y-2"><div><p className="text-xs font-semibold uppercase text-muted-foreground">What happened</p><p className="mt-1 text-muted-foreground">{finding.explanation}</p></div><div><p className="text-xs font-semibold uppercase text-muted-foreground">Why it matters</p><p className="mt-1 text-muted-foreground">This concern can weaken reader trust, clarity, or narrative momentum in the affected locations.</p></div></div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                {finding.affected_chapters.map((chapter) => <span key={`chapter-${chapter}`} className="rounded bg-muted px-2 py-1">Chapter {chapter}</span>)}
                {finding.affected_scenes.map((scene) => <span key={`scene-${scene}`} className="rounded bg-muted px-2 py-1">Scene {scene}</span>)}
                <span className="rounded bg-muted px-2 py-1">{Math.round(finding.confidence * 100)}% confidence</span>
              </div>
              {finding.evidence.length ? (
                <details className="mt-3">
                  <summary className="cursor-pointer font-medium">Supporting evidence</summary>
                  <div className="mt-2"><EvidenceList values={finding.evidence} /></div>
                </details>
              ) : null}
              {finding.recommended_actions.length ? (
                <div className="mt-3 rounded bg-sky-50 p-2 text-sky-950">
                  <p className="font-medium">How to improve it</p>
                  <p className="mt-1">{finding.recommended_actions[0]}</p>
                </div>
              ) : null}
            </article>
          ))}
          {!intelligenceFindings.length ? <p className="text-sm text-muted-foreground">No active findings in this domain.</p> : null}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-md border p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-semibold">Latest audit findings</h3>
            <span className="text-xs text-muted-foreground">
              {latestAudit?.findings.length || 0} findings
            </span>
          </div>
          <div className="mt-3 max-h-96 space-y-2 overflow-y-auto">
            {!latestAudit?.findings.length ? (
              <p className="text-sm text-muted-foreground">No story audit has been recorded.</p>
            ) : latestAudit.findings.slice(0, 40).map((finding, index) => (
              <div key={finding.finding_id || `${finding.category}-${index}`} className="rounded bg-muted p-3 text-sm">
                <div className="flex items-start gap-2">
                  {finding.severity === 'info'
                    ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-sky-600" />
                    : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />}
                  <div className="min-w-0">
                    <p className="font-medium">{finding.category.replaceAll('_', ' ')}</p>
                    <p className="mt-1 break-words text-muted-foreground">{finding.message}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-md border p-4">
          <h3 className="font-semibold">Change impact preview</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Inspect affected story records before approving a structural change.
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <select
              value={changeType}
              onChange={(event) => setChangeType(event.target.value)}
              className="h-10 min-w-0 rounded-md border bg-background px-3 text-sm"
              aria-label="Change type"
            >
              {changeTypes.map((item) => (
                <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>
              ))}
            </select>
            <input
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              placeholder="Character, mystery, artifact..."
              className="h-10 min-w-0 rounded-md border bg-background px-3 text-sm"
              aria-label="Change target"
            />
            <Button
              variant="outline"
              disabled={!target.trim() || busyId !== null}
              onClick={() => onPreviewImpact(changeType, { name: target.trim() })}
              data-testid="preview-change-impact"
            >
              Preview
            </Button>
          </div>
          {latestImpact ? (
            <div className="mt-4 rounded-md border p-3" data-testid="change-impact-preview">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">
                  {latestImpact.total_affected} affected records
                </p>
                <span className="rounded bg-muted px-2 py-1 text-xs font-semibold">
                  {latestImpact.risk} risk
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                {Object.entries(latestImpact.counts)
                  .filter(([, count]) => count > 0)
                  .map(([group, count]) => (
                    <span key={group} className="rounded bg-muted px-2 py-1">
                      {group.replaceAll('_', ' ')}: {count}
                    </span>
                  ))}
              </div>
              {latestImpact.status === 'preview' ? (
                <div className="mt-3 flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => onImpactStatus(latestImpact.impact_id, 'approved')}
                    disabled={busyId !== null}
                  >
                    Approve impact
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onImpactStatus(latestImpact.impact_id, 'rejected')}
                    disabled={busyId !== null}
                  >
                    Reject
                  </Button>
                </div>
              ) : (
                <p className="mt-3 text-sm font-medium">Decision: {latestImpact.status}</p>
              )}
            </div>
          ) : null}
        </section>
      </div>

      <section className="rounded-md border p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold">Chapter intelligence memory</h3>
          <span className="text-xs text-muted-foreground">
            {chapters.filter((item) => item.active).length} active records
          </span>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {chapters.slice(-9).reverse().map((chapter) => (
            <div key={chapter.intelligence_id} className="rounded bg-muted p-3 text-sm">
              <p className="font-medium">Chapter {chapter.chapter_number}</p>
              <p className="mt-1 line-clamp-3 text-muted-foreground">{chapter.chapter_summary}</p>
              <p className="mt-2 text-xs">
                {chapter.future_obligations.length} obligations · {chapter.word_count.toLocaleString()} words
              </p>
            </div>
          ))}
          {!chapters.length ? (
            <p className="text-sm text-muted-foreground">
              Approve a chapter to create its long-term intelligence record.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  )
}
