"use client"

import { useEffect, useState } from 'react'
import { CheckCircle2, Circle, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { dataApi } from '@/lib/api'
import type { NarrativeCompleteness, NovelCreationGuide } from '@/types'


export default function NarrativeProductionPipeline({ projectId, onNavigate, showGuide = false }: {
  projectId: string
  onNavigate: (section: string) => void
  showGuide?: boolean
}) {
  const [completeness, setCompleteness] = useState<NarrativeCompleteness | null>(null)
  const [guide, setGuide] = useState<NovelCreationGuide | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([dataApi.getNarrativeCompleteness(projectId), dataApi.getNovelCreationGuide(projectId)])
      .then(([nextCompleteness, nextGuide]) => {
        if (active) {
          setCompleteness(nextCompleteness)
          setGuide(nextGuide)
        }
      })
      .catch((reason) => active && setError(reason instanceof Error ? reason.message : 'Unable to load production milestones.'))
    return () => { active = false }
  }, [projectId])

  if (error) return <div className="rounded-md border border-red-200 p-4 text-sm text-red-700">{error}</div>
  if (!completeness || !guide) return <div className="flex items-center gap-2 rounded-md border p-4 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Evaluating narrative milestones…</div>

  return (
    <section className="space-y-4 rounded-md border bg-card p-4" data-testid="narrative-production-pipeline">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Guided production pipeline</p>
          <h2 className="text-xl font-semibold">{completeness.current_milestone}</h2>
          <p className="text-sm text-muted-foreground">{completeness.overall_completion}% complete across eight narrative dimensions</p>
        </div>
        {completeness.next_actions[0] ? (
          <Button onClick={() => onNavigate(completeness.next_actions[0].target)}>{completeness.next_actions[0].label}</Button>
        ) : null}
      </div>

      <div className="grid gap-2 md:grid-cols-5">
        {completeness.milestones.map((milestone) => (
          <details key={milestone.gate_id} className={`rounded-md border p-3 ${milestone.achieved ? 'border-emerald-300 bg-emerald-50/60' : 'bg-muted/20'}`}>
            <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-semibold">
              {milestone.achieved ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
              {milestone.label}
            </summary>
            <div className="mt-2 space-y-1 text-xs text-muted-foreground">
              {milestone.criteria.map((criterion) => <p key={criterion.criterion_id}>{criterion.met ? '✓' : '○'} {criterion.label}</p>)}
            </div>
          </details>
        ))}
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {Object.values(completeness.dimensions).map((dimension) => (
          <button key={dimension.dimension} type="button" onClick={() => onNavigate(dimension.remaining[0]?.target || 'story-health')} className="rounded-md border p-3 text-left hover:bg-muted/40">
            <span className="capitalize">{dimension.dimension} completion</span>
            <span className="float-right font-semibold">{dimension.score}%</span>
            <div className="mt-2 h-1.5 overflow-hidden rounded bg-muted"><div className="h-full bg-primary" style={{ width: `${dimension.score}%` }} /></div>
          </button>
        ))}
      </div>

      {showGuide ? (
        <div className="space-y-2" data-testid="novel-creation-guide">
          <h3 className="font-semibold">Novel Creation Guide</h3>
          <p className="text-sm text-muted-foreground">Jump freely. Each step explains its purpose, participating intelligence, and remaining information.</p>
          <div className="grid gap-2 md:grid-cols-2">
            {guide.steps.map((step) => (
              <button key={step.step_id} type="button" onClick={() => onNavigate(step.target)} className="rounded-md border p-3 text-left hover:bg-muted/40">
                <div className="flex justify-between gap-2"><strong>{step.label}</strong><span>{step.completion}%</span></div>
                <p className="mt-1 text-sm text-muted-foreground">{step.why_it_matters}</p>
                <p className="mt-2 text-xs">AI: {step.ai_systems.join(', ')}</p>
                {step.required_information.length ? <p className="mt-1 text-xs text-amber-700">Needed: {step.required_information.join(', ')}</p> : null}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
