"use client"

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { dataApi } from '@/lib/api'

type Candidate = {
  candidate_id: string
  type: string
  name?: string
  title?: string
  question?: string
  item?: string
  text?: string
  relationship?: string
  description?: string
  source_chapter?: number
  candidate_status?: string
  authority_status?: string
  character_a?: string
  character_b?: string
  summary?: string
}

export default function KnowledgeSuggestionsPanel({ projectId, candidates, types, onChanged }: { projectId: string; candidates: Candidate[]; types: string[]; onChanged?: () => void }) {
  const [busy, setBusy] = useState<string | null>(null)
  const visible = candidates.filter((candidate) => types.includes(candidate.type))
  if (!visible.length) return null
  const label = (candidate: Candidate) => candidate.name || candidate.title || candidate.question || candidate.item || candidate.relationship || candidate.text || candidate.description || candidate.summary || (candidate.character_a && candidate.character_b ? `${candidate.character_a} and ${candidate.character_b}` : null) || 'Untitled suggestion'
  const decide = async (candidate: Candidate, decision: 'confirm' | 'reject') => {
    setBusy(candidate.candidate_id)
    try {
      await dataApi.decideStoryKnowledgeCandidate(projectId, candidate.candidate_id, decision)
      onChanged?.()
    } finally {
      setBusy(null)
    }
  }
  return (
    <section className="mt-4 rounded-lg border border-amber-200 bg-amber-50/60 p-4" data-testid="knowledge-suggestions">
      <h3 className="font-semibold text-amber-950">Suggestions for your story</h3>
      <p className="mt-1 text-sm text-amber-900/80">NovelForge noticed these details in your discussion or approved chapters. They are suggestions, not approved story truth, until you confirm them.</p>
      <div className="mt-3 space-y-2">
        {visible.slice(0, 20).map((candidate) => (
          <div key={candidate.candidate_id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-background p-3 text-sm">
            <div className="min-w-0"><p className="font-medium break-words">{label(candidate)}</p><p className="text-xs text-muted-foreground">{candidate.type.replaceAll('_', ' ')} · {candidate.source_chapter ? `Chapter ${candidate.source_chapter}` : 'Story Studio'}</p></div>
            <div className="flex gap-2"><Button size="sm" onClick={() => void decide(candidate, 'confirm')} disabled={busy === candidate.candidate_id}>Confirm</Button><Button size="sm" variant="outline" onClick={() => void decide(candidate, 'reject')} disabled={busy === candidate.candidate_id}>Not a story fact</Button></div>
          </div>
        ))}
      </div>
    </section>
  )
}
