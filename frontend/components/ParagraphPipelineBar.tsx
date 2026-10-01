/**
 * ParagraphPipelineBar
 *
 * Shows the production-pipeline progress for a scene's paragraph skeletons.
 * Clicking a stage pill filters the board to only show paragraphs in that
 * stage. Clicking the active filter again clears it.
 */

import type { ParagraphSkeleton } from '@/types'

// ── Stage definitions ────────────────────────────────────────────────────────

export type PipelineStage =
  | 'planning'
  | 'ready_for_expansion'
  | 'needs_review'
  | 'approved'
  | 'locked'

interface StageConfig {
  id: PipelineStage
  label: string
  description: string
  color: string          // bar fill
  bgLight: string        // pill background
  textColor: string      // pill text
  activeBg: string       // selected state background
  activeRing: string     // selected state ring
  icon: string           // emoji icon
}

export const PIPELINE_STAGES: StageConfig[] = [
  {
    id: 'planning',
    label: 'Planning',
    description: 'Skeleton generated, awaiting review',
    color: 'bg-slate-400',
    bgLight: 'bg-slate-100 hover:bg-slate-200',
    textColor: 'text-slate-700',
    activeBg: 'bg-slate-200',
    activeRing: 'ring-2 ring-slate-500',
    icon: '📝',
  },
  {
    id: 'ready_for_expansion',
    label: 'Ready for Expansion',
    description: 'Reviewed — ready for prose generation',
    color: 'bg-blue-400',
    bgLight: 'bg-blue-50 hover:bg-blue-100',
    textColor: 'text-blue-700',
    activeBg: 'bg-blue-100',
    activeRing: 'ring-2 ring-blue-500',
    icon: '🔵',
  },
  {
    id: 'needs_review',
    label: 'Needs Review',
    description: 'Validation warnings or AI notes require attention',
    color: 'bg-amber-400',
    bgLight: 'bg-amber-50 hover:bg-amber-100',
    textColor: 'text-amber-700',
    activeBg: 'bg-amber-100',
    activeRing: 'ring-2 ring-amber-500',
    icon: '⚠️',
  },
  {
    id: 'approved',
    label: 'Approved',
    description: 'Skeleton signed off — will be used in expansion',
    color: 'bg-emerald-400',
    bgLight: 'bg-emerald-50 hover:bg-emerald-100',
    textColor: 'text-emerald-700',
    activeBg: 'bg-emerald-100',
    activeRing: 'ring-2 ring-emerald-500',
    icon: '✅',
  },
  {
    id: 'locked',
    label: 'Locked',
    description: 'Content locked — will not be touched by AI',
    color: 'bg-violet-400',
    bgLight: 'bg-violet-50 hover:bg-violet-100',
    textColor: 'text-violet-700',
    activeBg: 'bg-violet-100',
    activeRing: 'ring-2 ring-violet-500',
    icon: '🔒',
  },
]

// ── Classify a paragraph into a stage ────────────────────────────────────────

export function classifyParagraph(p: ParagraphSkeleton): PipelineStage {
  if (p.is_locked) return 'locked'
  if (p.approval_state === 'approved') return 'approved'
  // Check validation domains for errors
  const hasValidationError =
    p.validation_domains &&
    Object.values(p.validation_domains).some((r: any) => !r.valid)
  if (hasValidationError) return 'needs_review'
  // Check if paragraph has been reviewed at all (has any pipeline stage done)
  const pipelineKeys = Object.keys(p.processing_pipeline || {})
  const anyCompleted = pipelineKeys.some(
    (k) => (p.processing_pipeline as any)[k]?.status === 'completed',
  )
  if (anyCompleted) return 'ready_for_expansion'
  return 'planning'
}

// ── Stage counts helper ───────────────────────────────────────────────────────

