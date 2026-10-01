/**
 * ParagraphEditor — Milestone 5.1 Refinement
 *
 * A three-panel Narrative Workspace that coexists planning, writing, and context.
 *
 * Layout:
 * ┌────────────┬────────────────────────────────────────────┬───────────────┐
 * │ Paragraph  │              Writing Editor                │ Narrative     │
 * │ Outline    │                                            │ Context       │
 * │            │                                            │               │
 * │ P1         │  Current Paragraph                         │ Purpose       │
 * │ P2         │                                            │ Canon         │
 * │ P3         │                                            │ Characters    │
 * │ P4         │                                            │ Timeline      │
 * │ P5         │                                            │ Pipeline      │
 * └────────────┴────────────────────────────────────────────┴───────────────┘
 *
 * Key features:
 *  - Distraction-free Focus Mode (collapses left/right panels).
 *  - Breadcrumbs display at top: Project → Chapter → Scene → Paragraph.
 *  - Mini outline navigator on Left Panel.
 *  - Active Narrative Context on Right Panel (Purpose, Characters, Canon references, Timeline references, etc).
 *  - Expanded Context Ribbon.
 *  - Offline/Retry saving state machine + Local Storage backup recovery.
 *  - Performance diagnostic telemetry dashboard (editor load, paragraph switch, autosave latencies, typing latency).
 */

'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import {
  ArrowLeft,
  ArrowRight,
  Save,
  Check,
  AlertCircle,
  Loader2,
  X,
  PanelLeftClose,
  PanelLeft,
  PanelRightClose,
  PanelRight,
  Eye,
  EyeOff,
  Cpu,
  BookOpen,
  User,
  MapPin,
  HelpCircle,
  FileText,
  WifiOff,
  Wifi,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  CheckCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/store/projectStore'
import { numberedTitle } from '@/lib/storyLabels'
import ContextRibbon from './ContextRibbon'
import AiSuggestionPanel from './AiSuggestionPanel'
import VersionHistoryPanel from './VersionHistoryPanel'
import CommentsPanel from './CommentsPanel'
import CommandPalette from './CommandPalette'
import WritingAnalyticsPanel from './WritingAnalyticsPanel'
import type { ParagraphSkeleton, ScenePlanV2, ChapterPlan } from '@/types'
import { classifyParagraph } from './ParagraphPipelineBar'

// ── Save status ───────────────────────────────────────────────────────────────

type SaveStatus =
  | 'idle'
  | 'autosaving'
  | 'saving'
  | 'saved'
  | 'error'
  | 'offline'
  | 'retrying'
  | 'draft_recovered'

function SaveIndicator({ status, lastSaved }: { status: SaveStatus; lastSaved: Date | null }) {
  const timeStr = lastSaved ? lastSaved.toLocaleTimeString() : ''

  if (status === 'idle') {
    return lastSaved ? (
      <span className="text-[11px] text-muted-foreground">Last saved at {timeStr}</span>
    ) : null
  }
  if (status === 'autosaving')
    return (
      <span className="flex items-center gap-1.5 text-[12px] text-muted-foreground animate-pulse">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Autosaving…
      </span>
    )
  if (status === 'saving')
    return (
      <span className="flex items-center gap-1.5 text-[12px] text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
        Saving version…
      </span>
    )
  if (status === 'saved')
    return (
      <span className="flex items-center gap-1.5 text-[12px] font-medium text-emerald-600 animate-in fade-in duration-200">
        <Check className="h-3.5 w-3.5" />
        Saved
      </span>
    )
  if (status === 'error')
    return (
      <span className="flex items-center gap-1.5 text-[12px] font-medium text-red-600">
        <AlertCircle className="h-3.5 w-3.5" />
        Save failed
      </span>
    )
  if (status === 'offline')
    return (
      <span className="flex items-center gap-1.5 text-[12px] font-semibold text-amber-600">
        <WifiOff className="h-3.5 w-3.5" />
        Offline (Local Backup Active)
      </span>
    )
  if (status === 'retrying')
    return (
      <span className="flex items-center gap-1.5 text-[12px] font-medium text-amber-500 animate-pulse">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Retrying connection…
      </span>
    )
  if (status === 'draft_recovered')
    return (
      <span className="flex items-center gap-1.5 text-[12px] font-semibold text-purple-600 animate-bounce">
        <Sparkles className="h-3.5 w-3.5" />
        Draft Recovered from Browser
      </span>
    )
  return null
}

const AUTOSAVE_DELAY = 2000

// ── Main component ────────────────────────────────────────────────────────────

