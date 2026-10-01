'use client'

/**
 * WritingAnalyticsPanel — Phase 5B
 *
 * Modular writing metrics registry for the active paragraph.
 * Metrics:
 * - Word count (live) vs. target
 * - Sentence count
 * - Avg sentence length (pacing proxy)
 * - Dialogue ratio (% of words in quotes)
 * - Exposition ratio
 * - Readability (Flesch-Kincaid grade level)
 * - Paragraph-level progress bar
 */

import { useMemo } from 'react'
import { BarChart2, Target, MessageSquare, Book, Zap, BookOpen } from 'lucide-react'

// ── Text analysis utilities ────────────────────────────────────────────────

function countWords(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}

function countSentences(text: string): number {
  const matches = text.match(/[^.!?]+[.!?]+/g)
  return matches ? matches.length : 0
}

function avgSentenceLength(text: string): number {
  const words = countWords(text)
  const sentences = countSentences(text)
  return sentences > 0 ? Math.round(words / sentences) : 0
}

/**
 * Count words that appear inside dialogue quotes (straight or curly).
 */
function countDialogueWords(text: string): number {
  const matches = text.match(/[""\u201C\u201D][^""\u201C\u201D]+[""\u201C\u201D]/g)
  if (!matches) return 0
  return matches.reduce((acc, m) => acc + countWords(m), 0)
}

/**
 * Flesch-Kincaid Grade Level (approximation without syllable counting).
 * Uses average syllables per word approximated as: chars/word * 0.4
 */
function fleschKincaidGrade(text: string): number | null {
  const words = countWords(text)
  const sentences = countSentences(text)
  if (words < 10 || sentences < 1) return null

  // Approximate syllables: count vowel groups per word
  const syllableApprox = text
    .replace(/[^a-zA-Z\s]/g, '')
    .split(/\s+/)
    .reduce((acc, word) => {
      const vowelGroups = word.match(/[aeiou]+/gi)
      return acc + Math.max(1, vowelGroups ? vowelGroups.length : 1)
    }, 0)

  const asl = words / sentences // avg sentence length
  const asw = syllableApprox / words // avg syllables per word
  const grade = 0.39 * asl + 11.8 * asw - 15.59
  return Math.max(0, Math.round(grade * 10) / 10)
}

function readabilityLabel(grade: number | null): { label: string; color: string } {
  if (grade === null) return { label: 'Too short', color: 'text-muted-foreground' }
  if (grade <= 6) return { label: 'Elementary', color: 'text-emerald-600' }
  if (grade <= 9) return { label: 'Middle School', color: 'text-blue-600' }
  if (grade <= 12) return { label: 'High School', color: 'text-violet-600' }
  if (grade <= 16) return { label: 'College', color: 'text-amber-600' }
  return { label: 'Complex', color: 'text-red-600' }
}

// ── Metric card ────────────────────────────────────────────────────────────

interface MetricCardProps {
  label: string
  value: string | number
  subtext?: string
  icon: React.ReactNode
  color?: string
  progress?: number // 0-100
  progressColor?: string
}

