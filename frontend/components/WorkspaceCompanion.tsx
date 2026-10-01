"use client"

import { useEffect, useState } from 'react'
import { ArrowRight, Bot, Check, ChevronUp, Loader2, MessageCircle, Moon, PanelLeft, PanelRight, PartyPopper, Sparkles, Waves, X } from 'lucide-react'

import { dataApi } from '@/lib/api'
import type { WorkspaceCompanionFeed } from '@/types'


type CompanionProps = {
  projectId: string
  activeSurface?: string
  refreshKey?: string
  onNavigate: (section: string) => void
  onAsk: () => void
  onOpenChange?: (open: boolean, dock: 'left' | 'right') => void
  constrained?: boolean
}

export default function WorkspaceCompanion({ projectId, activeSurface = '', refreshKey = '', onNavigate, onAsk, onOpenChange, constrained = false }: CompanionProps) {
  const [feed, setFeed] = useState<WorkspaceCompanionFeed | null>(null)
  const [open, setOpen] = useState(false)
  const [dock, setDock] = useState<'left' | 'right'>('right')
  const [motion, setMotion] = useState(true)

  useEffect(() => {
    const saved = window.localStorage.getItem(`novelforge:companion:${projectId}`)
    if (!saved) return
    try {
      const preferences = JSON.parse(saved) as { dock?: 'left' | 'right'; motion?: boolean }
      if (preferences.dock === 'left' || preferences.dock === 'right') setDock(preferences.dock)
      if (typeof preferences.motion === 'boolean') setMotion(preferences.motion)
    } catch {
      // Ignore stale local preferences and retain accessible defaults.
    }
  }, [projectId])

  useEffect(() => {
    window.localStorage.setItem(
      `novelforge:companion:${projectId}`,
      JSON.stringify({ dock, motion }),
    )
    onOpenChange?.(open, dock)
  }, [dock, motion, onOpenChange, open, projectId])

  useEffect(() => {
    let active = true
    const refresh = () => dataApi.getWorkspaceCompanion(projectId, activeSurface).then((value) => {
      if (!active) return
      setFeed(value)
    }).catch(() => undefined)
    void refresh()
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refresh()
    }, 30_000)
    return () => { active = false; window.clearInterval(timer) }
  }, [activeSurface, projectId, refreshKey])

  useEffect(() => {
    if (!open || !feed?.messages.some((message) => !message.read)) return
    setFeed((current) => current ? {
      ...current,
      messages: current.messages.map((message) => ({ ...message, read: true })),
    } : current)
    void (dataApi.markWorkspaceCompanionRead?.(projectId) ?? Promise.resolve()).catch(() => undefined)
  }, [feed, open, projectId])

  const setCompanionOpen = (next: boolean) => {
    setOpen(next)
  }

  const dismiss = async (messageId: string) => {
    await dataApi.updateWorkspaceCompanionMessage(projectId, messageId, { dismissed: true })
    setFeed((current) => current ? { ...current, messages: current.messages.filter((item) => item.message_id !== messageId) } : current)
  }
  const complete = async (messageId: string) => {
    await dataApi.updateWorkspaceCompanionMessage(projectId, messageId, { completed: true })
    setFeed((current) => current ? { ...current, messages: current.messages.filter((item) => item.message_id !== messageId) } : current)
  }
  const snooze = async (messageId: string) => {
    await dataApi.updateWorkspaceCompanionMessage(projectId, messageId, { snooze_hours: 24 })
    setFeed((current) => current ? { ...current, messages: current.messages.filter((item) => item.message_id !== messageId) } : current)
  }

  const headline = feed?.messages[0]
  const state = feed?.state || (headline ? 'notifying' : 'idle')
  const visualState = !feed ? 'thinking' : state === 'idle' && !headline ? 'sleeping' : state
  const stateLabel = visualState === 'working' ? 'Reviewing your project' : visualState === 'thinking' ? 'Getting oriented' : visualState === 'celebrating' ? 'Milestone reached' : visualState === 'sleeping' ? 'Quietly standing by' : 'Ready to help'
  const unreadCount = feed?.messages.filter((message) => !message.read).length || 0

  return (
    <aside className={`fixed bottom-4 z-30 ${constrained ? 'w-[min(21rem,calc(100vw-2rem))]' : 'w-[min(25rem,calc(100vw-2rem))]'} ${dock === 'right' ? 'right-4' : 'left-20'}`} data-testid="workspace-companion" data-dock={dock} data-constrained={constrained || undefined}>
      <span className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {feed ? `${stateLabel}. ${unreadCount} new companion messages.` : 'Workspace Companion is getting oriented.'}
      </span>
      {open ? (
        <div className={`companion-panel relative mb-3 max-h-[min(36rem,70vh)] overflow-hidden rounded-2xl border border-slate-200/80 bg-card/95 shadow-2xl shadow-slate-950/15 backdrop-blur-xl ${motion ? 'companion-panel-enter' : ''}`}>
          <div className="h-1 bg-gradient-to-r from-violet-500 via-sky-400 to-emerald-400" />
          <div className="flex items-center gap-3 border-b bg-gradient-to-br from-violet-50/90 via-background to-sky-50/70 p-4">
            <CompanionAvatar state={visualState} compact motion={motion} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2"><strong>Workspace Companion</strong>{unreadCount ? <span className="rounded-full bg-violet-600 px-1.5 py-0.5 text-[10px] font-bold text-white" aria-label={`${unreadCount} new companion messages`}>{unreadCount}</span> : null}</div>
              <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground"><span className={`h-1.5 w-1.5 rounded-full ${visualState === 'working' || visualState === 'thinking' ? 'bg-sky-500' : visualState === 'celebrating' ? 'bg-emerald-500' : 'bg-slate-400'}`} />{stateLabel}</p>
            </div>
            <button className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500" aria-label={`Dock companion on the ${dock === 'right' ? 'left' : 'right'}`} title={`Dock on ${dock === 'right' ? 'left' : 'right'}`} onClick={() => setDock((value) => value === 'right' ? 'left' : 'right')}>{dock === 'right' ? <PanelLeft className="h-4 w-4" /> : <PanelRight className="h-4 w-4" />}</button>
            <button className={`rounded-full p-2 transition-colors hover:bg-black/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${motion ? 'text-violet-600' : 'text-muted-foreground'}`} aria-label={`${motion ? 'Disable' : 'Enable'} companion animations`} title={`${motion ? 'Disable' : 'Enable'} animations`} onClick={() => setMotion((value) => !value)}><Waves className="h-4 w-4" /></button>
            <button className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500" aria-label="Collapse companion" onClick={() => setCompanionOpen(false)}><X className="h-4 w-4" /></button>
          </div>

          <div className="max-h-[calc(min(36rem,70vh)-5rem)] overflow-y-auto p-3">
            {feed?.current_milestone ? <div className="mb-3 flex items-center justify-between rounded-lg border border-violet-100 bg-violet-50/60 px-3 py-2 text-xs"><span className="text-violet-700">Current milestone</span><strong className="text-violet-950">{feed.current_milestone}</strong></div> : null}
            {feed?.recap ? <p className="mb-3 rounded-lg border border-sky-100 bg-sky-50/70 p-3 text-sm leading-relaxed text-sky-950"><Sparkles className="mr-2 inline h-4 w-4 text-sky-600" />{feed.recap}</p> : null}
            <div className="space-y-2.5">
              {(feed?.messages || []).slice(0, 8).map((message) => (
                <article key={message.message_id} className={`group rounded-xl border p-3 text-sm transition-colors ${message.kind === 'celebration' || message.kind === 'milestone' ? 'border-emerald-200 bg-emerald-50/50' : message.kind === 'attention' ? 'border-amber-200 bg-amber-50/50' : 'border-slate-200 bg-background hover:border-violet-200'}`}>
                  <div className="flex justify-between gap-2">
                    <div className="min-w-0"><span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{message.kind === 'attention' ? 'Needs attention' : message.kind === 'recommendation' ? 'Suggested next step' : message.kind}</span><strong className="leading-snug">{message.title}</strong></div>
                    <button className="h-fit rounded-full p-1 text-muted-foreground opacity-60 transition-opacity hover:bg-black/5 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500" aria-label={`Dismiss ${message.title}`} onClick={() => void dismiss(message.message_id)}><X className="h-3.5 w-3.5" /></button>
                  </div>
                  <p className="mt-1.5 leading-relaxed text-muted-foreground">{message.message}</p>
                  {message.explanation ? (
                    <p className="mt-2 rounded-lg bg-white/70 px-2.5 py-2 text-xs leading-relaxed text-slate-600">
                      <strong className="text-slate-800">Why this is next: </strong>{message.explanation}
                    </p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-semibold">
                    <button className="inline-flex items-center rounded-full bg-slate-950 px-3 py-1.5 text-white transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2" onClick={() => onNavigate(message.target)}>{message.action_label || 'Show me'} <ArrowRight className="ml-1 h-3 w-3" /></button>
                    {message.kind === 'recommendation' ? <button className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-emerald-800 hover:bg-emerald-100" onClick={() => void complete(message.message_id)}><Check className="mr-1 h-3 w-3" />Complete</button> : null}
                    <button className="rounded-full px-2 py-1.5 text-muted-foreground hover:bg-muted" onClick={() => void snooze(message.message_id)}>Tomorrow</button>
                  </div>
                </article>
              ))}
              {!feed?.messages.length ? <div className="rounded-xl border border-dashed bg-slate-50/60 p-5 text-center text-sm text-muted-foreground"><Moon className="mx-auto mb-2 h-5 w-5 text-slate-400" /><strong className="block text-foreground">You’re all caught up</strong><span className="mt-1 block">I’ll stay nearby and let you focus.</span></div> : null}
            </div>
            <button className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-violet-200 bg-violet-50/70 px-3 py-2.5 text-sm font-semibold text-violet-900 transition-colors hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500" onClick={onAsk}><MessageCircle className="h-4 w-4" /> Ask how this page works</button>
          </div>
        </div>
      ) : null}

      <button type="button" onClick={() => setCompanionOpen(!open)} className={`companion-launcher flex max-w-full items-center gap-2.5 rounded-full border border-slate-200/90 bg-card/95 py-2 pl-2 pr-3 text-left shadow-xl shadow-slate-950/10 backdrop-blur transition-all hover:-translate-y-0.5 hover:shadow-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 ${dock === 'right' ? 'ml-auto' : 'mr-auto'}`} aria-expanded={open} aria-label={headline ? `${headline.title}. Open Workspace Companion` : 'Open Workspace Companion'}>
        <CompanionAvatar state={visualState} motion={motion} />
        <span className="min-w-0 flex-1"><span className="flex items-center gap-2"><span className="block truncate text-sm font-semibold">{headline?.title || 'Workspace Companion'}</span>{unreadCount ? <span className="companion-notify h-2 w-2 shrink-0 rounded-full bg-violet-500" /> : null}</span><span className="block truncate text-xs text-muted-foreground">{headline?.message || stateLabel}</span></span>
        <ChevronUp className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
    </aside>
  )
}


function CompanionAvatar({ state, compact = false, motion = true }: { state: string; compact?: boolean; motion?: boolean }) {
  const Icon = state === 'working' || state === 'thinking' ? Loader2 : state === 'celebrating' ? PartyPopper : state === 'sleeping' ? Moon : Bot
  const animation = !motion ? '' : state === 'working' ? 'companion-working' : state === 'thinking' ? 'companion-thinking' : state === 'celebrating' ? 'companion-celebrating' : state === 'sleeping' ? 'companion-sleeping' : 'companion-floating'
  return (
    <span className={`companion-avatar relative flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-600 via-indigo-500 to-sky-400 text-white shadow-md shadow-violet-500/20 ${compact ? 'h-10 w-10' : 'h-11 w-11'} ${animation}`} data-companion-state={state} aria-hidden="true">
      <span className="absolute inset-[3px] rounded-full border border-white/35 bg-slate-950/15" />
      <Icon className={`relative h-5 w-5 ${motion && (state === 'working' || state === 'thinking') ? 'companion-icon-spin' : ''}`} />
      {state === 'notifying' ? <span className={`${motion ? 'companion-notify' : ''} absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-white bg-amber-400`} /> : null}
      {motion && state === 'celebrating' ? <><span className="companion-spark companion-spark-one" /><span className="companion-spark companion-spark-two" /><span className="companion-spark companion-spark-three" /></> : null}
    </span>
  )
}
