/**
 * ContextRibbon — Milestone 5.1 Refined
 *
 * A metadata ribbon displayed above the Tiptap editor.
 * Surfaces Project, Chapter, Scene, Paragraph details, Purpose,
 * Characters, Canon/Timeline references, Target vs Current word count,
 * and the classification/pipeline stage.
 */

import type { ParagraphSkeleton } from '@/types'
import { Lock, Check, AlertCircle, Eye, HelpCircle, BookOpen, User, MapPin } from 'lucide-react'
import { classifyParagraph } from './ParagraphPipelineBar'

// ── Tension bar ───────────────────────────────────────────────────────────────

function TensionDots({ level }: { level: string }) {
  const n = Math.max(1, Math.min(10, Number(level) || 5))
  const color = n <= 3 ? 'bg-sky-400' : n <= 6 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <span className="flex items-center gap-0.5">
      {Array.from({ length: 10 }, (_, i) => (
        <span
          key={i}
          className={`inline-block h-1.5 w-1.5 rounded-full ${i < n ? color : 'bg-muted-foreground/20'}`}
        />
      ))}
      <span className="ml-1 text-[11px] font-semibold tabular-nums text-foreground">
        {n}/10
      </span>
    </span>
  )
}

// ── Status/Pipeline stage badge ───────────────────────────────────────────────

function StageBadge({ stage }: { stage: string }) {
  const config: Record<string, { label: string; style: string }> = {
    planning: { label: 'Planning', style: 'bg-slate-100 text-slate-800 border-slate-200' },
    ready_for_expansion: { label: 'Ready', style: 'bg-blue-100 text-blue-800 border-blue-200' },
    needs_review: { label: 'Review', style: 'bg-amber-100 text-amber-800 border-amber-200' },
    approved: { label: 'Approved', style: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
    locked: { label: 'Locked', style: 'bg-violet-100 text-violet-800 border-violet-200' },
  }
  const item = config[stage] || config.planning
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-semibold border ${item.style}`}>
      {item.label}
    </span>
  )
}

export interface ContextRibbonProps {
  projectTitle: string
  chapterTitle: string
  sceneTitle: string
  paragraph: ParagraphSkeleton
  index: number
  total: number
  wordCount: number
}

export default function ContextRibbon({
  projectTitle,
  chapterTitle,
  sceneTitle,
  paragraph: p,
  index,
  total,
  wordCount,
}: ContextRibbonProps) {
  const stage = classifyParagraph(p)
  const characters = p.dependencies?.characters || []
  const canonFacts = p.dependencies?.canon_facts || []
  const locations = p.dependencies?.locations || []
  const mysteries = p.dependencies?.mysteries || []

  return (
    <div className="flex flex-col gap-3 rounded-t-xl border border-b-0 bg-muted/30 p-4 shadow-inner" aria-label="Paragraph context">
      {/* Top Row: Quick Breadcrumbs & Pacing/Tension */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-1.5 text-muted-foreground font-medium">
          <span className="font-semibold text-foreground truncate max-w-[120px]" title={projectTitle}>{projectTitle}</span>
          <span>→</span>
          <span className="truncate max-w-[150px]" title={chapterTitle}>{chapterTitle}</span>
          <span>→</span>
          <span className="truncate max-w-[150px]" title={sceneTitle}>{sceneTitle}</span>
          <span>→</span>
          <span className="text-primary font-bold">¶ {index} of {total}</span>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Tension */}
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span>Tension</span>
            <TensionDots level={p.tension_level} />
          </div>

          <span className="h-3.5 w-px bg-border" />

          {/* Word Count Progress */}
          <span className="text-[11px] font-medium tabular-nums text-muted-foreground">
            {wordCount} / {p.target_word_count || 250} words
          </span>

          {/* Stage */}
          <StageBadge stage={stage} />
        </div>
      </div>

      {/* Middle Row: Purpose */}
      {p.purpose && (
        <div className="text-sm bg-background/50 border border-muted/50 rounded-lg p-2.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-0.5">Paragraph Purpose</span>
          <p className="text-foreground font-medium text-xs leading-relaxed">{p.purpose}</p>
        </div>
      )}

      {/* Bottom Row: Dependencies (if any) */}
      {(characters.length > 0 || canonFacts.length > 0 || locations.length > 0 || mysteries.length > 0) && (
        <div className="flex flex-wrap gap-2 pt-1">
          {/* Characters */}
          {characters.map((c) => (
            <span key={c} className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 border border-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
              <User className="h-3 w-3 shrink-0" />
              {c}
            </span>
          ))}

          {/* Locations */}
          {locations.map((l) => (
            <span key={l} className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
              <MapPin className="h-3 w-3 shrink-0" />
              {l}
            </span>
          ))}

          {/* Canon facts */}
          {canonFacts.map((f) => (
            <span key={f} className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700" title="Canon fact dependency">
              <BookOpen className="h-3 w-3 shrink-0" />
              {f}
            </span>
          ))}

          {/* Mysteries */}
          {mysteries.map((m) => (
            <span key={m} className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 border border-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700" title="Mystery plot point dependency">
              <HelpCircle className="h-3 w-3 shrink-0" />
              {m}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