function MetricCard({ label, value, subtext, icon, color = 'text-foreground', progress, progressColor = 'bg-primary' }: MetricCardProps) {
  return (
    <div className="bg-background rounded-lg border p-3 space-y-1.5">
      <div className="flex items-center gap-1.5">
        <span className="text-muted-foreground shrink-0">{icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
      </div>
      <div className={`text-xl font-bold tabular-nums ${color}`}>{value}</div>
      {subtext && <p className="text-[10px] text-muted-foreground leading-snug">{subtext}</p>}
      {progress !== undefined && (
        <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${progressColor}`}
            style={{ width: `${Math.min(100, progress)}%` }}
          />
        </div>
      )}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

interface WritingAnalyticsPanelProps {
  prose: string
  targetWordCount?: number
}

export default function WritingAnalyticsPanel({
  prose,
  targetWordCount = 200,
}: WritingAnalyticsPanelProps) {
  const metrics = useMemo(() => {
    const words = countWords(prose)
    const sentences = countSentences(prose)
    const avgSL = avgSentenceLength(prose)
    const dialogueWords = countDialogueWords(prose)
    const dialoguePct = words > 0 ? Math.round((dialogueWords / words) * 100) : 0
    const expositionPct = 100 - dialoguePct
    const fkGrade = fleschKincaidGrade(prose)
    const readability = readabilityLabel(fkGrade)
    const progressPct = targetWordCount > 0 ? Math.round((words / targetWordCount) * 100) : 0

    // Pacing evaluation
    let pacingLabel = 'Unknown'
    let pacingColor = 'text-muted-foreground'
    if (avgSL > 0) {
      if (avgSL <= 10) { pacingLabel = 'Fast'; pacingColor = 'text-emerald-600' }
      else if (avgSL <= 18) { pacingLabel = 'Moderate'; pacingColor = 'text-blue-600' }
      else if (avgSL <= 25) { pacingLabel = 'Slow'; pacingColor = 'text-amber-600' }
      else { pacingLabel = 'Very Slow'; pacingColor = 'text-red-600' }
    }

    return {
      words, sentences, avgSL, dialogueWords, dialoguePct, expositionPct,
      fkGrade, readability, progressPct, pacingLabel, pacingColor,
    }
  }, [prose, targetWordCount])

  if (!prose.trim()) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground px-4 text-center">
        <BarChart2 className="h-7 w-7 text-muted-foreground/30" />
        <p className="text-xs">Start writing to see analytics.</p>
      </div>
    )
  }

  return (
    <div className="p-3 space-y-3">
      {/* Header */}
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
        <BarChart2 className="h-3.5 w-3.5" />
        Writing Analytics
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard
          label="Words"
          value={metrics.words}
          icon={<BookOpen className="h-3.5 w-3.5" />}
          subtext={`Target: ${targetWordCount}w`}
          progress={metrics.progressPct}
          progressColor={metrics.progressPct >= 100 ? 'bg-emerald-500' : 'bg-primary'}
        />

        <MetricCard
          label="Sentences"
          value={metrics.sentences}
          icon={<Book className="h-3.5 w-3.5" />}
          subtext={`~${metrics.avgSL}w avg length`}
        />

        <MetricCard
          label="Pacing"
          value={metrics.pacingLabel}
          icon={<Zap className="h-3.5 w-3.5" />}
          color={metrics.pacingColor}
          subtext={`${metrics.avgSL} words/sentence`}
        />

        <MetricCard
          label="Readability"
          value={metrics.fkGrade !== null ? `Grade ${metrics.fkGrade}` : '—'}
          icon={<Target className="h-3.5 w-3.5" />}
          color={metrics.readability.color}
          subtext={metrics.readability.label}
        />
      </div>

      {/* Dialogue / Exposition breakdown */}
      <div className="bg-background rounded-lg border p-3 space-y-2">
        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <MessageSquare className="h-3.5 w-3.5" />
          Prose Composition
        </div>

        <div className="space-y-2">
          {/* Dialogue */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-medium text-foreground">Dialogue</span>
              <span className="text-[11px] font-bold tabular-nums text-violet-700">
                {metrics.dialoguePct}%
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full bg-violet-500 transition-all duration-500"
                style={{ width: `${metrics.dialoguePct}%` }}
              />
            </div>
          </div>

          {/* Exposition */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-medium text-foreground">Exposition</span>
              <span className="text-[11px] font-bold tabular-nums text-blue-700">
                {metrics.expositionPct}%
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-500"
                style={{ width: `${metrics.expositionPct}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Progress vs target */}
      <div className="bg-background rounded-lg border p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Word Count Progress
          </span>
          <span className={`text-[11px] font-bold tabular-nums ${
            metrics.progressPct >= 100 ? 'text-emerald-600' : 'text-foreground'
          }`}>
            {metrics.words} / {targetWordCount}
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              metrics.progressPct >= 100 ? 'bg-emerald-500' : 'bg-primary'
            }`}
            style={{ width: `${Math.min(100, metrics.progressPct)}%` }}
          />
        </div>
        <p className="text-[10px] text-muted-foreground">
          {metrics.progressPct >= 100
            ? `✓ Target reached (+${metrics.words - targetWordCount}w over)`
            : `${targetWordCount - metrics.words} words remaining`}
        </p>
      </div>
    </div>
  )
}
