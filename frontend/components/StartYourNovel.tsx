"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Bot, Check, ChevronRight, Circle, ClipboardPaste, Compass, Pencil, Save, SkipForward } from 'lucide-react'
import { dataApi, rc6Api } from '@/lib/api'
import type { BeginnerFlow, BeginnerStep } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

export default function StartYourNovel({
  projectId,
  autoOpen = false,
  onNavigate,
  onChanged,
}: {
  projectId: string
  autoOpen?: boolean
  onNavigate: (target: string) => void
  onChanged: () => Promise<void> | void
}) {
  const [flow, setFlow] = useState<BeginnerFlow | null>(null)
  const [open, setOpen] = useState(autoOpen)
  const [selectedId, setSelectedId] = useState('')
  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const [sourceMode, setSourceMode] = useState<'manual' | 'ai' | 'import'>('manual')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const editingRef = useRef(false)

  const load = useCallback(async () => {
    try {
      const value = await rc6Api.getBeginnerFlow(projectId)
      setFlow(value)
      const nextStep = value.steps.find((item) => item.step_id === value.current_step) || value.steps[0]
      if (!editingRef.current) {
        setSelectedId(nextStep?.step_id || '')
        setTitle(nextStep?.title || '')
        setDetails(nextStep?.details || '')
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The guided setup could not be loaded.')
    }
  }, [projectId])

  useEffect(() => {
    void load()
  }, [load])

  const selected = useMemo(
    () => flow?.steps.find((item) => item.step_id === selectedId) || flow?.steps[0] || null,
    [flow, selectedId],
  )

  function selectStep(step: BeginnerStep) {
    editingRef.current = false
    setSelectedId(step.step_id)
    setTitle(step.title || '')
    setDetails(step.details || '')
    setSourceMode('manual')
  }

  async function save(action: 'save' | 'skip' | 'reopen') {
    if (!selected) return
    if (action === 'save' && !(title.trim() || details.trim())) {
      setError('Add an idea or choose Decide later. Nothing has been saved yet.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const value = await rc6Api.updateBeginnerStep(projectId, selected.step_id, {
        action,
        title,
        details,
        source_mode: sourceMode,
      })
      setFlow(value)
      editingRef.current = false
      const nextStep = value.steps.find((item) => item.step_id === value.current_step) || value.steps[0]
      setSelectedId(nextStep?.step_id || '')
      setTitle(nextStep?.title || '')
      setDetails(nextStep?.details || '')
      setSourceMode('manual')
      await onChanged()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The step could not be saved.')
    } finally {
      setBusy(false)
    }
  }

  async function askAI() {
    if (!selected) return
    setBusy(true)
    setError('')
      setSourceMode('ai')
      editingRef.current = true
    try {
      const response = await dataApi.askProjectAssistant(
        projectId,
        selected.ai_prompt,
        selected.step_id === 'main_character' ? 'character_interviewer' : 'story_coach',
        'guide',
        'narrative_creation',
      )
      setDetails(String(response.answer || ''))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The AI suggestion could not be prepared.')
    } finally {
      setBusy(false)
    }
  }

  if (!flow) {
    return (
      <section className="rounded-xl border bg-card p-5" data-testid="start-your-novel-loading">
        <p className="font-semibold">Preparing your guided start…</p>
        <p className="mt-1 text-sm text-muted-foreground">Your existing story information will be reused.</p>
      </section>
    )
  }

  if (!open) {
    return (
      <section className="rounded-xl border border-primary/20 bg-primary/5 p-5 shadow-soft" data-testid="start-your-novel-cta">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-violet-700">Recommended for new authors</p>
            <h2 className="mt-1 text-xl font-semibold">Start Your Novel</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Move from your idea to a first scene in seven editable steps. Skip anything you want to decide later.
            </p>
          </div>
          <Button onClick={() => setOpen(true)} data-testid="start-your-novel">
            <Compass className="mr-2 h-4 w-4" />
            {flow.completion ? `Continue setup · ${flow.completion}%` : 'Start guided setup'}
          </Button>
        </div>
      </section>
    )
  }

  return (
    <section className="rounded-xl border bg-card p-5 shadow-sm" data-testid="start-your-novel-flow">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-violet-700">Guided author workflow</p>
          <h2 className="mt-1 text-xl font-semibold">Start Your Novel</h2>
          <p className="mt-1 text-sm text-muted-foreground">{flow.completed_steps} of {flow.total_steps} steps handled · {flow.completion}%</p>
        </div>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Minimize</Button>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted" aria-label={`${flow.completion}% complete`}>
        <div className="h-full rounded-full bg-violet-600 transition-all" style={{ width: `${flow.completion}%` }} />
      </div>

      <ol className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {flow.steps.map((step) => (
          <li key={step.step_id}>
            <button
              type="button"
              onClick={() => selectStep(step)}
              disabled={busy}
              className={`flex w-full items-center gap-2 rounded-lg border p-3 text-left text-sm transition-colors ${
                selected?.step_id === step.step_id ? 'border-violet-400 bg-violet-50' : 'hover:bg-muted/50'
              } disabled:cursor-wait disabled:opacity-60`}
              aria-current={selected?.step_id === step.step_id ? 'step' : undefined}
              data-testid={`beginner-step-${step.step_id}`}
            >
              {step.status === 'completed' ? <Check className="h-4 w-4 text-emerald-600" /> : step.status === 'skipped' ? <SkipForward className="h-4 w-4 text-amber-600" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
              <span className="min-w-0 flex-1 truncate">{step.order}. {step.label}</span>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
          </li>
        ))}
      </ol>

      {selected ? (
        <div className="mt-5 rounded-xl border bg-muted/20 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold">{selected.label}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{selected.description}</p>
              <p className="mt-1 text-xs text-muted-foreground">This can be changed, undone, or expanded later.</p>
            </div>
            {selected.status !== 'not_started' ? (
              <Button size="sm" variant="outline" onClick={() => void save('reopen')} disabled={busy}>
                <Pencil className="mr-2 h-4 w-4" />Edit this step
              </Button>
            ) : null}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" variant={sourceMode === 'manual' ? 'default' : 'outline'} onClick={() => setSourceMode('manual')}>
              <Pencil className="mr-2 h-4 w-4" />Enter manually
            </Button>
            <Button size="sm" variant={sourceMode === 'ai' ? 'default' : 'outline'} onClick={() => void askAI()} disabled={busy}>
              <Bot className="mr-2 h-4 w-4" />Use AI suggestion
            </Button>
            <Button size="sm" variant={sourceMode === 'import' ? 'default' : 'outline'} onClick={() => setSourceMode('import')}>
              <ClipboardPaste className="mr-2 h-4 w-4" />Import notes
            </Button>
          </div>

          <div className="mt-4 grid gap-3">
            <Input
              value={title}
              onChange={(event) => { editingRef.current = true; setTitle(event.target.value) }}
              placeholder={`${selected.label} name or short title`}
              aria-label={`${selected.label} title`}
            />
            <Textarea
              value={details}
              onChange={(event) => { editingRef.current = true; setDetails(event.target.value) }}
              rows={5}
              placeholder={sourceMode === 'import' ? 'Paste existing notes here…' : `Describe your ${selected.label.toLowerCase()}…`}
              aria-label={`${selected.label} details`}
            />
          </div>
          {error ? <p className="mt-3 text-sm text-destructive" role="alert">{error}</p> : null}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button onClick={() => void save('save')} disabled={busy}>
              <Save className="mr-2 h-4 w-4" />{busy ? 'Saving…' : 'Save and continue'}
            </Button>
            <Button variant="ghost" onClick={() => void save('skip')} disabled={busy}>
              <SkipForward className="mr-2 h-4 w-4" />Decide later
            </Button>
            <Button variant="outline" onClick={() => onNavigate(selected.target)}>
              Open full {selected.label} workspace
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
