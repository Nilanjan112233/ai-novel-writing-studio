"use client"

import { useEffect, useState } from 'react'
import { ChevronRight, Lightbulb } from 'lucide-react'

import { dataApi } from '@/lib/api'
import type { WorkspaceRecommendation } from '@/types'


export default function WorkspaceIntelligenceBanner({
  projectId,
  surface,
  onExplain,
  onNavigate,
}: {
  projectId: string
  surface: string
  onExplain: () => void
  onNavigate?: (destination: string) => void
}) {
  const [recommendation, setRecommendation] = useState<WorkspaceRecommendation | null>(null)

  useEffect(() => {
    let active = true
    dataApi.getWorkspaceIntelligence(projectId, { surface })
      .then((result) => {
        if (active) setRecommendation(result.recommendations?.[0] || null)
      })
      .catch(() => {
        if (active) setRecommendation(null)
      })
    return () => { active = false }
  }, [projectId, surface])

  if (!recommendation) return null
  return (
    <aside
      className="mx-3 mt-3 flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-sm sm:mx-6"
      data-testid="workspace-intelligence-banner"
    >
      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
          <p className="font-medium">Story guidance</p>
        <p className="break-words text-xs text-muted-foreground">{recommendation.message}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          {recommendation.affected_chapters.length
            ? `Chapters ${recommendation.affected_chapters.join(', ')}`
            : 'Project-wide evidence'}
          {recommendation.affected_scenes.length ? ` · ${recommendation.affected_scenes.length} scenes` : ''}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1"><button type="button" onClick={onExplain} className="flex items-center gap-1 text-xs font-medium text-primary hover:underline">Explain <ChevronRight className="h-3 w-3" /></button>{onNavigate ? <button type="button" onClick={() => onNavigate(recommendation.destination || 'story-health')} className="text-xs font-semibold text-primary hover:underline">Review now</button> : null}</div>
    </aside>
  )
}
