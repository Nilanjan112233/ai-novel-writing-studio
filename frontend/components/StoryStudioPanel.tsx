"use client"

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Check, ChevronDown, ChevronRight, Loader2, MessageSquare, PenLine, RefreshCw, Send, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { dataApi, settingsApi } from '@/lib/api'
import type { DiscoveryExtraction, StoryStudioJob, StoryStudioResult, WritingState } from '@/types'
import KnowledgeSuggestionsPanel from '@/components/KnowledgeSuggestionsPanel'

type Props = { projectId: string; onNavigate?: (target: string) => void; onChanged?: () => void }

export default function StoryStudioPanel({ projectId, onNavigate, onChanged }: Props) {
  const [tab, setTab] = useState<'talk' | 'write'>('talk')
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<StoryStudioResult | null>(null)
  const [jobs, setJobs] = useState<StoryStudioJob[]>([])
  const [expanded, setExpanded] = useState(false)
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null)
  const [showOlder, setShowOlder] = useState(false)
  const [clarificationJobId, setClarificationJobId] = useState<string | null>(null)
  const [refreshingJobId, setRefreshingJobId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [instruction, setInstruction] = useState('')
  const [minimum, setMinimum] = useState('1800')
  const [target, setTarget] = useState('2500')
  const [maximum, setMaximum] = useState('3200')
  const [draft, setDraft] = useState<any | null>(null)
  const [extractions, setExtractions] = useState<DiscoveryExtraction[]>([])
  const [notice, setNotice] = useState('')
  const [writingState, setWritingState] = useState<WritingState | null>(null)
  const [knowledgeCandidates, setKnowledgeCandidates] = useState<any[]>([])
  const [modelPreference, setModelPreference] = useState('auto')
  const [modelOptions, setModelOptions] = useState<Array<{ provider: string; model_id: string; display_name?: string; free_tier?: boolean }>>([])

  const applyJobs = (values: StoryStudioJob[]) => {
    setJobs(values)
    setResult((current) => {
      if (!current?.job_id) return current
      const refreshed = values.find((job) => (job.job_id || job.id) === current.job_id)
      return refreshed?.result || current
    })
  }
  const refreshJobs = async () => {
    try { applyJobs(await dataApi.getStoryStudioJobs(projectId)) } catch { /* the panel remains useful if progress is temporarily unavailable */ }
  }
  useEffect(() => {
    const refresh = () => { void dataApi.getStoryStudioJobs(projectId).then(applyJobs).catch(() => undefined) }
    refresh()
    const timer = window.setInterval(refresh, 3000)
    return () => window.clearInterval(timer)
  }, [projectId])
  useEffect(() => {
    dataApi.getWritingState(projectId).then((value) => setWritingState(value as WritingState)).catch(() => setWritingState(null))
    dataApi.getStoryKnowledgeCandidates(projectId).then((value) => setKnowledgeCandidates(Array.isArray(value) ? value : [])).catch(() => setKnowledgeCandidates([]))
    settingsApi.getModels(undefined, false, true).then((value) => {
      const options = (Array.isArray(value) ? value : []).filter((item: any) => item?.provider && item.provider !== 'mock' && item.model_id)
      setModelOptions(options)
    }).catch(() => setModelOptions([]))
  }, [projectId])

  const refreshKnowledgeCandidates = async () => {
    try {
      const value = await dataApi.getStoryKnowledgeCandidates(projectId)
      setKnowledgeCandidates(Array.isArray(value) ? value : [])
    } catch {
      setKnowledgeCandidates([])
    }
  }

  const activeJob = useMemo(() => {
    const newest = jobs[jobs.length - 1]
    return newest && (newest.status === 'running' || newest.status === 'queued' || newest.status === 'waiting') ? newest : undefined
  }, [jobs])
  const completedJobs = useMemo(() => jobs.filter((job) => job.status === 'completed' && job.result), [jobs])
  const recentJobs = useMemo(() => completedJobs.slice(-5), [completedJobs])
  const olderJobs = useMemo(() => completedJobs.slice(0, -5), [completedJobs])
  const evidenceItems = (evidence: StoryStudioResult['evidence']) => {
    if (!evidence) return []
    const cleanDetail = (value: unknown) => String(value ?? '').replace(/\b[0-9a-f]{8}-[0-9a-f-]{27,}\b/gi, 'the referenced story record').replace(/\b[0-9a-f]{24,}\b/gi, 'the referenced story record')
    if (Array.isArray(evidence)) return evidence.map((item) => ({ label: item.label || item.source || 'Story source', detail: cleanDetail(item.detail || 'Retrieved for this answer.') }))
    return Object.entries(evidence).flatMap(([key, value]) => {
      if (['authority_changed', 'finding_ids', 'node_ids', 'analysis_id', 'candidate_ids'].includes(key)) return []
      const label = key.replaceAll('_', ' ')
      if (Array.isArray(value)) return value.slice(0, 8).map((item) => ({ label: key === 'chapters' ? 'Story source' : key.includes('timeline') ? 'Story timeline' : label, detail: key === 'chapters' ? `Chapter ${item}` : key.includes('timeline') && typeof item === 'string' && /^[0-9a-f-]{24,}$/i.test(item) ? 'A saved timeline event from the current story.' : cleanDetail(typeof item === 'string' ? item : JSON.stringify(item)) }))
      if (value && typeof value === 'object') return [{ label, detail: Object.entries(value as Record<string, unknown>).slice(0, 5).map(([child, childValue]) => `${child.replaceAll('_', ' ')}: ${cleanDetail(typeof childValue === 'string' ? childValue : JSON.stringify(childValue))}`).join(' · ') }]
      return value ? [{ label, detail: cleanDetail(value) }] : []
    })
  }
  const safeAnswer = (answer: string | undefined) => String(answer || '').replace(/\s*\(IDs?[^)]*\)/gi, '').replace(/`[a-f0-9]{6,}`/gi, 'the referenced story record').replace(/\b[0-9a-f]{8}-[0-9a-f-]{27,}\b/gi, 'the referenced story record').replace(/\b[0-9a-f]{24,}\b/gi, 'the referenced story record')
  const refreshHistorical = async (job: StoryStudioJob) => {
    if (!job.query || refreshingJobId) return
    setRefreshingJobId(job.job_id || job.id); setNotice('Refreshing this question against the current story state…')
    try { const value = await dataApi.storyStudio(projectId, { query: job.query, active_surface: 'story-studio', request_id: crypto.randomUUID(), model_preference: modelPreference, model_scope: 'message' }); setResult(value); await refreshJobs(); setNotice('Current answer refreshed. The earlier response remains in the conversation as history.') } catch (error: any) { setNotice(error?.response?.data?.detail || 'The question could not be refreshed.') }
    finally { setRefreshingJobId(null) }
  }
  const submitQuestion = async (event: FormEvent) => {
    event.preventDefault()
    if (!query.trim() || busy) return
    setBusy(true); setNotice(''); setResult(null)
    try {
      const value = await dataApi.storyStudio(projectId, { query: query.trim(), active_surface: 'story-studio', target: clarificationJobId ? { reply_to_job_id: clarificationJobId } : undefined, model_preference: modelPreference, model_scope: 'message' })
      setResult(value); setQuery(''); setClarificationJobId(value?.clarification?.status === 'waiting' ? (value.job_id || null) : null); await refreshJobs(); await refreshKnowledgeCandidates(); onChanged?.()
    } catch (error: any) {
      setNotice(error?.response?.data?.detail || 'NovelForge could not finish this request. Your story data was not changed.')
    } finally { setBusy(false) }
  }
  const polishChapterFromChat = async (chapterNumber: number) => {
    if (busy) return
    setBusy(true); setNotice('Preparing a protected prose-polish suggestion. The current chapter will not be replaced.')
    try {
      const value = await dataApi.storyStudio(projectId, { query: `Make Chapter ${chapterNumber} sound more natural and human-written. Reduce repetitive rhythm, generic description, over-explained emotion, and formulaic transitions while preserving voice, POV, meaning, continuity, and the ending.`, active_surface: 'story-studio', request_id: crypto.randomUUID() })
      setResult(value); await refreshJobs(); setNotice('A protected prose-polish suggestion is ready to review in Editorial.')
    } catch (error: any) {
      setNotice(error?.response?.data?.detail || 'The prose-polish suggestion could not be created. The chapter remains safe.')
    } finally { setBusy(false) }
  }
  const generate = async (event: FormEvent) => {
    event.preventDefault()
    if (!instruction.trim() || busy) return
    setBusy(true); setNotice('Generating a reviewable draft. Nothing becomes approved automatically.')
    try {
      const value = await dataApi.generateDiscoveryWriting(projectId, {
        instruction: instruction.trim(), minimum: Number(minimum), target: Number(target), maximum: Number(maximum),
      })
      const reviewDraft = value?.draft || value
      setDraft(reviewDraft); setNotice(`Draft ready for review: ${Number(reviewDraft.word_count || 0).toLocaleString()} words.`)
    } catch (error: any) {
      setNotice(error?.response?.data?.detail || 'The draft could not be generated. No approved prose was changed.')
    } finally { setBusy(false) }
  }
  const approve = async () => {
    if (!draft?.draft_id) return
    setBusy(true)
    try {
      if (draft.status === 'draft') {
        await dataApi.updateDraftStatus(projectId, 'chapter', draft.draft_id, 'review', 'Submitted for author review')
        setDraft({ ...draft, status: 'review' })
        setNotice('Draft submitted for review. Read or edit it, then approve the prose when it is ready.')
        return
      }
      await dataApi.updateDraftStatus(projectId, 'chapter', draft.draft_id, 'approved', 'Approved from Discovery Writing')
      const values = await dataApi.getDiscoveryExtractions(projectId)
      setDraft({ ...draft, status: 'approved' }); setExtractions(Array.isArray(values) ? values : [values])
      setNotice('Approved prose is now part of the manuscript lineage. Extracted knowledge remains candidate-only until governed.')
      try { await refreshKnowledgeCandidates(); await onChanged?.() } catch {
        setNotice('Chapter approved. Story context refresh is still running; the approved prose is safe.')
      }
    } catch (error: any) { setNotice(error?.response?.data?.detail || 'Approval did not complete. The existing draft remains safe.') }
    finally { setBusy(false) }
  }

  const approveChatDraft = async () => {
    const chatDraft = result?.draft
    if (!chatDraft?.draft_id || busy) return
    setBusy(true)
    setNotice('Saving approval and updating the story context. Your draft remains safe while enrichment runs.')
    try {
      if (chatDraft.status === 'draft') {
        await dataApi.updateDraftStatus(projectId, 'chapter', chatDraft.draft_id, 'review', 'Submitted for author review from Story Studio')
      }
      await dataApi.updateDraftStatus(projectId, 'chapter', chatDraft.draft_id, 'approved', 'Approved from Story Studio')
      setResult((current) => current ? { ...current, draft: { ...current.draft, status: 'approved' } } : current)
      setNotice(`Chapter ${chatDraft.chapter_number || ''} approved. NovelForge is carrying its useful story details forward as governed suggestions.`)
      try { await refreshKnowledgeCandidates(); await onChanged?.() } catch {
        setNotice(`Chapter ${chatDraft.chapter_number || ''} approved. Story context refresh is still running; the approved prose is safe.`)
      }
    } catch (error: any) {
      setNotice(error?.response?.data?.detail || 'Approval did not complete. The existing draft remains safe.')
    } finally { setBusy(false) }
  }

  const reextract = async () => {
    if (!draft?.draft_id || busy) return
    setBusy(true); setNotice('Refreshing the useful story details from this approved chapter.')
    try {
      const value = await dataApi.reextractDiscoveryKnowledge(projectId, draft.draft_id)
      setExtractions(Array.isArray(value) ? value : [value]); await refreshKnowledgeCandidates(); onChanged?.(); setNotice('Story details refreshed. They remain suggestions until you confirm them.')
    } catch (error: any) {
      setNotice(error?.response?.data?.detail || 'The story details could not be refreshed. The approved prose is safe.')
    } finally { setBusy(false) }
  }

  return <div className="space-y-5" data-testid="story-studio-panel">
    <div className="flex flex-wrap gap-2 border-b pb-3">
      <Button size="sm" variant={tab === 'talk' ? 'default' : 'outline'} onClick={() => setTab('talk')}><MessageSquare className="mr-2 h-4 w-4" />Talk about the story</Button>
      <Button size="sm" variant={tab === 'write' ? 'default' : 'outline'} onClick={() => setTab('write')}><PenLine className="mr-2 h-4 w-4" />Start writing now</Button>
    </div>
    {writingState?.latest_approved_chapter ? <div className="rounded-lg border border-sky-200 bg-sky-50/60 p-3 text-sm"><p className="font-semibold text-sky-950">Your story has {writingState.chapter_count} chapter{writingState.chapter_count === 1 ? '' : 's'}</p><p className="mt-1 text-sky-900/80">Chapter {writingState.latest_approved_chapter.chapter_number} is the latest approved chapter. <button type="button" className="font-semibold underline" onClick={() => onNavigate?.('writing')}>Open your chapter library</button></p></div> : null}
    {activeJob ? <div className="rounded-lg border bg-sky-50/60 p-3 text-sm" aria-live="polite"><div className="flex items-center gap-2 font-medium">{activeJob.status === 'waiting' ? <MessageSquare className="h-4 w-4" /> : <Loader2 className="h-4 w-4 animate-spin" />}{activeJob.result?.development ? (activeJob.status === 'waiting' ? 'NovelForge is waiting for your story decision' : 'Developing your story') : (activeJob.status === 'waiting' ? 'NovelForge is waiting for your answer' : 'NovelForge is working')}</div><p className="mt-1 text-muted-foreground">{activeJob.status === 'waiting' ? (activeJob.result?.development?.question || activeJob.result?.clarification?.question || 'One creative choice is needed before this can continue.') : (activeJob.progress?.message || activeJob.result?.development?.author_phase || 'Preparing the next story task.')}</p>{activeJob.progress && activeJob.progress.total > 0 ? <p className="mt-2 text-xs text-sky-900/70">{activeJob.progress.completed} of {activeJob.progress.total} story areas reviewed</p> : null}</div> : null}
    {tab === 'talk' ? <>
      <div className="rounded-lg border bg-muted/30 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium">What would you like to do?</p><p className="mt-1 text-sm text-muted-foreground">Ask a question, explore alternatives, find contradictions, or ask what to work on next. Read-only questions never change canon.</p></div><label className="min-w-[12rem] text-xs font-medium text-muted-foreground">Response model<select aria-label="Story Studio response model" className="mt-1 block w-full rounded-md border bg-background px-2 py-1.5 text-sm font-normal text-foreground" value={modelPreference} onChange={(event) => setModelPreference(event.target.value)} disabled={busy}><option value="auto">Auto (recommended)</option>{modelOptions.map((item) => <option key={`${item.provider}|${item.model_id}`} value={`${item.provider}|${item.model_id}`}>{item.display_name || item.model_id}{item.free_tier ? ' · free tier' : ''}</option>)}</select><span className="mt-1 block font-normal">Controls the main response only; extraction and validation stay task-routed.</span></label></div>
        <form className="mt-3 flex gap-2" onSubmit={submitQuestion}><Textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={3} className="min-w-0" placeholder={clarificationJobId ? 'Answer NovelForge’s question so it can continue…' : 'Develop my story, explain why a character behaves this way, or find contradictions…'} disabled={busy} /><Button type="submit" size="icon" aria-label={clarificationJobId ? 'Answer Story Studio' : 'Ask Story Studio'} disabled={busy || !query.trim()}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button></form>
      </div>
      {olderJobs.length ? <section className="rounded-lg border border-dashed p-3" data-testid="story-studio-older-history"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-sm font-medium">Earlier conversation</p><p className="text-xs text-muted-foreground">{olderJobs.length} older interaction{olderJobs.length === 1 ? '' : 's'} · kept in chronological order</p></div><Button size="sm" variant="outline" onClick={() => setShowOlder((value) => !value)}>{showOlder ? 'Hide older' : 'Show older'}</Button></div>{showOlder ? <div className="mt-3 space-y-3">{olderJobs.map((job) => { const jobKey = job.job_id || job.id; return <div key={jobKey} className="rounded-md bg-muted/30 p-3 text-sm"><p className="font-medium">{job.query}</p><p className="mt-1 text-xs text-muted-foreground">Historical response · {job.created_at ? new Date(job.created_at).toLocaleString() : 'saved conversation'}</p></div> })}</div> : null}</section> : null}
      <div className="space-y-4" data-testid="story-studio-recent-history"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recent conversation · newest five</p>{recentJobs.map((job) => { const jobKey = job.job_id || job.id; const details = evidenceItems(job.result?.evidence); const currentChapter = job.result?.draft ? writingState?.chapters?.find((item) => Number(item.chapter_number) === Number(job.result?.draft?.chapter_number)) : null; const currentDraftStatus = currentChapter?.status || job.result?.draft?.status; return <div key={jobKey} className="rounded-lg border p-4" data-testid="story-studio-message"><div className="flex items-start gap-2"><div className="mt-0.5 rounded-full bg-primary/10 p-1.5"><MessageSquare className="h-4 w-4 text-primary" /></div><div className="min-w-0 flex-1"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{job.result?.draft ? 'Historical work · saved chapter draft' : 'Historical conversation · saved response'}</p><p className="mt-1 font-medium">{job.query}</p><div className="mt-4 rounded-lg bg-muted/30 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">NovelForge response at that time</p><p className="mt-2 whitespace-pre-wrap break-words text-sm">{safeAnswer(job.result?.answer)}</p></div>{job.result?.draft ? <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-violet-200 bg-violet-50/70 p-3 text-sm"><div><p className="font-semibold text-violet-950">Chapter {job.result.draft.chapter_number || 'next'} draft saved in Writing</p><p className="text-violet-900/80">{Number(job.result.draft.word_count || 0).toLocaleString()} words · {currentDraftStatus === 'approved' ? 'Approved' : 'Still needs your review'}</p></div><Button size="sm" variant="outline" onClick={() => onNavigate?.('writing')}>Open Writing</Button></div> : null}{job.result?.author_decision_required ? <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm"><p className="font-semibold">Proposal not applied · your decision was required</p><p className="mt-1">Nothing authoritative changed.</p></div> : null}<div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void refreshHistorical(job)} disabled={refreshingJobId === jobKey}>{refreshingJobId === jobKey ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="mr-1.5 h-3.5 w-3.5" />}Refresh against current story</Button><Button size="sm" variant="ghost" onClick={() => setExpandedJobId(expandedJobId === jobKey ? null : jobKey)}>{expandedJobId === jobKey ? <ChevronDown className="mr-1 h-4 w-4" /> : <ChevronRight className="mr-1 h-4 w-4" />}Evidence and detail</Button></div>{expandedJobId === jobKey ? <div className="mt-3 space-y-2 border-t pt-3 text-sm">{details.length ? details.map((item, index) => <div key={index} className="rounded bg-muted p-2"><span className="font-medium capitalize">{item.label}:</span> {item.detail}</div>) : <p className="text-muted-foreground">No readable story evidence was returned.</p>}<p className="text-xs text-muted-foreground">This is conversation history, not canon. Current answers are checked against saved story state.</p></div> : null}</div></div></div>})}</div>
    {result ? <div className="rounded-lg border border-sky-200 bg-sky-50/40 p-4" data-testid="story-studio-result"><div className="flex items-start gap-2"><Sparkles className="mt-0.5 h-4 w-4 text-amber-600" /><div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-wide text-sky-800">Current grounded answer</p><p className="mt-1 font-medium">{result.understood_as || result.understood || 'Your story request'}</p><p className="mt-3 whitespace-pre-wrap break-words text-sm">{safeAnswer(result.answer)}</p>{result.generation_metadata?.model ? <p className="mt-2 text-xs text-sky-900/70">{String(result.generation_metadata.provider || '')} · {String(result.generation_metadata.model)}{result.generation_metadata.latency_ms ? ` · ${Number(result.generation_metadata.latency_ms).toLocaleString()} ms` : ''}</p> : null}</div></div>{result.development ? <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50/70 p-3 text-sm"><p className="font-semibold text-indigo-950">{result.development.status === 'completed' ? 'Story development finished' : result.development.status === 'waiting' ? 'A story decision is needed' : 'Developing your story'}</p><p className="mt-1 text-indigo-900/80">{result.development.author_phase || result.development.summary || 'Reviewing confirmed planning and expanding the story.'}</p>{result.development.question ? <p className="mt-2 rounded bg-background p-2 font-medium">{result.development.question}</p> : null}<p className="mt-2 text-xs text-indigo-900/70">Confirmed planning is used as input. Nothing is silently promoted to canon.</p></div> : null}{result.author_decision_required ? <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm"><p className="font-semibold">Proposal not applied · your decision is required</p><p className="mt-1">Nothing authoritative changed.</p></div> : null}{result.draft ? <div className="mt-4 rounded-xl border border-violet-200 bg-violet-50/70 p-4" data-testid="story-studio-chapter-result"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-violet-800">Reviewable chapter draft</p><h3 className="mt-1 text-lg font-semibold">Chapter {result.draft.chapter_number || 'next'}</h3><p className="mt-1 text-sm text-violet-900/80">{Number(result.draft.word_count || 0).toLocaleString()} words · {result.draft.status === 'approved' ? 'Approved' : 'Not approved'}{result.draft.range_compliant === false ? ' · outside the requested range' : ''}</p></div><span className="rounded-full bg-background px-2 py-1 text-xs font-semibold">{result.draft.validation_result || 'Continuity pending'}</span></div><div className="mt-3 max-h-[48vh] overflow-y-auto whitespace-pre-wrap rounded-lg bg-background p-4 font-serif text-[1.02rem] leading-7">{result.draft.generated_text || 'Open Writing to read this chapter.'}</div><div className="mt-4 flex flex-wrap gap-2"><Button size="sm" onClick={() => onNavigate?.('writing')}><PenLine className="mr-1.5 h-3.5 w-3.5" />Open chapter</Button><Button size="sm" variant="outline" onClick={() => onNavigate?.('editorial')}><Sparkles className="mr-1.5 h-3.5 w-3.5" />Edit or revise</Button>{result.draft.status !== 'approved' ? <Button size="sm" variant="outline" onClick={() => void approveChatDraft()} disabled={busy}><Check className="mr-1.5 h-3.5 w-3.5" />Approve prose</Button> : <Button size="sm" variant="outline" onClick={() => onNavigate?.('writing')}><PenLine className="mr-1.5 h-3.5 w-3.5" />Continue writing</Button>}</div><p className="mt-3 text-xs text-violet-900/70">This is a draft in the existing chapter lineage. Approval is your decision; extracted details remain governed suggestions.</p></div> : null}<div className="mt-4 flex flex-wrap items-center gap-2">{(result.navigation?.target || result.navigation_actions?.[0]?.target) ? <Button size="sm" variant="outline" onClick={() => onNavigate?.(result.navigation?.target || result.navigation_actions?.[0]?.target || 'dashboard')}>Open related workspace</Button> : null}<Button size="sm" variant="ghost" onClick={() => setExpanded(!expanded)}>{expanded ? <ChevronDown className="mr-1 h-4 w-4" /> : <ChevronRight className="mr-1 h-4 w-4" />}Evidence and detail</Button></div>{expanded ? <div className="mt-3 space-y-2 border-t pt-3 text-sm">{evidenceItems(result.evidence).length ? evidenceItems(result.evidence).map((item, index) => <div key={index} className="rounded bg-muted p-2"><span className="font-medium capitalize">{item.label}:</span> {item.detail}</div>) : <p className="text-muted-foreground">No additional evidence was returned.</p>}<p className="text-xs text-muted-foreground">This answer is grounded in current saved story state. Conversation text is not canon.</p></div> : null}</div> : null}
    </> : <>
      <form className="space-y-3 rounded-lg border p-4" onSubmit={generate}><div><p className="font-medium">Write a chapter or scene from an instruction</p><p className="mt-1 text-sm text-muted-foreground">Planning can emerge later. The draft is reviewable first and approval is explicit.</p></div><Textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} rows={5} placeholder="A rain-soaked courier reaches the city gate carrying a letter she cannot read..." disabled={busy} /><div className="grid gap-3 sm:grid-cols-3"><label className="text-sm">Minimum words<Input type="number" min="1" value={minimum} onChange={(event) => setMinimum(event.target.value)} /></label><label className="text-sm">Target words<Input type="number" min="1" value={target} onChange={(event) => setTarget(event.target.value)} /></label><label className="text-sm">Maximum words<Input type="number" min="1" value={maximum} onChange={(event) => setMaximum(event.target.value)} /></label></div><Button type="submit" disabled={busy || !instruction.trim()}>{busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PenLine className="mr-2 h-4 w-4" />}Generate reviewable draft</Button></form>
      {draft ? <div className="rounded-lg border p-4" data-testid="discovery-draft-review"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-medium">Review draft · Chapter {draft.chapter_number || 'next'}</p><p className="text-sm text-muted-foreground">{Number(draft.word_count || 0).toLocaleString()} words · {draft.validation_result || 'validation pending'}</p></div><Button onClick={approve} disabled={busy || draft.status === 'approved'}><Check className="mr-2 h-4 w-4" />{draft.status === 'approved' ? 'Approved' : 'Approve prose'}</Button></div><div className="mt-4 max-h-[55vh] overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/30 p-4 font-serif text-[1.02rem] leading-7">{draft.generated_text}</div></div> : null}
      {extractions.length ? <div className="rounded-lg border p-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium">Candidate knowledge from approved writing</p>{draft?.status === 'approved' ? <Button size="sm" variant="outline" onClick={() => void reextract()} disabled={busy}><RefreshCw className="mr-1.5 h-3.5 w-3.5" />Refresh details</Button> : null}</div><p className="mt-1 text-sm text-muted-foreground">These are reusable leads, not canon. Review them in the existing authority surfaces before promotion.</p><div className="mt-3 flex flex-wrap gap-2">{extractions[0].candidates?.slice(0, 18).map((candidate: any, index) => <span key={index} className="rounded bg-muted px-2 py-1 text-xs">{candidate.type || candidate.candidate_type}: {candidate.value || candidate.subject || candidate.description}</span>)}</div></div> : null}
    </>}
    <KnowledgeSuggestionsPanel
      projectId={projectId}
      candidates={knowledgeCandidates}
      types={['character', 'relationship', 'world_fact', 'mystery', 'plot_thread', 'timeline_event', 'artifact', 'knowledge_change', 'arc', 'author_intention', 'promise', 'foreshadowing', 'unresolved_element', 'pov_style']}
      onChanged={async () => { await refreshKnowledgeCandidates(); onChanged?.() }}
    />
    {result?.clarification ? <div className="rounded-lg border border-sky-300 bg-sky-50 p-3 text-sm" data-testid="story-studio-clarification"><p className="font-semibold">One creative choice needed</p><p className="mt-1">{result.clarification.question}</p><p className="mt-2 text-xs text-muted-foreground">Nothing has changed yet. Your next answer will continue this request.</p></div> : null}
    {notice ? <p className="text-sm text-muted-foreground" aria-live="polite">{notice}</p> : null}
  </div>
}
