"use client"

import { useCallback, useEffect, useMemo, useState, type SyntheticEvent } from 'react'
import { AlertTriangle, BookOpen, CheckCircle2, ChevronDown, Clock3, Eye, GitBranch, Loader2, PenLine, RefreshCw, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { dataApi } from '@/lib/api'
import type { ChapterContextView, ChapterVersionComparison, WritingActivity, WritingState, WritingStateChapter } from '@/types'

type Props = { projectId: string; onNavigate?: (target: string) => void; onEditChapter?: (draftId: string) => void }

function statusLabel(status: string) {
  return status === 'approved' ? 'Approved' : status === 'review' ? 'In review' : status === 'draft' ? 'Draft' : status.replaceAll('_', ' ')
}

function statusClass(status: string) {
  if (status === 'approved') return 'bg-emerald-100 text-emerald-800'
  if (status === 'review') return 'bg-amber-100 text-amber-800'
  return 'bg-muted text-muted-foreground'
}

export default function WritingWorkspace({ projectId, onNavigate, onEditChapter }: Props) {
  const [state, setState] = useState<WritingState | null>(null)
  const [drafts, setDrafts] = useState<any[]>([])
  const [selected, setSelected] = useState<WritingStateChapter | null>(null)
  const [context, setContext] = useState<ChapterContextView | null>(null)
  const [comparison, setComparison] = useState<ChapterVersionComparison | null>(null)
  const [activity, setActivity] = useState<WritingActivity | null>(null)
  const [showVersions, setShowVersions] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionBusy, setActionBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editingText, setEditingText] = useState('')
  const [editNotice, setEditNotice] = useState('')
  const [selectedText, setSelectedText] = useState('')
  const [selectionBusy, setSelectionBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      // The chapter state and draft lineage are the safety-critical result of
      // an approval. Activity is a durable, secondary projection and may be
      // temporarily unavailable while enrichment/recovery is being refreshed.
      // Keep those concerns separate so a safe approval is never presented as
      // a failed save merely because the activity feed could not be read.
      const [nextState, nextDrafts] = await Promise.all([dataApi.getWritingState(projectId), dataApi.getChapterDrafts(projectId)])
      setState(nextState); setDrafts(Array.isArray(nextDrafts) ? nextDrafts : [])
      setSelected((current) => current ? nextState.chapters.find((item: WritingStateChapter) => item.chapter_number === current.chapter_number) || current : nextState.latest_approved_chapter || nextState.latest_chapter || null)
      try {
        setActivity(await dataApi.getWritingActivity(projectId))
      } catch {
        setActivity(null)
      }
    } catch (reason: any) { setError(reason?.response?.data?.detail || 'Writing state could not be loaded.') }
    finally { setLoading(false) }
  }, [projectId])

  useEffect(() => { void load() }, [load])

  const selectedDrafts = useMemo(() => drafts.filter((draft) => Number(draft.chapter_number) === Number(selected?.chapter_number)).sort((left, right) => Number(right.version_number || 0) - Number(left.version_number || 0)), [drafts, selected])
  const selectedDraft = selectedDrafts.find((draft) => draft.draft_id === selected?.draft_id) || selectedDrafts.find((draft) => draft.active) || selectedDrafts[0]

  const openContext = async (chapter: WritingStateChapter) => {
    setSelected(chapter); setContext(null); setComparison(null); setShowVersions(false); setEditing(false); setSelectedText('')
    try { setContext(await dataApi.getChapterContext(projectId, chapter.chapter_number)) } catch { setContext(null) }
  }

  const beginEdit = (chapter: WritingStateChapter) => {
    const source = drafts.find((item) => item.draft_id === chapter.draft_id) || drafts.find((item) => Number(item.chapter_number) === Number(chapter.chapter_number) && item.active)
    if (!source) return
    setSelected(chapter); setContext(null); setComparison(null); setShowVersions(false)
    setEditingText(String(source.generated_text || ''))
    setEditNotice('You are editing a copy. Saving creates a new version; the previous one stays in Versions.')
    setEditing(true)
  }

  const saveEdit = async () => {
    if (!selectedDraft?.draft_id || !editingText.trim() || actionBusy) return
    setActionBusy(true); setError('')
    try {
      await dataApi.editChapterContent(projectId, selectedDraft.draft_id, editingText, 'Author edited chapter prose')
      setEditing(false); setSelectedText(''); setEditNotice(`Chapter ${selected?.chapter_number} saved as a new reviewable version. The previous version remains available.`)
      await load()
    } catch (reason: any) {
      setError(reason?.response?.data?.detail || 'The edit could not be saved. Your previous version remains safe.')
    } finally { setActionBusy(false) }
  }

  const captureSelection = (event?: SyntheticEvent<HTMLElement>) => {
    const target = event?.currentTarget as HTMLTextAreaElement | null
    const start = target?.selectionStart ?? -1
    const end = target?.selectionEnd ?? -1
    const selection = start >= 0 && end > start
      ? String(target?.value || '').slice(start, end).trim()
      : window.getSelection()?.toString().trim() || ''
    setSelectedText(selection.length >= 6 ? selection : '')
  }

  const requestFocusedEdit = async (instruction: string) => {
    if (!selectedDraft?.draft_id || !selectedText || selectionBusy) return
    setSelectionBusy(true); setError('')
    try {
      await dataApi.createSelectionRevision(projectId, selectedDraft.draft_id, selectedText, instruction)
      setEditNotice('A suggested edit is ready under Review → Suggested edits. Your chapter has not changed.')
      onNavigate?.('editorial')
    } catch (reason: any) {
      setError(reason?.response?.data?.detail || 'The focused suggestion could not be created. Your chapter remains safe.')
    } finally { setSelectionBusy(false) }
  }

  const compareVersions = async (chapter: WritingStateChapter) => {
    setSelected(chapter); setComparison(null)
    try { setComparison(await dataApi.compareChapterVersions(projectId, chapter.chapter_number)) } catch { setComparison({ chapter_number: chapter.chapter_number, available: false, message: 'Version comparison is temporarily unavailable.' }) }
  }

  const approveSelected = async (chapter: WritingStateChapter) => {
    const draft = drafts.find((item) => item.draft_id === chapter.draft_id) || drafts.find((item) => Number(item.chapter_number) === Number(chapter.chapter_number) && item.active)
    if (!draft?.draft_id || actionBusy) return
    setActionBusy(true); setError('')
    try {
      if (draft.status === 'draft') await dataApi.updateDraftStatus(projectId, 'chapter', draft.draft_id, 'review', 'Submitted for author review from Writing')
      await dataApi.updateDraftStatus(projectId, 'chapter', draft.draft_id, 'approved', 'Approved from Writing')
      await load()
    } catch (reason: any) {
      setError(reason?.response?.data?.detail || 'Approval did not complete. The existing draft remains safe.')
    } finally { setActionBusy(false) }
  }

  if (loading) return <section className="flex min-h-40 items-center justify-center rounded-xl border bg-muted/20"><Loader2 className="mr-2 h-5 w-5 animate-spin" />Loading your chapters…</section>
  if (error) return <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm"><p className="font-semibold">Writing state could not be refreshed.</p><p className="mt-1">{error}</p><Button className="mt-3" size="sm" variant="outline" onClick={() => void load()}><RefreshCw className="mr-1.5 h-4 w-4" />Retry</Button></section>

  return <div className="space-y-5" data-testid="writing-workspace">
    {selectedText && selected && selectedDraft ? <section className="rounded-xl border border-violet-200 bg-violet-50 p-4 text-sm"><p className="font-semibold text-violet-950">Focused AI edit</p><p className="mt-1 text-violet-900">The AI suggests a new version of the selected passage. You compare it and decide under Review → Suggested edits.</p><div className="mt-2 flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={selectionBusy} onClick={() => void requestFocusedEdit('Rewrite this passage with more natural sentence rhythm while preserving meaning and voice.')}>Rewrite naturally</Button><Button size="sm" variant="outline" disabled={selectionBusy} onClick={() => void requestFocusedEdit('Shorten this passage without losing the emotional beat or important information.')}>Shorten</Button><Button size="sm" variant="outline" disabled={selectionBusy} onClick={() => void requestFocusedEdit('Improve the dialogue and subtext in this passage without changing what the characters know.')}>Improve dialogue</Button><Button size="sm" variant="outline" disabled={selectionBusy} onClick={() => { const instruction = window.prompt('How should this selected passage change?')?.trim(); if (instruction) void requestFocusedEdit(instruction) }}>{selectionBusy ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}Custom instruction</Button></div></section> : null}
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm" data-testid="writing-summary">
      <span><strong className="font-semibold">{state?.chapter_count || 0}</strong> <span className="text-muted-foreground">chapter{state?.chapter_count === 1 ? '' : 's'}</span></span>
      <span><strong className="font-semibold">{state?.chapters.filter((item) => item.status === 'approved').length || 0}</strong> <span className="text-muted-foreground">approved</span></span>
      <span><strong className="font-semibold">{state?.pending.review || 0}</strong> <span className="text-muted-foreground">to review</span></span>
      <span><strong className="font-semibold">{(state?.chapters || []).reduce((sum, item) => sum + (Number(item.word_count) || 0), 0).toLocaleString()}</strong> <span className="text-muted-foreground">words</span></span>
      <Button size="sm" variant="ghost" className="ml-auto" onClick={() => void load()}><RefreshCw className="mr-1.5 h-3.5 w-3.5" />Refresh</Button>
    </div>

    <section className="rounded-xl border bg-card p-5 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="text-lg font-semibold">Your chapters</h3><p className="text-sm text-muted-foreground">Open a chapter to read it, edit it or approve it. Every edit is saved as a new version.</p></div></div>
      {!state?.chapters.length ? <div className="mt-4 flex flex-col items-center rounded-xl border border-dashed bg-muted/30 px-6 py-10 text-center" data-testid="empty-state"><p className="font-semibold">No chapters yet</p><p className="mt-1 max-w-md text-sm text-muted-foreground">Describe what happens in Chapter 1 and the AI drafts it from your plan. You can edit every word.</p><Button className="mt-4" onClick={() => onNavigate?.('write-next')}><PenLine className="mr-2 h-4 w-4" />Write Chapter 1</Button></div> : <div className="mt-4 space-y-2">{state.chapters.map((chapter) => <article key={`${chapter.chapter_number}-${chapter.draft_id}`} className={`rounded-lg border bg-background p-4 ${selected?.chapter_number === chapter.chapter_number ? 'border-primary ring-1 ring-primary/20' : ''}`}>
        <div className="flex flex-wrap items-start justify-between gap-3"><button type="button" className="min-w-0 text-left" onClick={() => void openContext(chapter)}><p className="font-semibold">Chapter {chapter.chapter_number}{chapter.title && chapter.title !== `Chapter ${chapter.chapter_number}` ? ` · ${chapter.title}` : ''}</p><p className="mt-1 text-xs text-muted-foreground">{chapter.word_count.toLocaleString()} words · Version {chapter.active_version}{chapter.updated_at ? ` · Updated ${new Date(chapter.updated_at).toLocaleDateString()}` : ''}</p></button><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(chapter.status)}`}>{statusLabel(chapter.status)}</span>{chapter.validation_result ? <span className="rounded-full bg-muted px-2 py-1 text-xs" title="Automatic consistency check against your story facts">{String(chapter.validation_result).toUpperCase() === 'PASS' ? 'Consistent' : `Check: ${String(chapter.validation_result).toLowerCase()}`}</span> : null}</div></div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">{chapter.extraction.status === 'candidate' && chapter.extraction.candidate_count ? <span className="inline-flex items-center gap-1"><Sparkles className="h-3 w-3" />{chapter.extraction.candidate_count} new fact{chapter.extraction.candidate_count === 1 ? '' : 's'} found</span> : null}<span className="inline-flex items-center gap-1"><GitBranch className="h-3 w-3" />{chapter.version_count} version{chapter.version_count === 1 ? '' : 's'}</span></div>
        <div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void openContext(chapter)}><Eye className="mr-1.5 h-3.5 w-3.5" />Read</Button><Button size="sm" variant="outline" onClick={() => beginEdit(chapter)}><PenLine className="mr-1.5 h-3.5 w-3.5" />Edit</Button>{chapter.status !== 'approved' ? <Button size="sm" onClick={() => void approveSelected(chapter)} disabled={actionBusy}><CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />Approve Chapter {chapter.chapter_number}</Button> : null}<Button size="sm" variant="ghost" onClick={() => { setSelected(chapter); setShowVersions(!showVersions); setComparison(null) }}><GitBranch className="mr-1.5 h-3.5 w-3.5" />Versions</Button>{chapter.version_count > 1 ? <Button size="sm" variant="ghost" onClick={() => void compareVersions(chapter)}><GitBranch className="mr-1.5 h-3.5 w-3.5" />Compare versions</Button> : null}</div>
        {showVersions && selected?.chapter_number === chapter.chapter_number ? <div className="mt-3 rounded-md bg-muted/40 p-3 text-xs">{selectedDrafts.map((version) => <div key={version.draft_id} className="flex flex-wrap justify-between gap-2 border-b py-2 last:border-0"><span>Version {version.version_number} · {statusLabel(version.status)} · {Number(version.word_count || 0).toLocaleString()} words</span>{version.active ? <strong>Current</strong> : <span>Earlier</span>}</div>)}</div> : null}
      </article>)}</div>}
    </section>

    {selected && selectedDraft ? <section className="rounded-xl border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">Chapter {selected.chapter_number}</h3><p className="text-sm text-muted-foreground">{statusLabel(selected.status)} · Version {selected.active_version}</p></div><span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Clock3 className="h-3.5 w-3.5" />{selectedDraft.approved_at ? `Approved ${new Date(selectedDraft.approved_at).toLocaleString()}` : 'Not approved'}</span></div>{editNotice ? <p className="mt-3 rounded-md bg-sky-50 p-3 text-sm text-sky-900">{editNotice}</p> : null}{editing ? <><textarea data-testid="chapter-prose-editor" aria-label={`Edit Chapter ${selected.chapter_number}`} value={editingText} onChange={(event) => setEditingText(event.target.value)} onMouseUp={captureSelection} onKeyUp={captureSelection} className="mt-4 min-h-[60vh] w-full rounded-lg border bg-background p-5 font-serif text-[1.04rem] leading-7 focus:outline-none focus:ring-2 focus:ring-primary/30" /><div className="mt-3 flex flex-wrap items-center gap-2"><Button onClick={() => void saveEdit()} disabled={actionBusy || !editingText.trim()}>{actionBusy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-1.5 h-4 w-4" />}Save as new version</Button><Button variant="outline" onClick={() => { setEditing(false); setSelectedText('') }}>Cancel</Button>{selectedText ? <span className="text-xs text-muted-foreground">Selected {selectedText.split(/\s+/).length} words · Choose an AI edit above to get a suggestion.</span> : <span className="text-xs text-muted-foreground">Select text for focused AI help, or edit normally. Nothing replaces prose without your approval.</span>}</div></> : <div data-testid="chapter-prose-reader" onMouseUp={captureSelection} className="mt-4 max-h-[60vh] overflow-y-auto whitespace-pre-wrap rounded-lg bg-muted/30 p-5 font-serif text-[1.04rem] leading-7">{selectedDraft.generated_text || 'This version has no reader-facing prose.'}</div>}{selectedText && !editing ? <p className="mt-3 rounded-md border border-violet-200 bg-violet-50 p-3 text-sm text-violet-900">Choose an AI edit above. The AI writes a suggestion; your chapter only changes if you accept it.</p> : null}</section> : null}

    {activity && (activity.running.length || activity.attention.length) ? <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-4" aria-live="polite"><div className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 text-amber-700" /><div><h3 className="font-semibold text-amber-950">Story activity</h3><div className="mt-2 space-y-2 text-sm">{[...activity.running, ...activity.attention].slice(0, 5).map((item, index) => <div key={`${item.kind}-${index}`}><p className="font-medium">{item.status === 'failed' || item.status === 'interrupted' ? 'Needs attention' : item.status === 'waiting' ? 'Waiting for your decision' : 'Still working'} · {item.label}</p><p className="text-amber-900/80">{item.summary}{item.safe_prose ? ' Your approved prose is safe.' : ''}</p>{item.retryable ? <p className="text-xs font-medium">You can retry this enrichment from its owning workspace.</p> : null}</div>)}</div></div></div></section> : null}
    {selected && context ? <section className="rounded-xl border border-sky-200 bg-sky-50/50 p-4"><div className="flex items-start gap-2"><Sparkles className="mt-0.5 h-4 w-4 text-sky-700" /><div><h3 className="font-semibold text-sky-950">What the AI learned from Chapter {selected.chapter_number}</h3><p className="mt-1 text-sm text-sky-900/80">Details picked out of this chapter. They are suggestions until you confirm them under Review.</p></div></div><div className="mt-4 grid gap-3 md:grid-cols-2">{Object.entries(context.learned_from_chapter.groups).map(([kind, values]) => <div key={kind} className="rounded-lg border bg-background p-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{kind.replaceAll('_', ' ')}</p><ul className="mt-2 space-y-1 text-sm">{values.slice(0, 6).map((value, index) => <li key={index}>{value}</li>)}</ul><p className="mt-2 text-xs text-muted-foreground">Suggestion · from this chapter</p></div>)}</div>{context.carried_into_generation.length ? <div className="mt-4 rounded-lg border bg-background p-3"><p className="text-sm font-semibold">Used when writing later chapters</p><ul className="mt-2 space-y-2 text-sm">{context.carried_into_generation.slice(0, 8).map((item, index) => <li key={index}><span className="font-medium">{item.source_type || 'Story record'}:</span> {item.content}</li>)}</ul></div> : null}</section> : null}
    {selected && context?.approval_change ? <section className="rounded-xl border border-violet-200 bg-violet-50/50 p-4"><h3 className="font-semibold text-violet-950">What changed after approval</h3><p className="mt-1 text-sm text-violet-900/80">A compact view of what was already known, what this chapter added, and what can influence the next chapter.</p><div className="mt-3 grid gap-3 md:grid-cols-2"><div className="rounded-lg border bg-background p-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">New from Chapter {selected.chapter_number}</p><p className="mt-1 text-sm">{Object.values(context.approval_change.new_information.candidate_groups).flat().slice(0, 6).join(' · ') || 'No new candidate details recorded.'}</p><p className="mt-2 text-xs text-muted-foreground">{context.approval_change.new_information.candidate_status === 'candidate' ? 'Suggestion · not confirmed yet' : context.approval_change.new_information.candidate_status}</p></div><div className="rounded-lg border bg-background p-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Before approval</p><p className="mt-1 text-sm">{context.approval_change.before.summary || Object.values(context.approval_change.before.candidate_groups).flat().slice(0, 6).join(' · ') || 'No earlier derived context was available.'}</p></div><div className="rounded-lg border bg-background p-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Confirmed facts and open threads</p><p className="mt-1 text-sm">Confirmed facts changed: {context.approval_change.canon_changed ? 'Yes' : 'No'} · {context.approval_change.open_threads.slice(0, 4).join(' · ') || 'No new open thread recorded.'}</p></div><div className="rounded-lg border bg-background p-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Next chapter influence</p><p className="mt-1 text-sm">{context.approval_change.next_chapter_influence.slice(0, 4).map((item) => item.content).join(' · ')}</p></div></div></section> : null}
    {comparison ? <section className="rounded-xl border border-violet-200 bg-violet-50/50 p-4"><h3 className="font-semibold text-violet-950">Version comparison · Chapter {comparison.chapter_number}</h3><p className="mt-1 text-sm text-violet-900/80">{comparison.available ? `Version ${comparison.left?.version} compared with Version ${comparison.right?.version}. The current version is unchanged.` : comparison.message}</p>{comparison.available ? <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-background p-3 text-xs whitespace-pre-wrap">{comparison.diff || 'No textual differences found.'}</pre> : null}</section> : null}
  </div>
}
