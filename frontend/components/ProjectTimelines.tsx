"use client"

import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Bot, CalendarClock, ChevronRight, HeartPulse, UserRound } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { dataApi } from '@/lib/api'
import type { ExplainabilityTimeline, ProjectTimeline } from '@/types'


export function ProjectTimelineView({ projectId, onNavigate }: { projectId: string; onNavigate: (target: string) => void }) {
  const [timeline, setTimeline] = useState<ProjectTimeline | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [system, setSystem] = useState('all')
  const [date, setDate] = useState('')
  useEffect(() => { void dataApi.getProjectTimeline(projectId).then(setTimeline) }, [projectId])
  const systems = useMemo(() => [...new Set((timeline?.entries || []).flatMap((entry) => entry.affected_systems))].sort(), [timeline])
  const entries = useMemo(() => (timeline?.entries || []).filter((entry) => {
    const haystack = `${entry.action} ${entry.summary} ${entry.scene_label || ''} ${entry.chapter_number || ''}`.toLowerCase()
    return (!search || haystack.includes(search.toLowerCase()))
      && (system === 'all' || entry.affected_systems.includes(system))
      && (!date || entry.date.slice(0, 10) === date)
  }), [timeline, search, system, date])
  return (
    <div className="space-y-3" data-testid="project-timeline">
      <p className="text-sm text-muted-foreground">This records how the NovelForge project changed. Events inside the novel remain in Story Timeline.</p>
      <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]" data-testid="project-timeline-filters">
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search action, chapter, or scene" aria-label="Search project timeline" />
        <select value={system} onChange={(event) => setSystem(event.target.value)} className="rounded-md border bg-background px-3 text-sm" aria-label="Filter project timeline by system"><option value="all">All systems</option>{systems.map((item) => <option key={item}>{item}</option>)}</select>
        <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} aria-label="Filter project timeline by date" />
      </div>
      {!entries.length ? <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">{timeline?.entries.length ? 'No project events match these filters.' : 'Project evolution will appear here as you make decisions and reach milestones.'}</p> : entries.map((entry) => (
        <article key={entry.entry_id} className="rounded-lg border p-3">
          <button type="button" className="flex w-full items-start gap-3 text-left" onClick={() => setSelected(selected === entry.entry_id ? null : entry.entry_id)}>
            <span className="rounded-full bg-primary/10 p-2">{entry.actor === 'You' ? <UserRound className="h-4 w-4" /> : <Bot className="h-4 w-4" />}</span>
            <span className="min-w-0 flex-1"><strong>{entry.action}</strong><span className="mt-1 block text-sm text-muted-foreground">{entry.summary}</span><span className="mt-1 block text-xs text-muted-foreground">{entry.actor} · {entry.date ? new Date(entry.date).toLocaleString() : 'Date unavailable'}</span></span>
            <ChevronRight className={`h-4 w-4 transition-transform ${selected === entry.entry_id ? 'rotate-90' : ''}`} />
          </button>
          {selected === entry.entry_id ? <div className="ml-11 mt-3 rounded-md bg-muted/60 p-3 text-sm"><p>{entry.replay.outcome}</p><p className="mt-2 text-xs text-muted-foreground">Affected: {entry.affected_systems.join(', ')}</p><Button className="mt-3" size="sm" variant="outline" onClick={() => onNavigate(entry.destination)}>Open related workspace <ArrowRight className="ml-1 h-3 w-3" /></Button></div> : null}
        </article>
      ))}
    </div>
  )
}

export function ExplainabilityTimelineView({ projectId, onNavigate }: { projectId: string; onNavigate: (target: string) => void }) {
  const [timeline, setTimeline] = useState<ExplainabilityTimeline | null>(null)
  useEffect(() => { void dataApi.getExplainabilityTimeline(projectId).then(setTimeline) }, [projectId])
  return (
    <div className="space-y-3" data-testid="explainability-timeline">
      <p className="text-sm text-muted-foreground">Every comparison explains what changed, why the score moved, and where to act.</p>
      {!timeline?.changes.length ? <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">Run Narrative Analysis again after a story change to create the first comparison.</p> : timeline.changes.map((change) => (
        <article key={change.change_id} className="rounded-lg border p-4">
          <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><HeartPulse className="h-5 w-5 text-primary" /><strong>Story Health {change.overall.from ?? '—'} <ArrowRight className="inline h-4 w-4" /> {change.overall.to ?? '—'}</strong></div><span className={`rounded-full px-2 py-1 text-xs font-semibold ${change.overall.delta >= 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>{change.overall.delta > 0 ? '+' : ''}{change.overall.delta}</span></div>
          <p className="mt-3 text-sm">{change.what_happened}</p><p className="mt-1 text-sm text-muted-foreground">{change.why_it_matters}</p>
          <div className="mt-3 flex flex-wrap gap-2">{change.score_changes.map((score) => <span key={score.category} className="rounded bg-muted px-2 py-1 text-xs">{score.label}: {score.from} → {score.to} ({score.delta > 0 ? '+' : ''}{score.delta})</span>)}</div>
          <div className="mt-3 space-y-2">{change.reasons.map((reason) => <button key={`${reason.finding_id}-${reason.direction}`} type="button" onClick={() => onNavigate(reason.destination)} className="block w-full rounded-md border p-2 text-left text-sm hover:bg-muted">{reason.message}</button>)}</div>
          <Button className="mt-3" size="sm" variant="outline" onClick={() => onNavigate(change.suggested_next_step)}>Review supporting evidence</Button>
        </article>
      ))}
    </div>
  )
}
