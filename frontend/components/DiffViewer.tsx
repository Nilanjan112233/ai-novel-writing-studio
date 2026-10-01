'use client'

/**
 * DiffViewer — Phase 5B
 *
 * Professional prose diff viewer with word-level granularity.
 * - Unified mode: shows changes inline with color coding
 * - Side-by-side mode: left (old) / right (new) with synchronized highlighting
 * - Added text: green
 * - Removed text: red / strikethrough
 * - Unchanged text: muted
 */

import { useMemo, useState } from 'react'
import { Columns2, AlignLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

// ── Word-level diff algorithm ──────────────────────────────────────────────

type DiffOp = 'equal' | 'insert' | 'delete'

interface DiffChunk {
  op: DiffOp
  text: string
}

/**
 * Compute a simple word-level diff between two strings.
 * Uses the longest common subsequence (LCS) approach on token arrays.
 */
function computeWordDiff(oldText: string, newText: string): DiffChunk[] {
  const tokenize = (text: string) => text.split(/(\s+)/)
  const a = tokenize(oldText)
  const b = tokenize(newText)

  const m = a.length
  const n = b.length

  // LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  // Backtrack
  const chunks: DiffChunk[] = []
  let i = m
  let j = n
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      chunks.unshift({ op: 'equal', text: a[i - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      chunks.unshift({ op: 'insert', text: b[j - 1] })
      j--
    } else {
      chunks.unshift({ op: 'delete', text: a[i - 1] })
      i--
    }
  }

  return chunks
}

// ── Inline unified view ────────────────────────────────────────────────────

function UnifiedDiff({ chunks }: { chunks: DiffChunk[] }) {
  return (
    <div className="text-[12px] leading-relaxed font-serif p-3 bg-muted/10 rounded-lg border whitespace-pre-wrap break-words">
      {chunks.map((chunk, idx) => {
        if (chunk.op === 'equal') {
          return (
            <span key={idx} className="text-foreground">
              {chunk.text}
            </span>
          )
        }
        if (chunk.op === 'insert') {
          return (
            <span
              key={idx}
              className="bg-emerald-100 text-emerald-900 rounded-sm px-0.5"
            >
              {chunk.text}
            </span>
          )
        }
        return (
          <span
            key={idx}
            className="bg-red-100 text-red-800 line-through decoration-red-400 rounded-sm px-0.5"
          >
            {chunk.text}
          </span>
        )
      })}
    </div>
  )
}

// ── Side-by-side view ─────────────────────────────────────────────────────

function SideBySideDiff({
  oldText,
  newText,
  chunks,
  oldLabel,
  newLabel,
}: {
  oldText: string
  newText: string
  chunks: DiffChunk[]
  oldLabel: string
  newLabel: string
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {/* Old (left) */}
      <div>
        <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mb-1 px-1">
          {oldLabel}
        </div>
        <div className="text-[12px] leading-relaxed font-serif p-3 bg-red-50/40 rounded-lg border border-red-200/50 whitespace-pre-wrap break-words">
          {chunks.map((chunk, idx) => {
            if (chunk.op === 'equal') {
              return (
                <span key={idx} className="text-foreground">
                  {chunk.text}
                </span>
              )
            }
            if (chunk.op === 'delete') {
              return (
                <span
                  key={idx}
                  className="bg-red-200 text-red-900 line-through decoration-red-400 rounded-sm"
                >
                  {chunk.text}
                </span>
              )
            }
            return null
          })}
        </div>
      </div>

      {/* New (right) */}
      <div>
        <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mb-1 px-1">
          {newLabel}
        </div>
        <div className="text-[12px] leading-relaxed font-serif p-3 bg-emerald-50/40 rounded-lg border border-emerald-200/50 whitespace-pre-wrap break-words">
          {chunks.map((chunk, idx) => {
            if (chunk.op === 'equal') {
              return (
                <span key={idx} className="text-foreground">
                  {chunk.text}
                </span>
              )
            }
            if (chunk.op === 'insert') {
              return (
                <span
                  key={idx}
                  className="bg-emerald-200 text-emerald-900 rounded-sm"
                >
                  {chunk.text}
                </span>
              )
            }
            return null
          })}
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

interface DiffViewerProps {
  oldText: string
  newText: string
  oldLabel?: string
  newLabel?: string
  defaultMode?: 'unified' | 'sidebyside'
}

export default function DiffViewer({
  oldText,
  newText,
  oldLabel = 'Before',
  newLabel = 'After',
  defaultMode = 'unified',
}: DiffViewerProps) {
  const [mode, setMode] = useState<'unified' | 'sidebyside'>(defaultMode)

  const chunks = useMemo(() => computeWordDiff(oldText, newText), [oldText, newText])

  const insertCount = chunks.filter((c) => c.op === 'insert').length
  const deleteCount = chunks.filter((c) => c.op === 'delete').length

  return (
    <div className="space-y-2">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          {insertCount > 0 && (
            <span className="flex items-center gap-1 text-emerald-700 font-semibold">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
              +{insertCount} added
            </span>
          )}
          {deleteCount > 0 && (
            <span className="flex items-center gap-1 text-red-700 font-semibold">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
              -{deleteCount} removed
            </span>
          )}
          {insertCount === 0 && deleteCount === 0 && (
            <span className="text-muted-foreground">No changes</span>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant={mode === 'unified' ? 'secondary' : 'ghost'}
            className="h-6 w-6 p-0"
            onClick={() => setMode('unified')}
            title="Unified view"
          >
            <AlignLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant={mode === 'sidebyside' ? 'secondary' : 'ghost'}
            className="h-6 w-6 p-0"
            onClick={() => setMode('sidebyside')}
            title="Side-by-side view"
          >
            <Columns2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Diff content */}
      {mode === 'unified' ? (
        <UnifiedDiff chunks={chunks} />
      ) : (
        <SideBySideDiff
          oldText={oldText}
          newText={newText}
          chunks={chunks}
          oldLabel={oldLabel}
          newLabel={newLabel}
        />
      )}
    </div>
  )
}
