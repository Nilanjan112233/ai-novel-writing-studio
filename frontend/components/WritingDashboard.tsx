'use client'

import { useEffect, useState } from 'react'
import {
  ArrowRight,
  BookOpen,
  Check,
  Clock3,
  Feather,
  Flame,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { dataApi } from '@/lib/api'
import { numberedTitle } from '@/lib/storyLabels'
import type { WritingDashboard as WritingDashboardData } from '@/types'


export default function WritingDashboard({
  projectId,
  refreshKey,
  busyId,
  onNavigate,
  onGenerate,
}: {
  projectId: string
  refreshKey: string
  busyId?: string | null
  onNavigate?: (target: string) => void
  onGenerate: (sceneId: string, allowExploratory: boolean) => void
}) {
  const [dashboard, setDashboard] = useState<WritingDashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    setError('')
    void dataApi.getWritingDashboard(projectId, controller.signal)
      .then((result) => setDashboard(result as WritingDashboardData))
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setError(reason instanceof Error ? reason.message : 'Writing status is temporarily unavailable.')
      })
    return () => controller.abort()
  }, [projectId, refreshKey])

  if (error) {
    return (
      <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950" aria-live="polite">
        <p className="font-semibold">Writing status could not be refreshed.</p>
        <p className="mt-1">{error}</p>
        <Button className="mt-3" size="sm" variant="outline" onClick={() => window.location.reload()}>
          <RefreshCw className="mr-1.5 h-4 w-4" /> Retry
        </Button>
      </section>
    )
  }
  if (!dashboard) {
    return (
      <section className="flex min-h-36 items-center justify-center rounded-xl border bg-muted/20" aria-label="Loading writing dashboard">
        <Loader2 className="mr-2 h-5 w-5 animate-spin motion-reduce:animate-none" />
        <span className="text-sm">Preparing your writing desk…</span>
      </section>
    )
  }

  const metrics = dashboard.metrics
  const handleNext = () => {
    if (
      dashboard.next_action.action === 'Generate draft'
      && dashboard.next_action.scene_id
    ) {
      onGenerate(
        dashboard.next_action.scene_id,
        Boolean(dashboard.next_action.allow_exploratory),
      )
      return
    }
    onNavigate?.(dashboard.next_action.target)
  }

  return (
    <section className="overflow-hidden rounded-xl border bg-gradient-to-br from-background via-background to-primary/5 shadow-sm" data-testid="writing-dashboard">
      <div className="border-b p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Writing desk</p>
            <h2 className="mt-1 text-xl font-semibold">
              {dashboard.current_chapter
                ? numberedTitle('chapter', dashboard.current_chapter.number, dashboard.current_chapter.title)
                : 'Your first chapter starts here'}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {dashboard.current_scene?.title || 'Plan a scene to begin writing.'}
              {dashboard.current_draft ? ` · ${dashboard.current_draft.version_label}` : ''}
            </p>
          </div>
          <span className="rounded-full border bg-background px-3 py-1 text-xs font-semibold">
            {dashboard.workflow.active_stage}
          </span>
        </div>

        <ol className="mt-4 flex flex-wrap gap-2" aria-label="Writing workflow">
          {dashboard.workflow.steps.map((step, index) => (
            <li
              key={step.title}
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
                step.current
                  ? 'border-primary bg-primary text-primary-foreground'
                  : step.complete
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                    : 'bg-background text-muted-foreground'
              }`}
              aria-current={step.current ? 'step' : undefined}
            >
              {step.complete ? <Check className="h-3 w-3" /> : <span>{index + 1}</span>}
              {step.title}
            </li>
          ))}
        </ol>
      </div>

      <div className="grid gap-px bg-border sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Words', value: metrics.words.toLocaleString(), Icon: Feather },
          { label: 'Reading time', value: `${metrics.reading_minutes} min`, Icon: Clock3 },
          { label: 'Writing streak', value: `${metrics.writing_streak_days} day${metrics.writing_streak_days === 1 ? '' : 's'}`, Icon: Flame },
          { label: 'Scenes approved', value: `${metrics.approved_scenes} / ${metrics.total_scenes}`, Icon: BookOpen },
        ].map(({ label, value, Icon }) => (
          <div key={label} className="flex items-center gap-3 bg-background/95 p-3">
            <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
            <div>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="font-semibold">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(17rem,0.65fr)]">
        <div className="rounded-lg border bg-background p-3">
          <div className="flex items-start gap-2">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            <div>
              <p className="font-semibold">{dashboard.next_action.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{dashboard.next_action.explanation}</p>
            </div>
          </div>
          <Button className="mt-3" size="sm" onClick={handleNext} disabled={busyId === dashboard.next_action.scene_id}>
            {busyId === dashboard.next_action.scene_id ? <><Loader2 className="mr-1.5 h-4 w-4 animate-spin motion-reduce:animate-none" />Writing scene…</> : <>{dashboard.next_action.action} <ArrowRight className="ml-1.5 h-4 w-4" /></>}
          </Button>
        </div>
        <div className="rounded-lg border bg-background p-3 text-sm">
          <p className="font-semibold">Story context ready</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Drafts reuse your planning and Narrative Intelligence instead of rebuilding a separate story.
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(dashboard.context_used).map(([name, count]) => (
              <span key={name} className="rounded-full bg-muted px-2 py-1 text-xs">
                {count} {name.replaceAll('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      </div>

      {dashboard.scene_health.blockers.length ? (
        <div className="border-t border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <div className="flex items-start gap-2">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">This can be an exploratory draft, but approval is still protected.</p>
              <p className="mt-1">
                Resolve these planning checks before the scene can become approved canon:
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {dashboard.scene_health.blockers.slice(0, 4).map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
              {onNavigate ? (
                <Button className="mt-3" size="sm" variant="outline" onClick={() => onNavigate('arc-development')}>
                  Review planning checks <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
      {dashboard.scene_health.coaching_notes?.length ? (
        <div className="border-t border-sky-200 bg-sky-50 p-4 text-sm text-sky-950" role="note">
          <p className="font-semibold">Before final prose</p>
          {dashboard.scene_health.coaching_notes.map((note) => (
            <p key={note} className="mt-1">{note}</p>
          ))}
        </div>
      ) : null}
    </section>
  )
}
