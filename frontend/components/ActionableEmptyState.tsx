"use client"

import { useState } from 'react'
import { Bot, ClipboardPaste, Compass, Plus, Save, X } from 'lucide-react'
import { rc6Api, dataApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

type Area = 'character' | 'world' | 'timeline' | 'power' | 'relationship' | 'theme' | 'plot_thread' | 'arc' | 'mystery' | 'faction' | 'scene'

export default function ActionableEmptyState({
  projectId,
  area,
  label,
  description,
  onCreated,
  onGuide,
}: {
  projectId: string
  area: Area
  label: string
  description: string
  onCreated: () => Promise<void> | void
  onGuide: () => void
}) {
  const [mode, setMode] = useState<'manual' | 'ai' | 'import' | null>(null)
  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function askAI() {
    setMode('ai')
    setBusy(true)
    setError('')
    try {
      const result = await dataApi.askProjectAssistant(
        projectId,
        `Suggest one strong ${label.toLowerCase()} for this novel. Ground it in the existing project and keep the author in control. Put a concise name on the first line as "Title: ...", then put the usable details on the following lines. Do not describe your process.`,
        'story_coach',
        area === 'plot_thread' ? 'threads' : area,
      )
      const answer = String(result.answer || '').trim()
      const titleMatch = answer.match(/^\s*Title:\s*(.+)$/im)
      if (titleMatch?.[1]) {
        setTitle(titleMatch[1].trim())
        setDetails(answer.replace(titleMatch[0], '').trim())
      } else {
        setTitle(`Suggested ${label}`)
        setDetails(answer)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The AI suggestion could not be prepared.')
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    if (!title.trim()) return
    setBusy(true)
    setError('')
    try {
      await rc6Api.createWorkspaceEntry(projectId, {
        area,
        title: title.trim(),
        details: details.trim(),
        source_mode: mode || 'manual',
      })
      setMode(null)
      setTitle('')
      setDetails('')
      await onCreated()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `Could not add ${label.toLowerCase()}.`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="rounded-xl border border-dashed bg-muted/20 p-5" data-testid={`empty-state-${area}`}>
      <h3 className="font-semibold">Create your first {label.toLowerCase()}</h3>
      <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => setMode('manual')} data-testid={`empty-create-${area}`}>
          <Plus className="mr-2 h-4 w-4" />Create manually
        </Button>
        <Button size="sm" variant="outline" onClick={() => void askAI()} disabled={busy}>
          <Bot className="mr-2 h-4 w-4" />Generate with AI
        </Button>
        <Button size="sm" variant="outline" onClick={() => setMode('import')}>
          <ClipboardPaste className="mr-2 h-4 w-4" />Import existing
        </Button>
        <Button size="sm" variant="ghost" onClick={onGuide}>
          <Compass className="mr-2 h-4 w-4" />Continue guided setup
        </Button>
      </div>

      {mode ? (
        <div className="mt-4 space-y-3 rounded-lg border bg-background p-4" data-testid={`empty-state-form-${area}`}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-medium">
                {mode === 'ai' ? 'Review the AI suggestion' : mode === 'import' ? 'Import existing notes' : `Add ${label.toLowerCase()}`}
              </p>
              <p className="text-xs text-muted-foreground">You can edit this later. Saving updates the existing Story Bible and project guidance.</p>
            </div>
            <Button size="icon" variant="ghost" onClick={() => setMode(null)} aria-label="Close entry form"><X className="h-4 w-4" /></Button>
          </div>
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={`${label} name or title`}
            aria-label={`${label} name or title`}
          />
          <Textarea
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            placeholder={mode === 'import' ? 'Paste your existing notes here…' : `Describe the ${label.toLowerCase()}…`}
            rows={5}
            aria-label={`${label} details`}
          />
          {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
          <Button size="sm" onClick={() => void save()} disabled={busy || !title.trim()}>
            <Save className="mr-2 h-4 w-4" />{busy ? 'Saving…' : 'Save and update project'}
          </Button>
        </div>
      ) : null}
    </section>
  )
}