export function computeStageCounts(
  paragraphs: ParagraphSkeleton[],
): Record<PipelineStage, number> {
  const counts: Record<PipelineStage, number> = {
    planning: 0,
    ready_for_expansion: 0,
    needs_review: 0,
    approved: 0,
    locked: 0,
  }
  paragraphs.forEach((p) => {
    counts[classifyParagraph(p)]++
  })
  return counts
}

// ── Component ─────────────────────────────────────────────────────────────────

interface ParagraphPipelineBarProps {
  paragraphs: ParagraphSkeleton[]
  activeFilter: PipelineStage | null
  onFilterChange: (stage: PipelineStage | null) => void
}

export default function ParagraphPipelineBar({
  paragraphs,
  activeFilter,
  onFilterChange,
}: ParagraphPipelineBarProps) {
  const counts = computeStageCounts(paragraphs)
  const total = paragraphs.length

  if (total === 0) return null

  return (
    <div
      className="rounded-xl border bg-card p-4 space-y-3"
      data-testid="pipeline-bar"
      role="region"
      aria-label="Scene paragraph production pipeline"
    >
      {/* Title row */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Production Pipeline
        </h2>
        {activeFilter && (
          <button
            className="text-xs text-muted-foreground underline hover:text-foreground transition-colors"
            onClick={() => onFilterChange(null)}
            data-testid="pipeline-clear-filter"
          >
            Show all {total}
          </button>
        )}
      </div>

      {/* Progress bar — stacked segments */}
      <div
        className="relative flex h-3 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label="Pipeline stage distribution"
        aria-valuemin={0}
        aria-valuemax={total}
      >
        {PIPELINE_STAGES.map((stage) => {
          const count = counts[stage.id]
          if (count === 0) return null
          const pct = (count / total) * 100
          return (
            <div
              key={stage.id}
              className={`h-full transition-all duration-500 ${stage.color} ${
                activeFilter === stage.id ? 'opacity-100' : activeFilter ? 'opacity-40' : 'opacity-80'
              }`}
              style={{ width: `${pct}%` }}
              title={`${stage.label}: ${count}`}
            />
          )
        })}
      </div>

      {/* Stage pill buttons */}
      <div className="flex flex-wrap gap-2">
        {PIPELINE_STAGES.map((stage) => {
          const count = counts[stage.id]
          const isActive = activeFilter === stage.id
          const isEmpty = count === 0

          return (
            <button
              key={stage.id}
              disabled={isEmpty}
              onClick={() => onFilterChange(isActive ? null : stage.id)}
              data-testid={`pipeline-stage-${stage.id}`}
              aria-pressed={isActive}
              title={stage.description}
              className={`
                inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium
                transition-all duration-150 select-none
                ${isEmpty ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}
                ${isActive
                  ? `${stage.activeBg} ${stage.textColor} ${stage.activeRing}`
                  : isEmpty
                  ? 'bg-muted text-muted-foreground'
                  : `${stage.bgLight} ${stage.textColor}`
                }
              `}
            >
              <span aria-hidden="true">{stage.icon}</span>
              <span>{stage.label}</span>
              <span
                className={`
                  rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums
                  ${isActive ? 'bg-white/60' : 'bg-black/10'}
                `}
              >
                {count}
              </span>
              {/* Mini bar for this stage */}
              {count > 0 && (
                <span
                  className={`hidden sm:inline-block h-1 rounded-full ${stage.color} opacity-70`}
                  style={{ width: `${Math.max(12, (count / total) * 48)}px` }}
                  aria-hidden="true"
                />
              )}
            </button>
          )
        })}
      </div>

      {/* Active filter callout */}
      {activeFilter && (
        <p className="text-xs text-muted-foreground italic">
          Showing{' '}
          <span className="font-semibold text-foreground">
            {counts[activeFilter]} paragraph{counts[activeFilter] !== 1 ? 's' : ''}
          </span>{' '}
          in <span className="font-semibold text-foreground">{PIPELINE_STAGES.find(s => s.id === activeFilter)?.label}</span>
        </p>
      )}
    </div>
  )
}
