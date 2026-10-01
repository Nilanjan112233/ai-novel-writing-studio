"use client"

import { useEffect, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { dataApi } from '@/lib/api'
import { EvidenceList } from '@/components/AuthorValue'
import type { NarrativeCritique } from '@/types'


export default function NarrativeCritiquePanel({ projectId, onNavigate }: { projectId: string; onNavigate: (section: string) => void }) {
  const [critique, setCritique] = useState<NarrativeCritique | null>(null)
  const [busy, setBusy] = useState(false)
  const load = (refresh = false) => {
    setBusy(true)
    const request = refresh ? dataApi.refreshNarrativeCritique(projectId) : dataApi.getNarrativeCritique(projectId)
    request.then(setCritique).finally(() => setBusy(false))
  }
  useEffect(() => { load(false) }, [projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className="space-y-3 rounded-md border p-4" data-testid="narrative-critique-panel">
      <div className="flex items-start justify-between gap-3">
        <div><h2 className="font-semibold">Narrative Critique & Improvement Loop</h2><p className="text-sm text-muted-foreground">Consumes Story Health. Improvements remain author-controlled proposals.</p></div>
        <Button variant="outline" size="sm" onClick={() => load(true)} disabled={busy}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}<span className="ml-1">Refresh</span></Button>
      </div>
      {!critique && busy ? <p className="text-sm text-muted-foreground">Building evidence-backed critique…</p> : null}
      {critique?.findings.filter((finding) => finding.finding_type === 'critique').slice(0, 12).map((finding) => (
        <article key={finding.finding_id} className="rounded-md border p-3 text-sm">
          <div className="flex flex-wrap justify-between gap-2"><strong>{finding.category.replaceAll('_', ' ')}</strong><span className="rounded bg-muted px-2 py-0.5 text-xs">{finding.severity} · {Math.round(finding.confidence * 100)}%</span></div>
          <p className="mt-1">{finding.explanation}</p>
          <p className="mt-2 rounded bg-muted/50 p-2"><strong>Suggested improvement:</strong> {finding.suggested_improvement}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground"><span>Responsible: {finding.responsible_subsystem.replaceAll('_', ' ')}</span><span>Chapters: {finding.affected_chapters.join(', ') || 'project-wide'}</span><Button size="sm" variant="outline" onClick={() => onNavigate(({ dialogue: 'editorial', plot: 'threads', character: 'characters', canon: 'canon', timeline: 'timeline', pacing: 'story-health', continuity: 'story-health', balance: 'story-health' } as Record<string, string>)[finding.domain] || 'story-health')}>Open responsible workspace</Button></div>
          <details className="mt-2 text-xs"><summary className="cursor-pointer font-medium">Supporting evidence</summary><div className="mt-2"><EvidenceList values={finding.evidence} /></div></details>
        </article>
      ))}
      {critique && critique.critique_finding_count === 0 ? <p className="rounded border border-dashed p-4 text-sm text-muted-foreground">No additional critique findings are active.</p> : null}
    </section>
  )
}
