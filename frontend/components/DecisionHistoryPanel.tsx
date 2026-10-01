"use client"

import { useCallback, useEffect, useState } from 'react'
import { Eye, History, Pencil, RotateCcw, Undo2 } from 'lucide-react'
import { rc6Api } from '@/lib/api'
import type { EditableDecision } from '@/types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export default function DecisionHistoryPanel({
  projectId,
  onChanged,
}: {
  projectId: string
  onChanged: () => Promise<void> | void
}) {
  const [decisions, setDecisions] = useState<EditableDecision[]>([])
  const [editing, setEditing] = useState('')
  const [draft, setDraft] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [impactId, setImpactId] = useState('')

  const load = useCallback(async () => {
    try {
      const value = await rc6Api.getDecisions(projectId)
      setDecisions(value.decisions)
    } catch (reasonValue) {
      setError(reasonValue instanceof Error ? reasonValue.message : 'Decision history could not be loaded.')
    }
  }, [projectId])

  useEffect(() => {
    void load()
  }, [load])

  async function run(id: string, action: 'change' | 'undo' | 'reopen' | 'impact') {
    setBusy(`${action}:${id}`)
    setError('')
    try {
      if (action === 'change') await rc6Api.changeDecision(projectId, id, { answer: draft, reason })
      if (action === 'undo') await rc6Api.undoDecision(projectId, id, reason)
      if (action === 'reopen') await rc6Api.reopenDecision(projectId, id, reason)
      if (action === 'impact') {
        const updated = await rc6Api.previewDecisionImpact(projectId, id)
        setDecisions((current) => current.map((item) => item.question_id === id ? updated : item))
        setImpactId(id)
      } else {
        setEditing('')
        setDraft('')
        setReason('')
        await load()
        await onChanged()
      }
    } catch (reasonValue) {
      setError(reasonValue instanceof Error ? reasonValue.message : 'The decision could not be updated.')
    } finally {
      setBusy('')
    }
  }

  const answered = decisions.filter((item) => item.history.length || item.answered)
  if (!answered.length) return null

  return (
    <section className="mt-5 rounded-xl border p-4" data-testid="decision-history">
      <div className="flex items-start gap-3">
        <History className="mt-0.5 h-5 w-5 text-violet-600" />
        <div>
          <h3 className="font-semibold">Decision History</h3>
          <p className="text-sm text-muted-foreground">Earlier answers remain visible and editable. Preview what may change before revising one.</p>
        </div>
      </div>
      {error ? <p role="alert" className="mt-3 text-sm text-destructive">{error}</p> : null}
      <div className="mt-4 space-y-3">
        {answered.map((decision) => (
          <article key={decision.question_id} className="rounded-lg border p-4" data-testid="decision-card">
            <p className="font-medium">{decision.question}</p>
            <p className="mt-2 rounded-md bg-muted/50 p-3 text-sm">{decision.current_answer || 'This question has been reopened.'}</p>
            <p className="mt-2 text-xs text-muted-foreground">Version {decision.version} · {decision.history.length} recorded change{decision.history.length === 1 ? '' : 's'}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => {
                setEditing(decision.question_id)
                setDraft(decision.current_answer || '')
              }}>
                <Pencil className="mr-2 h-4 w-4" />Change decision
              </Button>
              <Button size="sm" variant="outline" onClick={() => void run(decision.question_id, 'impact')} disabled={Boolean(busy)}>
                <Eye className="mr-2 h-4 w-4" />What will change?
              </Button>
              <Button size="sm" variant="outline" onClick={() => void run(decision.question_id, 'undo')} disabled={!decision.can_undo || Boolean(busy)}>
                <Undo2 className="mr-2 h-4 w-4" />Undo decision
              </Button>
              <Button size="sm" variant="ghost" onClick={() => void run(decision.question_id, 'reopen')} disabled={!decision.can_reopen || Boolean(busy)}>
                <RotateCcw className="mr-2 h-4 w-4" />Reopen question
              </Button>
            </div>

            {impactId === decision.question_id ? (
              <div className="mt-3 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm" data-testid="decision-impact-preview">
                <p className="font-medium">Impact preview</p>
                <p className="mt-1 text-muted-foreground">
                  {String(decision.impact_preview?.risk_level || 'low')} risk · Review affected chapters, arcs, characters, canon, and timeline before saving.
                </p>
              </div>
            ) : null}

            {editing === decision.question_id ? (
              <div className="mt-3 space-y-3 rounded-md border bg-background p-3">
                <Textarea value={draft} onChange={(event) => setDraft(event.target.value)} rows={4} aria-label="Changed decision" />
                <Textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={2} placeholder="Why are you changing this? (optional)" aria-label="Reason for decision change" />
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => void run(decision.question_id, 'change')} disabled={!draft.trim() || Boolean(busy)}>
                    Save changed decision
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditing('')}>Cancel</Button>
                </div>
              </div>
            ) : null}

            <details className="mt-3 text-sm">
              <summary className="cursor-pointer font-medium">View decision timeline</summary>
              <ol className="mt-2 space-y-2 border-l pl-4">
                {decision.history.map((item) => (
                  <li key={`${decision.question_id}-${item.version}`}>
                    <p>Version {item.version} · {item.action}</p>
                    <p className="text-muted-foreground">{item.answer}</p>
                    {item.reason ? <p className="text-xs text-muted-foreground">Reason: {item.reason}</p> : null}
                  </li>
                ))}
              </ol>
            </details>
          </article>
        ))}
      </div>
    </section>
  )
}
