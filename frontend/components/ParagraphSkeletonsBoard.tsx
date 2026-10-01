/**
 * ParagraphSkeletonsBoard — Phase 4 RC2 Redesign
 *
 * Visual paragraph planning board for NovelForge.
 * Writers use this to decompose a scene into structured paragraph skeletons
 * before prose generation.
 *
 * Improvements in RC2:
 *  - Pipeline status bar with stage filtering
 *  - Drag-and-drop card reordering (HTML5 native, zero deps)
 *  - Redesigned cards — cleaner hierarchy, glanceable metadata chips
 *  - Responsive at 4 breakpoints
 *  - Keyboard nav (Escape to cancel edit)
 *  - Loading skeleton state
 *  - Toaster-style save confirmation
 *  - Generate button in empty state
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react'
import {
  ArrowLeft,
  Lock,
  Check,
  Trash2,
  Copy,
  RefreshCw,
  AlertTriangle,
  Play,
  Edit3,
  X,
  History,
  Sparkles,
  Eye,
  ChevronDown,
  ChevronRight,
  PenLine,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ParagraphSkeleton } from '@/types'
import ParagraphPipelineBar, {
  classifyParagraph,
  type PipelineStage,
} from './ParagraphPipelineBar'
import ParagraphEditor from './ParagraphEditor'

// ── Prop types ────────────────────────────────────────────────────────────────

interface ParagraphSkeletonsBoardProps {
  projectId: string
  sceneId: string
  sceneTitle: string
  paragraphs: ParagraphSkeleton[]
  isParagraphsLoading: boolean
  onGoBack: () => void
  fetchSceneParagraphs: (projectId: string, sceneId: string) => Promise<void>
  generateSceneParagraphs: (
    projectId: string,
    sceneId: string,
    changeReason?: string,
  ) => Promise<void>
  updateParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    updates: Record<string, any>,
    changeReason?: string,
    createVersion?: boolean,
  ) => Promise<void>
  reorderParagraphSkeletons: (
    projectId: string,
    sceneId: string,
    reorderPayload: { paragraph_id: string; order: number }[],
  ) => Promise<void>
  lockParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    isLocked: boolean,
  ) => Promise<void>
  deleteParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
  ) => Promise<void>
  duplicateParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
  ) => Promise<void>
  approveParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    approvalState: string,
  ) => Promise<void>
  regenerateParagraphSkeleton: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
    changeReason?: string,
  ) => Promise<void>
  getParagraphHistory: (
    projectId: string,
    sceneId: string,
    paragraphId: string,
  ) => Promise<any[]>
}

// ── Skeleton loading card ─────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border bg-card p-5 animate-pulse space-y-3">
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 rounded-full bg-muted" />
        <div className="h-4 w-32 rounded bg-muted" />
        <div className="ml-auto h-5 w-16 rounded-full bg-muted" />
      </div>
      <div className="h-3 w-3/4 rounded bg-muted" />
      <div className="h-3 w-1/2 rounded bg-muted" />
      <div className="grid grid-cols-4 gap-2 pt-1">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-10 rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  )
}

// ── Toast notification ────────────────────────────────────────────────────────

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 2500)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="fixed bottom-5 right-5 z-[200] flex items-center gap-2 rounded-lg border bg-card px-4 py-3 shadow-xl text-sm font-medium text-foreground animate-in slide-in-from-bottom-2 duration-200">
      <Check className="h-4 w-4 text-emerald-500 shrink-0" />
      {message}
    </div>
  )
}

// ── Status chip helpers ───────────────────────────────────────────────────────

function ApprovalChip({ state }: { state: string }) {
  const map: Record<string, string> = {
    approved: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
    rejected: 'bg-red-100 text-red-800 border border-red-200',
    pending: 'bg-amber-100 text-amber-800 border border-amber-200',
  }
  const labels: Record<string, string> = {
    approved: '✓ Approved',
    rejected: '✗ Rejected',
    pending: '⋯ Pending',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${map[state] ?? map.pending}`}
    >
      {labels[state] ?? state}
    </span>
  )
}

function TensionMeter({ level }: { level: string }) {
  const n = Math.max(1, Math.min(10, Number(level) || 5))
  const color =
    n <= 3 ? 'bg-sky-400' : n <= 6 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span>Tension</span>
      <div className="flex gap-0.5">
        {Array.from({ length: 10 }, (_, i) => (
          <div
            key={i}
            className={`h-1.5 w-1.5 rounded-full transition-colors ${
              i < n ? color : 'bg-muted'
            }`}
          />
        ))}
      </div>
      <span className="tabular-nums font-semibold text-foreground">{n}/10</span>
    </div>
  )
}

// ── Edit form modal ───────────────────────────────────────────────────────────

function EditModal({
  paragraph,
  onSave,
  onCancel,
}: {
  paragraph: ParagraphSkeleton
  onSave: (updates: Partial<ParagraphSkeleton>, reason: string) => void
  onCancel: () => void
}) {
  const [form, setForm] = useState<Partial<ParagraphSkeleton>>({ ...paragraph })
  const [reason, setReason] = useState('')
  const firstInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    firstInputRef.current?.focus()
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onCancel])

  const field = (
    key: keyof ParagraphSkeleton,
    label: string,
    type: 'input' | 'textarea' = 'input',
    inputType = 'text',
  ) => (
    <label className="block">
      <span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
        {label}
      </span>
      {type === 'textarea' ? (
        <textarea
          rows={3}
          className="w-full rounded-lg border bg-background p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
          value={(form[key] as string) || ''}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        />
      ) : (
        <input
          type={inputType}
          className="h-9 w-full rounded-lg border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          value={(form[key] as string | number) || ''}
          onChange={(e) =>
            setForm({
              ...form,
              [key]: inputType === 'number' ? Number(e.target.value) : e.target.value,
            })
          }
        />
      )}
    </label>
  )

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-sm p-4"
      onClick={(e) => e.target === e.currentTarget && onCancel()}
    >
      <div className="w-full max-w-2xl rounded-2xl border bg-card shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div>
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Edit3 className="h-5 w-5 text-primary" />
              Edit Paragraph #{paragraph.order}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Changes are versioned — all edits can be reviewed in history
            </p>
          </div>
          <Button size="icon" variant="ghost" onClick={onCancel}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Form body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            {field('pov', 'POV Character')}
            {field('location', 'Location / Setting')}
            {field('emotion', 'Emotional Tone')}
            {field('tension_level', 'Tension Level (1–10)', 'input', 'number')}
            {field('target_word_count', 'Target Word Count', 'input', 'number')}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {field('purpose', 'Paragraph Purpose', 'textarea')}
            {field('narrative_goal', 'Narrative Goal', 'textarea')}
            {field('dialogue_goal', 'Dialogue Pass Goal', 'textarea')}
            {field('exposition_goal', 'Exposition Goal', 'textarea')}
          </div>
          <label className="block">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Change Reason (optional — saved in version history)
            </span>
            <input
              ref={firstInputRef as any}
              className="h-9 w-full rounded-lg border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              placeholder="e.g. Adjusted to raise tension before confrontation…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t shrink-0">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={() => onSave(form, reason)} data-testid="save-edit-btn">
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── History panel ─────────────────────────────────────────────────────────────

function HistoryPanel({
  versions,
  isLoading,
  onClose,
}: {
  versions: any[]
  isLoading: boolean
  onClose: () => void
}) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-background/80 backdrop-blur-sm p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-2xl rounded-2xl border bg-card shadow-2xl flex flex-col max-h-[80vh] sm:max-h-[85vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <h3 className="font-bold text-lg flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Revision History
          </h3>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-lg bg-muted" />
              ))}
            </div>
          ) : versions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <History className="mx-auto h-8 w-8 mb-3 opacity-40" />
              <p className="text-sm">No previous versions found.</p>
            </div>
          ) : (
            versions.map((v, idx) => (
              <article
                key={v.version_id || idx}
                className="rounded-xl border bg-muted/30 p-4 text-sm"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-primary">
                    Version {v.version_number}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(v.created_at).toLocaleString()}
                  </span>
                </div>
                {v.change_reason && (
                  <p className="text-xs italic text-muted-foreground bg-muted px-2.5 py-1.5 rounded mb-3">
                    &ldquo;{v.change_reason}&rdquo;
                  </p>
                )}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">POV:</span>{' '}
                    <strong>{v.snapshot?.pov || '—'}</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Location:</span>{' '}
                    <strong>{v.snapshot?.location || '—'}</strong>
                  </div>
                  <div className="col-span-2">
                    <span className="text-muted-foreground">Purpose:</span>{' '}
                    {v.snapshot?.purpose}
                  </div>
                </div>
              </article>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// ── Paragraph Card ────────────────────────────────────────────────────────────

interface ParagraphCardProps {
  paragraph: ParagraphSkeleton
  index: number
  total: number
  isDragging: boolean
  isDragOver: boolean
  onEdit: () => void
  onWriteProse: () => void
  onHistory: () => void
  onLock: () => void
  onDelete: () => void
  onDuplicate: () => void
  onApprove: () => void
  onRegenerate: () => void
  onDragStart: () => void
  onDragEnd: () => void
  onDragOver: (e: React.DragEvent) => void
  onDrop: () => void
}

function ParagraphCard({
  paragraph: p,
  index,
  total,
  isDragging,
  isDragOver,
  onEdit,
  onWriteProse,
  onHistory,
  onLock,
  onDelete,
  onDuplicate,
  onApprove,
  onRegenerate,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
}: ParagraphCardProps) {
  const [expanded, setExpanded] = useState(false)
  const stage = classifyParagraph(p)

  const stageColors: Record<string, string> = {
    planning: 'border-l-slate-400',
    ready_for_expansion: 'border-l-blue-400',
    needs_review: 'border-l-amber-400',
    approved: 'border-l-emerald-400',
    locked: 'border-l-violet-400',
  }

  const hasValidationError =
    p.validation_domains &&
    Object.values(p.validation_domains).some((r: any) => !r.valid)

  const charList = p.dependencies?.characters || []

  return (
    <article
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={onDrop}
      data-testid={`paragraph-card-${p.order}`}
      className={`
        group relative rounded-xl border-l-4 bg-card shadow-sm
        transition-all duration-200 select-none
        ${stageColors[stage]}
        ${isDragging ? 'opacity-40 scale-[0.98]' : ''}
        ${isDragOver ? 'ring-2 ring-primary ring-offset-2 scale-[1.01]' : ''}
        ${p.is_locked ? 'opacity-80' : 'hover:shadow-md'}
        ${hasValidationError && !p.is_locked ? 'ring-1 ring-amber-300' : ''}
      `}
    >
      {/* ── Card Header ── */}
      <header className="flex items-start gap-3 px-4 pt-4 pb-3">
        {/* Drag handle */}
        <div
          className="mt-0.5 shrink-0 cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-60 transition-opacity"
          aria-hidden="true"
          title="Drag to reorder"
        >
          <svg
            width="10"
            height="16"
            viewBox="0 0 10 16"
            fill="currentColor"
            className="text-muted-foreground"
          >
            <circle cx="2" cy="2" r="1.5" />
            <circle cx="8" cy="2" r="1.5" />
            <circle cx="2" cy="8" r="1.5" />
            <circle cx="8" cy="8" r="1.5" />
            <circle cx="2" cy="14" r="1.5" />
            <circle cx="8" cy="14" r="1.5" />
          </svg>
        </div>

        {/* Order number */}
        <div className="shrink-0 flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
          {p.order}
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <ApprovalChip state={p.approval_state} />
            {p.is_locked && (
              <span className="inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-semibold text-violet-700">
                <Lock className="h-3 w-3" />
                Locked
              </span>
            )}
            {hasValidationError && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                <AlertTriangle className="h-3 w-3" />
                Warnings
              </span>
            )}
          </div>
          {/* Purpose — always visible */}
          <p className="mt-1.5 text-sm font-medium text-foreground leading-snug line-clamp-2">
            {p.purpose || <span className="text-muted-foreground italic">No purpose set</span>}
          </p>
        </div>

        {/* Expand / collapse */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 mt-0.5 h-7 w-7 flex items-center justify-center rounded-md hover:bg-muted transition-colors text-muted-foreground"
          aria-expanded={expanded}
          aria-label={expanded ? 'Collapse card' : 'Expand card'}
          data-testid={`expand-btn-${p.order}`}
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </header>

      {/* ── Glanceable meta chips — always visible ── */}
      <div className="px-4 pb-3 flex flex-wrap gap-2">
        {p.pov && (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700 border border-blue-100">
            👤 {p.pov}
          </span>
        )}
        {p.location && (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600 border border-slate-100">
            📍 {p.location}
          </span>
        )}
        {p.emotion && (
          <span className="inline-flex items-center gap-1 rounded-full bg-pink-50 px-2.5 py-1 text-[11px] font-medium text-pink-700 border border-pink-100">
            💫 {p.emotion}
          </span>
        )}
        {p.target_word_count > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
            ~{p.target_word_count}w
          </span>
        )}
        {charList.length > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2.5 py-1 text-[11px] font-medium text-violet-700 border border-violet-100">
            🎭 {charList.join(', ')}
          </span>
        )}
      </div>

      {/* ── Expanded detail section ── */}
      {expanded && (
        <div className="border-t mx-4 pt-3 pb-4 space-y-4 text-sm">
          {/* Narrative goals */}
          {(p.narrative_goal || p.dialogue_goal || p.exposition_goal) && (
            <div className="grid gap-3 sm:grid-cols-3">
              {p.narrative_goal && (
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                    Narrative Goal
                  </p>
                  <p className="text-xs text-foreground leading-relaxed">{p.narrative_goal}</p>
                </div>
              )}
              {p.dialogue_goal && (
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                    Dialogue Pass Goal
                  </p>
                  <p className="text-xs text-foreground leading-relaxed">{p.dialogue_goal}</p>
                </div>
              )}
              {p.exposition_goal && (
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                    Exposition Goal
                  </p>
                  <p className="text-xs text-foreground leading-relaxed">{p.exposition_goal}</p>
                </div>
              )}
            </div>
          )}

          {/* Tension meter */}
          <TensionMeter level={p.tension_level} />

          {/* Dependencies */}
          {(p.dependencies?.canon_facts?.length > 0 ||
            p.dependencies?.locations?.length > 0 ||
            p.dependencies?.mysteries?.length > 0) && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">
                Canon Dependencies
              </p>
              <div className="flex flex-wrap gap-1.5">
                {p.dependencies.canon_facts?.map((cf) => (
                  <span
                    key={cf}
                    className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800"
                  >
                    📚 {cf}
                  </span>
                ))}
                {p.dependencies.locations?.map((loc) => (
                  <span
                    key={loc}
                    className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800"
                  >
                    🗺 {loc}
                  </span>
                ))}
                {p.dependencies.mysteries?.map((m) => (
                  <span
                    key={m}
                    className="rounded-full bg-purple-100 px-2 py-0.5 text-[11px] font-medium text-purple-800"
                  >
                    ❓ {m}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Processing pipeline stages */}
          {Object.keys(p.processing_pipeline || {}).length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">
                Processing Stages
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(p.processing_pipeline).map(
                  ([stage, meta]: [string, any]) => (
                    <span
                      key={stage}
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                        meta.status === 'completed'
                          ? 'bg-emerald-100 text-emerald-800'
                          : meta.status === 'generating'
                          ? 'bg-blue-100 text-blue-800 animate-pulse'
                          : meta.status === 'rejected'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-muted text-muted-foreground'
                      }`}
                      title={`${stage}: ${meta.status}`}
                    >
                      {stage}
                    </span>
                  ),
                )}
              </div>
            </div>
          )}

          {/* Validation errors */}
          {hasValidationError && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-700 flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                Validation Alerts
              </p>
              {Object.entries(p.validation_domains).map(
                ([domain, res]: [string, any]) =>
                  !res.valid ? (
                    <p key={domain} className="text-xs text-amber-900">
                      <strong>{domain}:</strong> {res.errors?.join(' ')}
                    </p>
                  ) : null,
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Card Action Footer ── */}
      <footer
        className={`flex flex-wrap items-center justify-between gap-2 border-t bg-muted/20 px-4 py-2.5 rounded-b-xl ${
          expanded ? '' : 'rounded-t-none'
        }`}
      >
        {/* Left actions */}
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1"
            onClick={onEdit}
            disabled={p.is_locked}
            data-testid={`edit-btn-${p.order}`}
          >
            <Edit3 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Edit</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1 text-primary hover:text-primary hover:bg-primary/10"
            onClick={onWriteProse}
            title="Open prose editor"
            data-testid={`write-prose-btn-${p.order}`}
          >
            <PenLine className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Write</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1"
            onClick={onRegenerate}
            disabled={p.is_locked}
            title="AI Regenerate skeleton"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">AI Regen</span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1"
            onClick={onHistory}
            title="View revision history"
            data-testid={`history-btn-${p.order}`}
          >
            <History className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              History{p.version > 1 ? ` (${p.version - 1})` : ''}
            </span>
          </Button>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs gap-1 ${
              p.approval_state === 'approved'
                ? 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                : ''
            }`}
            onClick={onApprove}
            disabled={p.is_locked}
            data-testid={`approve-btn-${p.order}`}
          >
            <Check className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              {p.approval_state === 'approved' ? 'Approved' : 'Approve'}
            </span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs gap-1 ${
              p.is_locked ? 'text-violet-700 bg-violet-50 hover:bg-violet-100' : ''
            }`}
            onClick={onLock}
            title={p.is_locked ? 'Unlock paragraph' : 'Lock paragraph'}
            data-testid={`lock-btn-${p.order}`}
          >
            {p.is_locked ? (
              <Eye className="h-3.5 w-3.5" />
            ) : (
              <Lock className="h-3.5 w-3.5" />
            )}
            <span className="hidden sm:inline">
              {p.is_locked ? 'Unlock' : 'Lock'}
            </span>
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1"
            onClick={onDuplicate}
            title="Duplicate paragraph"
            data-testid={`duplicate-btn-${p.order}`}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs gap-1 text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={onDelete}
            title="Delete paragraph"
            data-testid={`delete-btn-${p.order}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </footer>
    </article>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({
  isGenerating,
  onGenerate,
}: {
  isGenerating: boolean
  onGenerate: () => void
}) {
  return (
    <div
      className="flex flex-col items-center justify-center py-20 rounded-2xl border-2 border-dashed bg-card/50 text-center px-6"
      data-testid="empty-state"
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <Sparkles className="h-8 w-8 text-primary" />
      </div>
      <h3 className="text-lg font-bold text-foreground mb-2">
        No paragraph skeletons yet
      </h3>
      <p className="max-w-sm text-sm text-muted-foreground leading-relaxed mb-6">
        Paragraph skeletons are structural blueprints — they define each
        paragraph&apos;s purpose, POV, emotion, tension, and dependencies{' '}
        <em>before</em> any prose is written. This gives the AI a precise
        creative brief for expansion.
      </p>
      <Button
        size="lg"
        disabled={isGenerating}
        onClick={onGenerate}
        data-testid="generate-btn"
        className="gap-2"
      >
        {isGenerating ? (
          <RefreshCw className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {isGenerating ? 'Generating Skeletons…' : 'Generate Paragraph Skeletons'}
      </Button>
      <p className="mt-3 text-xs text-muted-foreground">
        The AI will decompose your scene plan into a paragraph-by-paragraph blueprint
      </p>
    </div>
  )
}

// ── Main Board ────────────────────────────────────────────────────────────────

export default function ParagraphSkeletonsBoard({
  projectId,
  sceneId,
  sceneTitle,
  paragraphs,
  isParagraphsLoading,
  onGoBack,
  fetchSceneParagraphs,
  generateSceneParagraphs,
  updateParagraphSkeleton,
  reorderParagraphSkeletons,
  lockParagraphSkeleton,
  deleteParagraphSkeleton,
  duplicateParagraphSkeleton,
  approveParagraphSkeleton,
  regenerateParagraphSkeleton,
  getParagraphHistory,
}: ParagraphSkeletonsBoardProps) {
  // ── Local state ──────────────────────────────────────────────────────────
  const [editingParagraph, setEditingParagraph] =
    useState<ParagraphSkeleton | null>(null)
  const [historyParagraphId, setHistoryParagraphId] = useState<string | null>(
    null,
  )
  const [historyVersions, setHistoryVersions] = useState<any[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<PipelineStage | null>(null)
  /**
   * Index into `sortedParagraphs` for the paragraph currently open in the
   * prose editor.  null means the editor is closed (board view is shown).
   */
  const [activeParagraphEditorIndex, setActiveParagraphEditorIndex] =
    useState<number | null>(null)

  // Drag-and-drop state
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [dragOverId, setDragOverId] = useState<string | null>(null)

  // Derived — filtered and sorted paragraphs
  const sortedParagraphs = useMemo(
    () => [...paragraphs].sort((a, b) => a.order - b.order),
    [paragraphs],
  )
  const visibleParagraphs = useMemo(
    () =>
      activeFilter
        ? sortedParagraphs.filter(
            (p) => classifyParagraph(p) === activeFilter,
          )
        : sortedParagraphs,
    [sortedParagraphs, activeFilter],
  )

  const totalValidationErrors = useMemo(
    () =>
      paragraphs.reduce((acc, p) => {
        if (!p.validation_domains) return acc
        const errs = Object.values(p.validation_domains).filter(
          (r: any) => !r.valid,
        ).length
        return acc + errs
      }, 0),
    [paragraphs],
  )

  // ── Effects ──────────────────────────────────────────────────────────────
  useEffect(() => {
    void fetchSceneParagraphs(projectId, sceneId)
  }, [projectId, sceneId, fetchSceneParagraphs])

  // ── Handlers ─────────────────────────────────────────────────────────────

  const showToast = useCallback((msg: string) => {
    setToast(msg)
  }, [])

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    try {
      await generateSceneParagraphs(projectId, sceneId)
      showToast('Paragraph skeletons generated!')
    } finally {
      setIsGenerating(false)
    }
  }, [generateSceneParagraphs, projectId, sceneId, showToast])

  const handleSaveEdit = useCallback(
    async (updates: Partial<ParagraphSkeleton>, reason: string) => {
      if (!editingParagraph) return
      const payload = {
        pov: updates.pov || '',
        location: updates.location || '',
        purpose: updates.purpose || '',
        narrative_goal: updates.narrative_goal || '',
        scene_goal: updates.scene_goal || '',
        emotion: updates.emotion || '',
        tension_level: String(updates.tension_level || '5'),
        dialogue_goal: updates.dialogue_goal || '',
        exposition_goal: updates.exposition_goal || '',
        target_word_count: Number(updates.target_word_count || 250),
      }
      await updateParagraphSkeleton(
        projectId,
        sceneId,
        editingParagraph.paragraph_id,
        payload,
        reason,
        true,
      )
      setEditingParagraph(null)
      showToast('Changes saved & versioned')
    },
    [editingParagraph, updateParagraphSkeleton, projectId, sceneId, showToast],
  )

  const handleViewHistory = useCallback(
    async (paragraphId: string) => {
      setHistoryParagraphId(paragraphId)
      setIsLoadingHistory(true)
      try {
        const hist = await getParagraphHistory(projectId, sceneId, paragraphId)
        setHistoryVersions(hist)
      } catch {
        setHistoryVersions([])
      } finally {
        setIsLoadingHistory(false)
      }
    },
    [getParagraphHistory, projectId, sceneId],
  )

  const handleRegenerate = useCallback(
    async (paragraphId: string) => {
      const reason = window.prompt(
        'What should the AI focus on when regenerating this skeleton?',
        '',
      )
      if (reason === null) return
      await regenerateParagraphSkeleton(projectId, sceneId, paragraphId, reason)
      showToast('Skeleton regenerated')
    },
    [regenerateParagraphSkeleton, projectId, sceneId, showToast],
  )

  const handleDelete = useCallback(
    async (paragraphId: string) => {
      if (
        !window.confirm(
          'Delete this paragraph skeleton? This cannot be undone.',
        )
      )
        return
      await deleteParagraphSkeleton(projectId, sceneId, paragraphId)
      showToast('Paragraph deleted')
    },
    [deleteParagraphSkeleton, projectId, sceneId, showToast],
  )

  const handleDuplicate = useCallback(
    async (paragraphId: string) => {
      await duplicateParagraphSkeleton(projectId, sceneId, paragraphId)
      showToast('Paragraph duplicated')
    },
    [duplicateParagraphSkeleton, projectId, sceneId, showToast],
  )

  const handleApprove = useCallback(
    async (p: ParagraphSkeleton) => {
      const next = p.approval_state === 'approved' ? 'pending' : 'approved'
      await approveParagraphSkeleton(projectId, sceneId, p.paragraph_id, next)
      showToast(next === 'approved' ? 'Paragraph approved' : 'Approval removed')
    },
    [approveParagraphSkeleton, projectId, sceneId, showToast],
  )

  const handleLock = useCallback(
    async (p: ParagraphSkeleton) => {
      await lockParagraphSkeleton(
        projectId,
        sceneId,
        p.paragraph_id,
        !p.is_locked,
      )
      showToast(p.is_locked ? 'Paragraph unlocked' : 'Paragraph locked')
    },
    [lockParagraphSkeleton, projectId, sceneId, showToast],
  )

  // ── Drag-and-drop ─────────────────────────────────────────────────────────

  const handleDragStart = useCallback((paragraphId: string) => {
    setDraggingId(paragraphId)
  }, [])

  const handleDragEnd = useCallback(() => {
    setDraggingId(null)
    setDragOverId(null)
  }, [])

  const handleDragOver = useCallback(
    (e: React.DragEvent, paragraphId: string) => {
      e.preventDefault()
      if (paragraphId !== draggingId) setDragOverId(paragraphId)
    },
    [draggingId],
  )

  const handleDrop = useCallback(
    async (targetId: string) => {
      if (!draggingId || draggingId === targetId) return
      const draggingIndex = sortedParagraphs.findIndex(
        (p) => p.paragraph_id === draggingId,
      )
      const targetIndex = sortedParagraphs.findIndex(
        (p) => p.paragraph_id === targetId,
      )
      if (draggingIndex === -1 || targetIndex === -1) return

      // Build reordered list
      const reordered = [...sortedParagraphs]
      const [moved] = reordered.splice(draggingIndex, 1)
      reordered.splice(targetIndex, 0, moved)
      const payload = reordered.map((p, i) => ({
        paragraph_id: p.paragraph_id,
        order: i + 1,
      }))
      setDraggingId(null)
      setDragOverId(null)
      await reorderParagraphSkeletons(projectId, sceneId, payload)
      showToast('Paragraphs reordered')
    },
    [
      draggingId,
      sortedParagraphs,
      reorderParagraphSkeletons,
      projectId,
      sceneId,
      showToast,
    ],
  )

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div
      className="space-y-5"
      data-testid="paragraph-planning-board"
    >
      {/* ── Modals ── */}
      {editingParagraph && (
        <EditModal
          paragraph={editingParagraph}
          onSave={handleSaveEdit}
          onCancel={() => setEditingParagraph(null)}
        />
      )}
      {historyParagraphId && (
        <HistoryPanel
          versions={historyVersions}
          isLoading={isLoadingHistory}
          onClose={() => setHistoryParagraphId(null)}
        />
      )}
      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}

      {/* ── Page header ── */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={onGoBack}
            data-testid="back-to-drafting-btn"
          >
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            <span className="hidden sm:inline">Back to Drafting</span>
            <span className="sm:hidden">Back</span>
          </Button>
          <div className="border-l pl-3">
            <h1
              className="text-xl font-bold tracking-tight text-foreground leading-tight line-clamp-2"
              data-testid="board-scene-title"
            >
              {sceneTitle}
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Paragraph-Level Decomposition Board
            </p>
          </div>
        </div>

        {/* Header stats */}
        <div className="flex items-center gap-2 shrink-0">
          {totalValidationErrors > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
              <AlertTriangle className="h-3.5 w-3.5" />
              {totalValidationErrors} warning{totalValidationErrors !== 1 ? 's' : ''}
            </span>
          ) : paragraphs.length > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
              <Check className="h-3.5 w-3.5" />
              Board Valid
            </span>
          ) : null}
          <span className="rounded-lg bg-muted px-3 py-1 text-xs font-medium text-muted-foreground tabular-nums">
            {paragraphs.length} paragraph{paragraphs.length !== 1 ? 's' : ''}
          </span>
          {paragraphs.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerate}
              disabled={isGenerating}
              title="Regenerate all paragraph skeletons"
              data-testid="regenerate-all-btn"
            >
              {isGenerating ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              <span className="ml-1.5 hidden sm:inline">Regenerate All</span>
            </Button>
          )}
        </div>
      </header>

      {/* ── Pipeline bar (shows when we have paragraphs) ── */}
      {paragraphs.length > 0 && (
        <ParagraphPipelineBar
          paragraphs={paragraphs}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
        />
      )}

      {/* ── Loading skeletons ── */}
      {isParagraphsLoading && paragraphs.length === 0 && (
        <div className="space-y-4" data-testid="loading-state">
          {[1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* ── Empty state ── */}
      {!isParagraphsLoading && paragraphs.length === 0 && (
        <EmptyState isGenerating={isGenerating} onGenerate={handleGenerate} />
      )}

      {/* ── Active filter empty state ── */}
      {paragraphs.length > 0 && activeFilter && visibleParagraphs.length === 0 && (
        <div className="text-center py-10 rounded-xl border border-dashed text-muted-foreground">
          <p className="text-sm">No paragraphs in this stage.</p>
          <button
            className="mt-2 text-xs underline"
            onClick={() => setActiveFilter(null)}
          >
            Show all paragraphs
          </button>
        </div>
      )}

      {/* ── Prose editor — replaces card list when a paragraph is open ── */}
      {activeParagraphEditorIndex !== null && sortedParagraphs.length > 0 && (
        <ParagraphEditor
          projectId={projectId}
          sceneId={sceneId}
          paragraphs={sortedParagraphs}
          activeParagraphIndex={activeParagraphEditorIndex}
          onClose={() => setActiveParagraphEditorIndex(null)}
          onNavigate={(newIdx) => setActiveParagraphEditorIndex(newIdx)}
        />
      )}

      {/* ── Paragraph cards ── */}
      {activeParagraphEditorIndex === null && visibleParagraphs.length > 0 && (
        <section
          className="space-y-3"
          aria-label="Paragraph skeleton cards"
        >
          {activeFilter && (
            <p className="text-xs text-muted-foreground px-1">
              Showing {visibleParagraphs.length} of {sortedParagraphs.length}{' '}
              paragraphs
            </p>
          )}
          {visibleParagraphs.map((p, idx) => (
            <ParagraphCard
              key={p.paragraph_id}
              paragraph={p}
              index={idx}
              total={visibleParagraphs.length}
              isDragging={draggingId === p.paragraph_id}
              isDragOver={dragOverId === p.paragraph_id}
              onEdit={() => setEditingParagraph(p)}
              onWriteProse={() => {
                // Map back to sortedParagraphs index for navigation
                const sortedIdx = sortedParagraphs.findIndex(
                  (sp) => sp.paragraph_id === p.paragraph_id,
                )
                setActiveParagraphEditorIndex(sortedIdx >= 0 ? sortedIdx : idx)
              }}
              onHistory={() => handleViewHistory(p.paragraph_id)}
              onLock={() => handleLock(p)}
              onDelete={() => handleDelete(p.paragraph_id)}
              onDuplicate={() => handleDuplicate(p.paragraph_id)}
              onApprove={() => handleApprove(p)}
              onRegenerate={() => handleRegenerate(p.paragraph_id)}
              onDragStart={() => handleDragStart(p.paragraph_id)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => handleDragOver(e, p.paragraph_id)}
              onDrop={() => handleDrop(p.paragraph_id)}
            />
          ))}
        </section>
      )}

      {/* ── Drop target hint during active drag ── */}
      {draggingId && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 rounded-full bg-primary px-4 py-2 text-xs font-medium text-primary-foreground shadow-lg">
          Drop to reorder
        </div>
      )}
    </div>
  )
}
