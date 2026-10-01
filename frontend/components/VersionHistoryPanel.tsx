'use client'

/**
 * VersionHistoryPanel — Phase 5B
 *
 * Sidebar panel showing the full version timeline for a paragraph.
 * - Type badges: manual, autosave, ai_suggestion, restore, approval, lock, system
 * - Inline prose diff preview when a version is selected
 * - Restore action with two-step confirmation
 */

import { useCallback, useEffect, useState } from 'react'
import {
  History,
  RotateCcw,
  Eye,
  Loader2,
  ChevronRight,
  GitCommit,
  Bot,
  User,
  Shield,
  Lock,
  RefreshCw,
  Save,
  Clock,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/store/projectStore'
import DiffViewer from './DiffViewer'
import type { ParagraphVersion } from '@/types'

// ── Version classification ──────────────────────────────────────────────────

function classifyVersion(v: ParagraphVersion): {
  label: string
  color: string
  icon: React.ReactNode
  short: string
} {
  const reason = (v.change_reason || '').toLowerCase()

  if (reason.includes('autosave') || reason === '') {
    return {
      label: 'Autosave',
      short: 'auto',
      color: 'bg-slate-100 text-slate-600 border-slate-200',
      icon: <Save className="h-3 w-3" />,
    }
  }
  if (reason.includes('manual') || reason.includes('user save')) {
    return {
      label: 'Manual Save',
      short: 'manual',
      color: 'bg-blue-100 text-blue-700 border-blue-200',
      icon: <User className="h-3 w-3" />,
    }
  }
  if (
    reason.includes('ai edit') ||
    reason.includes('ai suggestion') ||
    reason.includes('accepted')
  ) {
    return {
      label: 'AI Edit',
      short: 'ai',
      color: 'bg-violet-100 text-violet-700 border-violet-200',
      icon: <Bot className="h-3 w-3" />,
    }
  }
  if (reason.includes('pre-restore') || reason.includes('restore')) {
    return {
      label: 'Restore',
      short: 'restore',
      color: 'bg-amber-100 text-amber-700 border-amber-200',
      icon: <RotateCcw className="h-3 w-3" />,
    }
  }
  if (reason.includes('approved') || reason.includes('approval')) {
    return {
      label: 'Approval',
      short: 'approval',
      color: 'bg-emerald-100 text-emerald-700 border-emerald-200',
      icon: <Shield className="h-3 w-3" />,
    }
  }
  if (reason.includes('lock')) {
    return {
      label: 'Lock',
      short: 'lock',
      color: 'bg-violet-100 text-violet-700 border-violet-200',
      icon: <Lock className="h-3 w-3" />,
    }
  }
  return {
    label: 'System',
    short: 'sys',
    color: 'bg-muted text-muted-foreground border-border',
    icon: <GitCommit className="h-3 w-3" />,
  }
}

function formatRelTime(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const s = Math.floor(diff / 1000)
    if (s < 60) return `${s}s ago`
    const m = Math.floor(s / 60)
    if (m < 60) return `${m}m ago`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h}h ago`
    const d = Math.floor(h / 24)
    return `${d}d ago`
  } catch {
    return ''
  }
}

// ── Main component ──────────────────────────────────────────────────────────

interface VersionHistoryPanelProps {
  projectId: string
  sceneId: string
  paragraphId: string
  paragraphVersion?: number
  currentProse: string
}

export default function VersionHistoryPanel({
  projectId,
  sceneId,
  paragraphId,
  paragraphVersion,
  currentProse,
}: VersionHistoryPanelProps) {
  const {
    versionHistory,
    isVersionHistoryLoading,
    fetchVersionHistory,
    restoreVersion,
  } = useProjectStore()

  const versions = versionHistory[paragraphId] || []
  const [selectedVersion, setSelectedVersion] = useState<ParagraphVersion | null>(null)
  const [showDiff, setShowDiff] = useState(false)
  const [confirmRestore, setConfirmRestore] = useState<string | null>(null)
  const [isRestoring, setIsRestoring] = useState(false)

  useEffect(() => {
    void fetchVersionHistory(projectId, sceneId, paragraphId)
    setSelectedVersion(null)
    setShowDiff(false)
    setConfirmRestore(null)
  }, [paragraphId, projectId, sceneId, fetchVersionHistory, paragraphVersion])

  const handleRestore = useCallback(
    async (versionId: string) => {
      if (confirmRestore !== versionId) {
        setConfirmRestore(versionId)
        return
      }
      setIsRestoring(true)
      try {
        await restoreVersion(projectId, sceneId, paragraphId, versionId)
        await fetchVersionHistory(projectId, sceneId, paragraphId)
        setSelectedVersion(null)
        setShowDiff(false)
      } finally {
        setIsRestoring(false)
        setConfirmRestore(null)
      }
    },
    [confirmRestore, projectId, sceneId, paragraphId, restoreVersion, fetchVersionHistory]
  )

  // ── Loading state ─────────────────────────────────────────────────────────

  if (isVersionHistoryLoading && versions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
        <span className="text-xs">Loading version history…</span>
      </div>
    )
  }

  if (versions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground px-4 text-center">
        <History className="h-8 w-8 text-muted-foreground/40" />
        <p className="text-xs leading-relaxed">
          No saved versions yet. Manually saving or accepting an AI suggestion creates a version
          entry.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Diff viewer pane */}
      {showDiff && selectedVersion && (
        <div className="border-b bg-background px-3 pt-3 pb-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Diff — v{selectedVersion.version_number} vs Current
            </span>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-[10px] text-muted-foreground hover:text-foreground"
              onClick={() => setShowDiff(false)}
            >
              Close
            </Button>
          </div>
          <DiffViewer
            oldText={selectedVersion.snapshot.prose || ''}
            newText={currentProse}
            oldLabel={`v${selectedVersion.version_number}`}
            newLabel="Current"
          />
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/10 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <History className="h-3.5 w-3.5" />
          {versions.length} version{versions.length !== 1 ? 's' : ''}
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
          onClick={() => fetchVersionHistory(projectId, sceneId, paragraphId)}
          title="Refresh history"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto">
        {versions.map((v, idx) => {
          const isFirst = idx === 0
          const meta = classifyVersion(v)
          const isSelected = selectedVersion?.version_id === v.version_id
          const wordCount =
            v.snapshot.word_count ??
            (v.snapshot.prose?.split(/\s+/).filter(Boolean).length ?? 0)
          const isConfirming = confirmRestore === v.version_id

          return (
            <div
              key={v.version_id}
              className={`relative border-b transition-colors cursor-pointer group ${
                isSelected
                  ? 'bg-primary/5 border-l-2 border-l-primary/40'
                  : 'hover:bg-muted/20 border-l-2 border-l-transparent'
              }`}
              onClick={() => {
                setSelectedVersion(isSelected ? null : v)
                if (isSelected) setShowDiff(false)
              }}
            >
              <div className="flex items-start gap-2.5 px-3 py-2.5">
                {/* Version dot */}
                <div
                  className={`mt-0.5 h-5 w-5 rounded-full flex items-center justify-center shrink-0 border transition-colors ${
                    isFirst
                      ? 'bg-primary/10 border-primary/30'
                      : 'bg-muted/60 border-border group-hover:bg-muted'
                  }`}
                >
                  {isFirst ? (
                    <div className="h-2 w-2 rounded-full bg-primary" />
                  ) : (
                    <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                    <span
                      className={`inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded border ${meta.color}`}
                    >
                      {meta.icon}
                      {meta.short}
                    </span>

                    {isFirst && (
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                        latest
                      </span>
                    )}

                    <span className="text-[10px] font-bold text-foreground ml-auto">
                      v{v.version_number}
                    </span>
                  </div>

                  {v.change_reason && (
                    <p className="text-[11px] text-foreground font-medium leading-snug truncate">
                      {v.change_reason}
                    </p>
                  )}

                  <div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground flex-wrap">
                    <Clock className="h-3 w-3 shrink-0" />
                    <span>{formatRelTime(v.created_at)}</span>
                    {v.created_by && (
                      <>
                        <span>·</span>
                        <span className="font-medium">{v.created_by}</span>
                      </>
                    )}
                    {wordCount > 0 && (
                      <>
                        <span>·</span>
                        <span>{wordCount}w</span>
                      </>
                    )}
                  </div>

                  {/* Expanded actions */}
                  {isSelected && (
                    <div
                      className="flex items-center gap-1.5 mt-2"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-[10px] gap-1"
                        onClick={() => setShowDiff((prev) => !prev)}
                      >
                        <Eye className="h-3 w-3" />
                        {showDiff ? 'Hide Diff' : 'View Diff'}
                      </Button>

                      {!isFirst && (
                        <Button
                          size="sm"
                          variant={isConfirming ? 'destructive' : 'outline'}
                          className="h-6 px-2 text-[10px] gap-1"
                          disabled={isRestoring}
                          onClick={() => void handleRestore(v.version_id)}
                        >
                          {isRestoring ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <RotateCcw className="h-3 w-3" />
                          )}
                          {isConfirming ? 'Confirm' : 'Restore'}
                        </Button>
                      )}

                      {isConfirming && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-[10px] text-muted-foreground"
                          onClick={() => setConfirmRestore(null)}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  )}
                </div>

                <ChevronRight
                  className={`h-3.5 w-3.5 text-muted-foreground/40 mt-0.5 shrink-0 transition-transform ${
                    isSelected ? 'rotate-90' : ''
                  }`}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