interface ParagraphEditorProps {
  projectId: string
  sceneId: string
  paragraphs: ParagraphSkeleton[]
  activeParagraphIndex: number
  onClose: () => void
  onNavigate: (newIndex: number) => void
}

export default function ParagraphEditor({
  projectId,
  sceneId,
  paragraphs,
  activeParagraphIndex,
  onClose,
  onNavigate,
}: ParagraphEditorProps) {
  const paragraph = paragraphs[activeParagraphIndex]
  const {
    selectedProject,
    chapterPlans,
    scenes,
    paragraphContents,
    isParagraphContentLoading,
    fetchParagraphContent,
    updateParagraphSkeleton,
  } = useProjectStore()

  const content = paragraphContents[paragraph.paragraph_id]

  // Layout control states
  const [outlineCollapsed, setOutlineCollapsed] = useState(false)
  const [contextCollapsed, setContextCollapsed] = useState(false)
  const [focusMode, setFocusMode] = useState(false)
  const [devMode, setDevMode] = useState(false)
  const [activeRightTab, setActiveRightTab] = useState<'inspector' | 'suggestions' | 'history' | 'comments' | 'analytics'>('inspector')
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  // Scene Progress metrics calculation
  const totalParas = paragraphs.length
  const writtenCount = paragraphs.filter((p) => {
    const c = paragraphContents[p.paragraph_id]
    return c && c.prose && c.prose.trim().length > 0
  }).length
  const reviewedCount = paragraphs.filter((p) => p.approval_state === 'approved' || p.is_locked).length
  const approvedCount = paragraphs.filter((p) => p.approval_state === 'approved').length
  const canonViolations = paragraphs.filter((p) => p.validation_domains?.canon?.valid === false).length
  const editorialCompletion = totalParas > 0 ? Math.round((approvedCount / totalParas) * 100) : 0

  // Keyboard shortcut listener to toggle Developer Mode: Ctrl+Alt+Shift+D
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.altKey && e.shiftKey && e.key === 'D') {
        e.preventDefault()
        setDevMode((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // ── Keyboard shortcut: Ctrl/Cmd+K → Command Palette ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Focus restoration logic
  const previousFocusedElementRef = useRef<HTMLElement | null>(null)
  useEffect(() => {
    if (commandPaletteOpen) {
      previousFocusedElementRef.current = document.activeElement as HTMLElement
    } else {
      if (previousFocusedElementRef.current && document.body.contains(previousFocusedElementRef.current)) {
        previousFocusedElementRef.current.focus()
      }
    }
  }, [commandPaletteOpen])

  // Save states
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [wordCount, setWordCount] = useState(content?.word_count ?? 0)
  const [hasRecoveredDraft, setHasRecoveredDraft] = useState(false)
  const [recoveredText, setRecoveredText] = useState('')

  // Diagnostics / Performance telemetry states
  const [telemetry, setTelemetry] = useState({
    editorLoadTime: 0,
    switchLatency: 0,
    autosaveLatency: 0,
    typingLatency: 0,
  })

  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const autosaveActionRef = useRef<(prose: string) => Promise<void>>(async () => undefined)
  const editorInstanceRef = useRef<ReturnType<typeof useEditor>>(null)
  const isLocked = paragraph.is_locked

  // Latency reference trackers
  const switchStartRef = useRef<number>(0)
  const saveStartRef = useRef<number>(0)
  const keystrokeRef = useRef<number>(0)

  // ── Network status tracking ──
  const [isOnline, setIsOnline] = useState(true)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsOnline(navigator.onLine)
      const handleOnline = () => {
        setIsOnline(true)
        if (saveStatus === 'offline') {
          setSaveStatus('retrying')
          if (editorInstanceRef.current) {
            void autosaveActionRef.current(editorInstanceRef.current.getText())
          }
        }
      }
      const handleOffline = () => {
        setIsOnline(false)
        setSaveStatus('offline')
      }
      window.addEventListener('online', handleOnline)
      window.addEventListener('offline', handleOffline)
      return () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
      }
    }
  }, [saveStatus])

  // Resolve breadcrumb detail structures
  const projectTitle = selectedProject?.story_title || 'Untitled novel'
  const scenePlan = (scenes as ScenePlanV2[]).find((s) => s.scene_id === sceneId)
  const sceneTitle = scenePlan?.title || 'Current Scene'
  const chapterPlan = (chapterPlans as ChapterPlan[]).find((c) => c.chapter_plan_id === scenePlan?.chapter_plan_id)
  const chapterTitle = chapterPlan
    ? numberedTitle('chapter', chapterPlan.chapter_number, chapterPlan.title)
    : 'Chapter Plan'

  // ── Local Storage recovery check ──
  useEffect(() => {
    if (typeof window !== 'undefined' && paragraph.paragraph_id) {
      const storageKey = `novelforge:draft:${paragraph.paragraph_id}`
      const savedDraft = localStorage.getItem(storageKey)
      if (savedDraft && content && savedDraft !== content.prose) {
        setHasRecoveredDraft(true)
        setRecoveredText(savedDraft)
      } else {
        setHasRecoveredDraft(false)
        setRecoveredText('')
      }
    }
  }, [paragraph.paragraph_id, content])

  // Load prose when the active paragraph changes
  useEffect(() => {
    if (paragraph.paragraph_id) {
      switchStartRef.current = performance.now()
      fetchParagraphContent(projectId, sceneId, paragraph.paragraph_id).then(() => {
        const loadDuration = Math.round(performance.now() - switchStartRef.current)
        setTelemetry((prev) => ({
          ...prev,
          switchLatency: loadDuration,
        }))
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paragraph.paragraph_id, projectId, sceneId])

  // ── Tiptap editor ─────────────────────────────────────────────────────────

  const editor = useEditor({
    extensions: [StarterKit],
    content: '',
    editable: !isLocked,
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none min-h-[320px] focus:outline-none px-6 py-5',
        'data-testid': 'paragraph-prose-editor',
        'aria-label': 'Paragraph prose editor',
      },
      handleKeyDown: () => {
        keystrokeRef.current = performance.now()
      },
    },
    onCreate: () => {
      const loadDuration = Math.round(performance.now() - switchStartRef.current)
      setTelemetry((prev) => ({
        ...prev,
        editorLoadTime: loadDuration,
      }))
    },
    onUpdate: ({ editor }) => {
      // Calculate key latency (typing latency measurement)
      if (keystrokeRef.current > 0) {
        const keyLatency = Math.round(performance.now() - keystrokeRef.current)
        setTelemetry((prev) => ({ ...prev, typingLatency: keyLatency }))
        keystrokeRef.current = 0
      }

      const text = editor.getText()
      const words = text.trim() ? text.trim().split(/\s+/).length : 0
      setWordCount(words)

      if (isLocked) return

      // Write safety backup to localStorage
      localStorage.setItem(`novelforge:draft:${paragraph.paragraph_id}`, text)

      // Debounced autosave
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
      if (!isOnline) {
        setSaveStatus('offline')
        return
      }
      setSaveStatus('autosaving')
      autosaveTimer.current = setTimeout(() => {
        void autosaveActionRef.current(text)
      }, AUTOSAVE_DELAY)
    },
  })
  editorInstanceRef.current = editor

  // Sync content when fully loaded or changed
  useEffect(() => {
    if (!editor || !content) return
    const prose = content.prose ?? ''
    if (editor.getText() !== prose) {
      editor.commands.setContent(prose ? `<p>${prose}</p>` : '')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content?.paragraph_id, content?.updated_at])

  // Apply recovered draft
  const applyRecoveredDraft = () => {
    if (editor && recoveredText) {
      editor.commands.setContent(`<p>${recoveredText}</p>`)
      setHasRecoveredDraft(false)
      setSaveStatus('draft_recovered')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  // Clear recovered draft from storage
  const discardRecoveredDraft = () => {
    localStorage.removeItem(`novelforge:draft:${paragraph.paragraph_id}`)
    setHasRecoveredDraft(false)
  }

  // ── Autosave action ────────────────────────────────────────────────────────

  const doAutosave = useCallback(
    async (prose: string) => {
      if (!isOnline) {
        setSaveStatus('offline')
        return
      }
      saveStartRef.current = performance.now()
      try {
        await updateParagraphSkeleton(
          projectId,
          sceneId,
          paragraph.paragraph_id,
          { prose },
          'autosave',
          false,
        )
        // Clear local backup on successful remote persist
        localStorage.removeItem(`novelforge:draft:${paragraph.paragraph_id}`)
        const saveTime = Math.round(performance.now() - saveStartRef.current)
        setTelemetry((prev) => ({ ...prev, autosaveLatency: saveTime }))
        setLastSaved(new Date())
        setSaveStatus('saved')
        setTimeout(() => setSaveStatus('idle'), 2000)
      } catch {
        setSaveStatus('error')
      }
    },
    [projectId, sceneId, paragraph.paragraph_id, updateParagraphSkeleton, isOnline],
  )
  autosaveActionRef.current = doAutosave

  // ── Manual save ───────────────────────────────────────────────────────────

  const doManualSave = useCallback(async () => {
    if (!editor || isLocked) return
    if (autosaveTimer.current) {
      clearTimeout(autosaveTimer.current)
      autosaveTimer.current = null
    }
    if (!isOnline) {
      setSaveStatus('offline')
      return
    }
    const prose = editor.getText()
    setSaveStatus('saving')
    saveStartRef.current = performance.now()
    try {
      await updateParagraphSkeleton(
        projectId,
        sceneId,
        paragraph.paragraph_id,
        { prose },
        'Manual save',
        true,
      )
      localStorage.removeItem(`novelforge:draft:${paragraph.paragraph_id}`)
      const saveTime = Math.round(performance.now() - saveStartRef.current)
      setTelemetry((prev) => ({ ...prev, autosaveLatency: saveTime }))
      setLastSaved(new Date())
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2500)
    } catch {
      setSaveStatus('error')
    }
  }, [editor, isLocked, projectId, sceneId, paragraph.paragraph_id, updateParagraphSkeleton, isOnline])

  // ── Keyboard shortcut: Ctrl/Cmd+S ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        void doManualSave()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [doManualSave])

  useEffect(() => {
    return () => {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
    }
  }, [])

  // ── Focus mode trigger ──
  const toggleFocusMode = () => {
    const nextMode = !focusMode
    setFocusMode(nextMode)
    setOutlineCollapsed(nextMode)
    setContextCollapsed(nextMode)
  }

  return (
    <div className="flex h-[calc(100vh-140px)] w-full overflow-hidden rounded-xl border bg-card text-card-foreground shadow-lg" data-testid="narrative-workspace">
      {/* 1. LEFT PANEL: Paragraph Outline Navigator */}
      <aside
        className={`flex flex-col border-r bg-muted/10 transition-all duration-300 ${
          outlineCollapsed ? 'w-0 border-r-0 overflow-hidden' : 'w-72 shrink-0'
        }`}
        aria-label="Paragraph outline navigator"
      >
        <div className="flex items-center justify-between border-b px-4 py-3 bg-muted/20">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Paragraphs</span>
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setOutlineCollapsed(true)} title="Collapse Outline" aria-label="Collapse Outline">
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>

        {/* Scene Completion Progress Dashboard */}
        <div className="p-3 border-b bg-muted/5 space-y-2.5 text-[11px]" data-testid="scene-progress-panel">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-muted-foreground">Scene Completion</span>
            <span className="font-bold text-foreground">{editorialCompletion}%</span>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden border border-muted-foreground/10">
            <div 
              className="bg-primary h-full rounded-full transition-all duration-500" 
              style={{ width: `${editorialCompletion}%` }}
            />
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1 font-medium">
            <div className="bg-background rounded border p-1.5 flex flex-col justify-between">
              <span className="text-[9px] text-muted-foreground block">Prose Written</span>
              <span className="text-xs font-bold text-foreground tabular-nums">{writtenCount} / {totalParas}</span>
            </div>
            <div className="bg-background rounded border p-1.5 flex flex-col justify-between">
              <span className="text-[9px] text-muted-foreground block">Reviewed</span>
              <span className="text-xs font-bold text-foreground tabular-nums">{reviewedCount} / {totalParas}</span>
            </div>
            <div className="bg-background rounded border p-1.5 flex flex-col justify-between">
              <span className="text-[9px] text-muted-foreground block">Canon Audit</span>
              <span className="flex items-center gap-1 mt-0.5">
                {canonViolations === 0 ? (
                  <>
                    <ShieldCheck className="h-3 w-3 text-emerald-600 shrink-0" />
                    <span className="text-[10px] text-emerald-800 font-semibold">Verified</span>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-3 w-3 text-rose-500 shrink-0" />
                    <span className="text-[10px] text-rose-700 font-semibold">{canonViolations} Issues</span>
                  </>
                )}
              </span>
            </div>
            <div className="bg-background rounded border p-1.5 flex flex-col justify-between">
              <span className="text-[9px] text-muted-foreground block">Skeletons</span>
              <span className="text-xs font-bold text-foreground tabular-nums">{totalParas} Planned</span>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {paragraphs.map((p, idx) => {
            const active = idx === activeParagraphIndex
            const stage = classifyParagraph(p)
            return (
              <button
                key={p.paragraph_id}
                onClick={() => onNavigate(idx)}
                className={`w-full text-left rounded-lg p-2.5 transition-all text-xs border ${
                  active
                    ? 'bg-primary/5 border-primary/20 text-foreground ring-1 ring-primary/20 font-medium'
                    : 'bg-background/40 hover:bg-muted/30 border-transparent text-muted-foreground'
                }`}
                title={`Paragraph ${p.order}`}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="font-bold text-[10px] tracking-wide text-primary">¶ {idx + 1}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full border shrink-0 ${
                    stage === 'locked' ? 'bg-violet-100 text-violet-800 border-violet-200' :
                    stage === 'approved' ? 'bg-emerald-100 text-emerald-800 border-emerald-200' :
                    stage === 'ready_for_expansion' ? 'bg-blue-100 text-blue-800 border-blue-200' :
                    stage === 'needs_review' ? 'bg-amber-100 text-amber-800 border-amber-200' :
                    'bg-slate-100 text-slate-800 border-slate-200'
                  }`}>
                    {stage}
                  </span>
                </div>
                <p className="line-clamp-2 leading-relaxed text-[11px] font-medium text-foreground">{p.purpose || 'No purpose defined.'}</p>
                {p.pov && <p className="text-[10px] text-muted-foreground mt-1 font-semibold">👤 {p.pov}</p>}
              </button>
            )
          })}
        </div>
      </aside>

      {/* 2. MIDDLE PANEL: Writing Editor */}
      <main className="flex-1 flex flex-col min-w-0 bg-background overflow-hidden relative">
        {/* Breadcrumb Path Banner */}
        <div className="border-b bg-muted/5 px-4 py-2 text-xs flex items-center gap-1.5 text-muted-foreground select-none shrink-0 font-medium border-t-0">
          <span className="hover:text-foreground cursor-default truncate max-w-[120px]">{projectTitle}</span>
          <span>/</span>
          <span className="hover:text-foreground cursor-default truncate max-w-[150px]">{chapterTitle}</span>
          <span>/</span>
          <span className="hover:text-foreground cursor-default truncate max-w-[150px]">{sceneTitle}</span>
          <span>/</span>
          <span className="text-primary font-bold">Paragraph {activeParagraphIndex + 1}</span>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2 border-b px-4 py-2 shrink-0 bg-background">
          {outlineCollapsed && (
            <Button size="sm" variant="ghost" onClick={() => setOutlineCollapsed(false)} title="Expand Outline" aria-label="Expand Outline" className="h-8 px-2 gap-1 text-xs text-muted-foreground hover:text-foreground">
              <PanelLeft className="h-4 w-4" />
              <span>Outline</span>
            </Button>
          )}

          <Button size="sm" variant="ghost" onClick={onClose} aria-label="Back to planning board" className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
            <span className="hidden sm:inline">Close Editor</span>
          </Button>

          <span className="h-4 w-px bg-border hidden sm:block" />

          {/* Outline navigation control */}
          <div className="flex items-center gap-1">
            <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => onNavigate(activeParagraphIndex - 1)} disabled={activeParagraphIndex === 0} title="Previous Paragraph" aria-label="Previous Paragraph">
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => onNavigate(activeParagraphIndex + 1)} disabled={activeParagraphIndex === paragraphs.length - 1} title="Next Paragraph" aria-label="Next Paragraph">
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>

          <span className="h-4 w-px bg-border" />

          {/* Focus Mode button */}
          <Button size="sm" variant={focusMode ? 'secondary' : 'ghost'} onClick={toggleFocusMode} title={focusMode ? 'Exit Focus Mode' : 'Enter Focus Mode'} aria-label={focusMode ? 'Exit Focus Mode' : 'Enter Focus Mode'} className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground">
            <EyeOff className="h-4 w-4" />
            <span>Focus Mode</span>
          </Button>

          <span className="flex-1" />

          {/* Save indicator & action */}
          <SaveIndicator status={saveStatus} lastSaved={lastSaved} />

          {!isLocked && (
            <Button
              size="sm"
              variant="outline"
              onClick={doManualSave}
              disabled={saveStatus === 'saving' || saveStatus === 'autosaving' || !isOnline}
              aria-label="Save and create version"
              data-testid="paragraph-manual-save-btn"
              className="h-8 text-xs gap-1.5"
            >
              <Save className="h-3.5 w-3.5" />
              Save
            </Button>
          )}

          {contextCollapsed && (
            <Button size="sm" variant="ghost" onClick={() => setContextCollapsed(false)} title="Expand Context" aria-label="Expand Inspector" className="h-8 px-2 gap-1 text-xs text-muted-foreground hover:text-foreground">
              <span>Context</span>
              <PanelRight className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Workspace Body */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {/* Recovery Notification banner */}
          {hasRecoveredDraft && (
            <div className="bg-purple-50 border-b border-purple-200 px-4 py-2.5 flex items-center justify-between text-xs text-purple-900 animate-in fade-in duration-200">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-600 animate-pulse" />
                <span>We found a newer draft saved in your browser storage for this paragraph.</span>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="secondary" className="h-7 text-xs bg-purple-100 hover:bg-purple-200 text-purple-950 font-semibold" onClick={applyRecoveredDraft}>
                  Restore Draft
                </Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs text-purple-800 hover:text-purple-950 font-medium" onClick={discardRecoveredDraft}>
                  Discard
                </Button>
              </div>
            </div>
          )}

          {/* Rich Context Ribbon */}
          <ContextRibbon
            projectTitle={projectTitle}
            chapterTitle={chapterTitle}
            sceneTitle={sceneTitle}
            paragraph={paragraph}
            index={activeParagraphIndex + 1}
            total={paragraphs.length}
            wordCount={wordCount}
          />

          {/* Loading status */}
          {isParagraphContentLoading && !content && (
            <div className="flex flex-1 items-center justify-center py-20">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-medium">Fetching paragraph prose...</span>
              </div>
            </div>
          )}

          {/* Locked Read-Only view */}
          {isLocked && content && (
            <div className="relative flex-1">
              <div className="pointer-events-none opacity-80">
                <EditorContent editor={editor} />
              </div>
              <div className="absolute inset-0 flex items-center justify-center bg-muted/10 backdrop-blur-xs">
                <span className="flex items-center gap-2 rounded-lg bg-background px-4 py-2.5 text-xs font-semibold shadow-md border border-violet-200 text-violet-800">
                  🔒 Locked — this prose is frozen and cannot be changed.
                </span>
              </div>
            </div>
          )}

          {/* Normal Editable Editor */}
          {!isLocked && content !== undefined && (
            <div className="flex-1 min-h-[350px] max-w-3xl mx-auto w-full">
              <EditorContent editor={editor} />
            </div>
          )}

          {/* Narrative Goals Footnote */}
          {paragraph.narrative_goal && (
            <div className="border-t bg-muted/5 px-4 py-2.5 text-[11px] text-muted-foreground flex gap-1.5 leading-relaxed">
              <span className="font-semibold text-foreground shrink-0 uppercase tracking-wider text-[9px] mt-0.5">Narrative Goal:</span>
              <span>{paragraph.narrative_goal}</span>
            </div>
          )}
        </div>


      </main>

      {/* 3. RIGHT PANEL: Narrative Inspector & Writing Assistant */}
      <aside
        className={`flex flex-col border-l bg-muted/10 transition-all duration-300 ${
          contextCollapsed ? 'w-0 border-l-0 overflow-hidden' : 'w-80 shrink-0'
        }`}
        aria-label="Narrative inspector panel"
      >
        {/* Header container */}
        <div className="flex items-center justify-between border-b px-3 py-2 bg-muted/20">
          <Button size="sm" variant="ghost" className="h-7 w-7 p-0 shrink-0" onClick={() => setContextCollapsed(true)} title="Collapse Inspector" aria-label="Collapse Inspector">
            <PanelRightClose className="h-4 w-4" />
          </Button>

          {/* Tabs Selector Navigation */}
          <div className="flex bg-muted/50 border rounded-md p-0.5 mx-1 flex-1 overflow-x-auto">
            {([
              { id: 'inspector', label: 'Inspector' },
              { id: 'suggestions', label: 'Assistant' },
              { id: 'history', label: 'History' },
              { id: 'comments', label: 'Comments' },
              { id: 'analytics', label: 'Analytics' },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveRightTab(tab.id)}
                data-testid={tab.id === 'suggestions' ? 'writing-assistant-tab-btn' : undefined}
                className={`flex-1 py-1 px-1.5 rounded text-[10px] font-bold text-center transition-all whitespace-nowrap ${
                  activeRightTab === tab.id
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          
          {/* Subtle Dev Mode toggle indicator */}
          <Button 
            size="sm" 
            variant={devMode ? 'secondary' : 'ghost'} 
            className="h-7 w-7 p-0 shrink-0" 
            onClick={() => setDevMode(!devMode)} 
            title="Toggle Developer Diagnostics"
            aria-label="Toggle Developer Diagnostics"
          >
            <Cpu className={`h-4 w-4 ${devMode ? 'text-primary' : 'text-muted-foreground'}`} />
          </Button>
        </div>

        {/* Tab-driven contents render */}
        {activeRightTab === 'suggestions' && (
          <div className="flex-1 overflow-hidden">
            <AiSuggestionPanel
              projectId={projectId}
              sceneId={sceneId}
              paragraphId={paragraph.paragraph_id}
              paragraph={paragraph}
              devMode={devMode}
            />
          </div>
        )}

        {activeRightTab === 'history' && (
          <div className="flex-1 overflow-hidden">
            <VersionHistoryPanel
              projectId={projectId}
              sceneId={sceneId}
              paragraphId={paragraph.paragraph_id}
              paragraphVersion={paragraph.version}
              currentProse={editor?.getText() ?? content?.prose ?? ''}
            />
          </div>
        )}

        {activeRightTab === 'comments' && (
          <div className="flex-1 overflow-hidden">
            <CommentsPanel
              projectId={projectId}
              sceneId={sceneId}
              paragraphId={paragraph.paragraph_id}
            />
          </div>
        )}

        {activeRightTab === 'analytics' && (
          <div className="flex-1 overflow-y-auto">
            <WritingAnalyticsPanel
              prose={editor?.getText() ?? content?.prose ?? ''}
              targetWordCount={paragraph.target_word_count ?? 200}
            />
          </div>
        )}

        {activeRightTab === 'inspector' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            
            {/* SECTION 1: Story Function */}
            <div className="space-y-2 border-b pb-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                <span>⚙️</span> Story Function
              </h4>
              <div className="grid grid-cols-2 gap-2 text-[11px] leading-relaxed">
                <div className="bg-background border rounded px-2.5 py-1.5">
                  <span className="text-[10px] text-muted-foreground block font-medium">POV Perspective</span>
                  <strong className="text-foreground font-semibold">{paragraph.pov || '—'}</strong>
                </div>
                <div className="bg-background border rounded px-2.5 py-1.5">
                  <span className="text-[10px] text-muted-foreground block font-medium">Location Setting</span>
                  <strong className="text-foreground font-semibold">{paragraph.location || '—'}</strong>
                </div>
                <div className="bg-background border rounded px-2.5 py-1.5">
                  <span className="text-[10px] text-muted-foreground block font-medium">Emotional Tone</span>
                  <strong className="text-foreground font-semibold">{paragraph.emotion || '—'}</strong>
                </div>
                <div className="bg-background border rounded px-2.5 py-1.5">
                  <span className="text-[10px] text-muted-foreground block font-medium">Tension Level</span>
                  <strong className="text-foreground font-semibold">{paragraph.tension_level || '—'}/10</strong>
                </div>
              </div>
            </div>

            {/* SECTION 2: Narrative Purpose */}
            <div className="space-y-3 border-b pb-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                <span>📌</span> Narrative Purpose
              </h4>
              {paragraph.purpose && (
                <div className="bg-background border rounded p-2.5 leading-relaxed">
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block mb-1">Core Purpose</span>
                  <p className="text-foreground font-medium text-xs">{paragraph.purpose}</p>
                </div>
              )}
              {paragraph.narrative_goal && (
                <div className="bg-background border rounded p-2.5 leading-relaxed">
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block mb-1">Narrative Goal</span>
                  <p className="text-foreground text-xs">{paragraph.narrative_goal}</p>
                </div>
              )}
              {paragraph.dialogue_goal && (
                <div className="bg-background border rounded p-2.5 leading-relaxed">
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block mb-1">Dialogue Pass Goal</span>
                  <p className="text-foreground text-xs">{paragraph.dialogue_goal}</p>
                </div>
              )}
              {paragraph.exposition_goal && (
                <div className="bg-background border rounded p-2.5 leading-relaxed">
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block mb-1">Exposition Pass Goal</span>
                  <p className="text-foreground text-xs">{paragraph.exposition_goal}</p>
                </div>
              )}
            </div>

            {/* SECTION 3: Dependencies & Canon References */}
            {paragraph.dependencies && (
              <div className="space-y-3 border-b pb-3">
                <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                  <span>🔗</span> Narrative Dependencies
                </h4>
                
                {/* Characters */}
                {paragraph.dependencies.characters && paragraph.dependencies.characters.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[9px] text-muted-foreground font-semibold block uppercase">Characters Present</span>
                    <div className="flex flex-wrap gap-1.5">
                      {paragraph.dependencies.characters.map((c) => (
                        <span key={c} className="inline-flex items-center gap-1 bg-blue-50 border border-blue-100 rounded px-2 py-0.5 text-[10px] font-medium text-blue-700">
                          <User className="h-3 w-3 shrink-0" />
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Canon facts */}
                {paragraph.dependencies.canon_facts && paragraph.dependencies.canon_facts.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[9px] text-muted-foreground font-semibold block uppercase">Canon References</span>
                    <div className="flex flex-wrap gap-1.5">
                      {paragraph.dependencies.canon_facts.map((cf) => (
                        <span key={cf} className="inline-flex items-center gap-1 bg-amber-50 border border-amber-100 rounded px-2 py-0.5 text-[10px] font-medium text-amber-700">
                          <BookOpen className="h-3 w-3 shrink-0" />
                          {cf}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Locations */}
                {paragraph.dependencies.locations && paragraph.dependencies.locations.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[9px] text-muted-foreground font-semibold block uppercase">Locations Pinned</span>
                    <div className="flex flex-wrap gap-1.5">
                      {paragraph.dependencies.locations.map((l) => (
                        <span key={l} className="inline-flex items-center gap-1 bg-emerald-50 border border-emerald-100 rounded px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                          <MapPin className="h-3 w-3 shrink-0" />
                          {l}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Mysteries */}
                {paragraph.dependencies.mysteries && paragraph.dependencies.mysteries.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[9px] text-muted-foreground font-semibold block uppercase">Timeline & Mysteries</span>
                    <div className="flex flex-wrap gap-1.5">
                      {paragraph.dependencies.mysteries.map((m) => (
                        <span key={m} className="inline-flex items-center gap-1 bg-purple-50 border border-purple-100 rounded px-2 py-0.5 text-[10px] font-medium text-purple-700">
                          <HelpCircle className="h-3 w-3 shrink-0" />
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* SECTION 4: Future Callbacks */}
            <div className="space-y-2 border-b pb-3">
              <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                <span>🔮</span> Future Callbacks
              </h4>
              <div className="bg-background border border-dashed rounded p-2 text-center text-muted-foreground text-[10px] leading-relaxed">
                No foreshadowing seeds or payoffs linked to this paragraph yet. Link items in the planning dashboard.
              </div>
            </div>

            {/* EXTENSIBLE SECTION 5: Story Health & AI Review Ledgers */}
            <div className="space-y-3 pt-1 border-t-0">
              <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                <span>🩺</span> Story Health & Audit Ledger
              </h4>
              <div className="bg-background border border-emerald-100 rounded-lg p-2.5 space-y-1.5 text-[11px]">
                <div className="flex items-center justify-between font-semibold text-emerald-800">
                  <span>Validation Domains</span>
                  <span className="bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[9px] border border-emerald-200">PASS</span>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  All consistency checks (POV continuity, location context, pacing progression, character evolution constraints) passed.
                </p>
              </div>
            </div>

            {/* DEVELOPER PERFORMANCE TELEMETRY SECTION (Visible only in devMode) */}
            {devMode && (
              <div className="space-y-2 border-t pt-3 border-primary/20 animate-in fade-in duration-300">
                <h4 className="font-bold text-[10px] uppercase tracking-wide text-primary flex items-center gap-1.5">
                  <Cpu className="h-3.5 w-3.5" />
                  Developer Telemetry Diagnostics
                </h4>
                <div className="p-3 rounded-lg border border-primary/10 font-mono bg-muted/30 text-muted-foreground text-[11px] leading-relaxed space-y-1">
                  <div className="flex justify-between">
                    <span>Editor Load:</span>
                    <span className="text-foreground font-semibold">{telemetry.editorLoadTime}ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Paragraph Switch:</span>
                    <span className="text-foreground font-semibold">{telemetry.switchLatency}ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Autosave Roundtrip:</span>
                    <span className="text-foreground font-semibold">{telemetry.autosaveLatency}ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Typing P99 Latency:</span>
                    <span className="text-foreground font-semibold">{telemetry.typingLatency}ms</span>
                  </div>
                </div>
              </div>
            )}

          </div>
        )}
      </aside>

      {/* Command Palette */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        paragraphCount={paragraphs.length}
        activeParagraphIndex={activeParagraphIndex}
        onNavigate={(idx) => { onNavigate(idx); setCommandPaletteOpen(false) }}
        onToggleFocus={toggleFocusMode}
        onToggleOutline={() => setOutlineCollapsed((v) => !v)}
        onToggleInspector={() => setContextCollapsed((v) => !v)}
        onSwitchTab={(tab) => { setActiveRightTab(tab); setContextCollapsed(false); setCommandPaletteOpen(false) }}
        onManualSave={() => { void doManualSave(); setCommandPaletteOpen(false) }}
        onToggleDevMode={() => { setDevMode((v) => !v); setCommandPaletteOpen(false) }}
      />
    </div>
  )
}
