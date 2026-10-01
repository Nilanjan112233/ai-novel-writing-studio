'use client'

import { useState, useEffect } from 'react'
import { 
  Sparkles, 
  Check, 
  X, 
  RefreshCw, 
  ChevronRight, 
  BookOpen, 
  User, 
  Info, 
  Loader2, 
  AlertCircle, 
  Cpu, 
  History,
  AlignLeft,
  MessageSquare,
  TrendingUp,
  Heart,
  Wand2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/store/projectStore'
import type { ParagraphSuggestion, ParagraphSkeleton } from '@/types'

interface AiSuggestionPanelProps {
  projectId: string
  sceneId: string
  paragraphId: string
  paragraph: ParagraphSkeleton
  devMode: boolean
}

export default function AiSuggestionPanel({
  projectId,
  sceneId,
  paragraphId,
  paragraph,
  devMode,
}: AiSuggestionPanelProps) {
  const {
    suggestions,
    isSuggestionsLoading,
    fetchParagraphSuggestions,
    triggerAiEdit,
    acceptParagraphSuggestion,
    rejectParagraphSuggestion,
    paragraphContents,
  } = useProjectStore()

  const currentProse = paragraphContents[paragraphId]?.prose || ''

  // Selected suggestion to inspect (defaults to the first pending one if available)
  const [selectedSuggestionId, setSelectedSuggestionId] = useState<string | null>(null)
  const [customPrompt, setCustomPrompt] = useState('')
  const [activeCategory, setActiveCategory] = useState<'writing' | 'dialogue' | 'style' | 'emotion' | 'pacing'>('writing')

  useEffect(() => {
    void fetchParagraphSuggestions(projectId, sceneId, paragraphId)
  }, [projectId, sceneId, paragraphId, fetchParagraphSuggestions])

  // Select the first pending suggestion by default
  const pendingSuggestions = suggestions.filter((s) => s.status === 'pending')
  const activeSuggestion = suggestions.find((s) => s.suggestion_id === selectedSuggestionId) || pendingSuggestions[0]

  useEffect(() => {
    if (pendingSuggestions.length > 0 && !selectedSuggestionId) {
      setSelectedSuggestionId(pendingSuggestions[0].suggestion_id)
    }
  }, [suggestions, pendingSuggestions, selectedSuggestionId])

  const handleAction = async (mode: string) => {
    await triggerAiEdit(projectId, sceneId, paragraphId, mode, customPrompt)
    setCustomPrompt('')
  }

  // Categories of writing actions
  const categories = {
    writing: {
      label: 'Drafting & Flow',
      icon: <AlignLeft className="h-3.5 w-3.5" />,
      actions: [
        { mode: 'expand', label: 'Expand Prose', description: 'Flesh out narrative details and imagery.' },
        { mode: 'shorten', label: 'Shorten Prose', description: 'Tighten wording and remove redundancy.' },
      ]
    },
    dialogue: {
      label: 'Dialogue & Subtext',
      icon: <MessageSquare className="h-3.5 w-3.5" />,
      actions: [
        { mode: 'dialogue', label: 'Polish Dialogue', description: 'Inject voice distinctiveness and subtext.' },
      ]
    },
    style: {
      label: 'Style & Prose',
      icon: <Wand2 className="h-3.5 w-3.5" />,
      actions: [
        { mode: 'rewrite', label: 'General Rewrite', description: 'Restructure prose for better aesthetic flow.' },
      ]
    },
    emotion: {
      label: 'Emotion & Focus',
      icon: <Heart className="h-3.5 w-3.5" />,
      actions: [
        { mode: 'tone', label: 'Shift Emotion', description: 'Accentuate planned character emotional states.' },
      ]
    },
    pacing: {
      label: 'Pacing & Suspense',
      icon: <TrendingUp className="h-3.5 w-3.5" />,
      actions: [
        { mode: 'rewrite', label: 'Pacing Polish', description: 'Adjust sentence cadence to modulate tempo.' },
      ]
    }
  }

  return (
    <div className="flex flex-col h-full text-xs">
      
      {/* 1. INLINE AI ACTIONS BAR */}
      <div className="p-3 border-b bg-muted/5 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-primary animate-pulse" />
            Writing Assistant Tools
          </span>
        </div>

        {/* Categories Tabs */}
        <div className="flex border rounded overflow-hidden">
          {(Object.keys(categories) as Array<keyof typeof categories>).map((key) => {
            const cat = categories[key]
            const active = activeCategory === key
            return (
              <button
                key={key}
                onClick={() => setActiveCategory(key)}
                className={`flex-1 py-1.5 flex flex-col items-center gap-0.5 border-r last:border-r-0 transition-colors text-[9px] font-semibold ${
                  active ? 'bg-primary/10 text-primary' : 'bg-background hover:bg-muted/40 text-muted-foreground'
                }`}
                title={cat.label}
              >
                {cat.icon}
                <span className="capitalize">{key}</span>
              </button>
            )
          })}
        </div>

        {/* Selected Category Action list */}
        <div className="bg-background rounded border p-2 space-y-2">
          <div className="grid grid-cols-2 gap-1.5">
            {categories[activeCategory].actions.map((act) => (
              <Button
                key={act.mode}
                size="sm"
                variant="outline"
                onClick={() => handleAction(act.mode)}
                disabled={isSuggestionsLoading}
                className="h-7 text-[10px] font-bold gap-1 flex items-center justify-center border-primary/20 hover:bg-primary/5 hover:text-primary transition-all active:scale-[0.98]"
              >
                <Sparkles className="h-3 w-3 shrink-0" />
                {act.label}
              </Button>
            ))}
          </div>
          
          {/* Custom prompt entry */}
          <div className="space-y-1">
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Inject custom specifications (e.g. 'Make it suspenseful', 'focus on sensory detail')..."
              className="w-full h-11 px-2.5 py-1 text-[11px] rounded border bg-background/50 text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary/20 leading-normal resize-none"
            />
          </div>
        </div>
      </div>

      {/* Suggestion Loading Spinner */}
      {isSuggestionsLoading && (
        <div className="flex items-center justify-center py-4 bg-primary/5 border-b text-[11px] text-primary/80 font-medium gap-1.5 animate-pulse">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Generating AI Suggestion proposal...</span>
        </div>
      )}

      {/* 2. MAIN PREVIEW AREA (Active Suggestion) */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3.5">
        {activeSuggestion ? (
          <div className="space-y-3.5" data-testid="suggestion-inspection-area">
            
            {/* Suggestion Identity Banner */}
            <div className="flex items-center justify-between bg-primary/5 border border-primary/10 rounded px-2 py-1 text-[10px] font-semibold text-primary">
              <span className="capitalize flex items-center gap-1">
                <span>🤖</span> Proposed {activeSuggestion.suggestion_type} Suggestion
              </span>
              <span className="text-muted-foreground uppercase text-[9px] tracking-wide">
                Status: {activeSuggestion.status}
              </span>
            </div>

            {/* Structured Explanation Box */}
            <div className="space-y-2">
              <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5" />
                Assistant Reasoning
              </h4>
              <div className="bg-background border rounded-lg p-2.5 space-y-2 leading-relaxed text-[11px]">
                <div>
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block">Editing Goal</span>
                  <strong className="text-foreground">{activeSuggestion.explanation?.editing_goal || 'Apply prose adjustments'}</strong>
                </div>
                <div>
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block">Reasoning Logic</span>
                  <p className="text-muted-foreground mt-0.5">{activeSuggestion.explanation?.reasoning || 'Polished flow of prose to match scene guidelines.'}</p>
                </div>
                <div>
                  <span className="text-[9px] text-muted-foreground font-semibold uppercase block">Summary of Changes</span>
                  <p className="text-muted-foreground mt-0.5">{activeSuggestion.explanation?.summary_of_changes || 'Refructured active paragraph sentences.'}</p>
                </div>
                {activeSuggestion.explanation?.trade_offs && (
                  <div>
                    <span className="text-[9px] text-muted-foreground font-semibold uppercase block">Potential Trade-offs</span>
                    <p className="text-muted-foreground mt-0.5">{activeSuggestion.explanation.trade_offs}</p>
                  </div>
                )}
                {activeSuggestion.explanation?.confidence && (
                  <div className="flex items-center gap-1 pt-1.5 border-t">
                    <span className="text-[9px] text-muted-foreground font-semibold uppercase">Confidence Score:</span>
                    <span className="bg-emerald-50 text-emerald-800 font-bold border border-emerald-100 rounded px-1.5 py-0.5 text-[10px]">
                      {activeSuggestion.explanation.confidence}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Side-by-side or stacked diff view */}
            <div className="space-y-2">
              <h4 className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground">
                Prose Comparison
              </h4>
              <div className="grid grid-cols-1 gap-2 leading-relaxed text-[11px]">
                {/* Current prose block */}
                <div className="bg-muted/10 border rounded p-2.5">
                  <span className="text-[9px] font-bold text-muted-foreground uppercase block mb-1">Current Prose</span>
                  <p className="text-muted-foreground italic line-clamp-4">{currentProse || '— (No active prose written yet)'}</p>
                </div>
                {/* Proposed suggestion block */}
                <div className="bg-emerald-50/20 border border-emerald-200 rounded p-2.5">
                  <span className="text-[9px] font-bold text-emerald-800 uppercase block mb-1">Proposed Assistant Suggestion</span>
                  <p className="text-foreground leading-normal font-medium">{activeSuggestion.proposed_prose}</p>
                </div>
              </div>
            </div>

            {/* Provider and prompt version metadata */}
            {devMode && activeSuggestion.generation_metadata && (
              <div className="space-y-1.5 border-t pt-2 border-primary/10">
                <span className="font-bold text-[9px] uppercase tracking-wide text-primary flex items-center gap-1.5">
                  <Cpu className="h-3 w-3" />
                  Provider Metadata (Developer Mode)
                </span>
                <div className="p-2 border rounded font-mono text-[9px] bg-muted/10 text-muted-foreground space-y-1">
                  <div className="flex justify-between">
                    <span>Prompt Template:</span>
                    <span className="text-foreground font-semibold">{activeSuggestion.generation_metadata.prompt_template || 'edit'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Prompt Version:</span>
                    <span className="text-foreground font-semibold">{activeSuggestion.generation_metadata.prompt_version || 'v1'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Model Settings:</span>
                    <span className="text-foreground font-semibold">{activeSuggestion.model} (t={activeSuggestion.generation_metadata.temperature || 0.7})</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Duration / Latency:</span>
                    <span className="text-foreground font-semibold">{activeSuggestion.generation_metadata.latency_ms}ms</span>
                  </div>
                  {activeSuggestion.generation_metadata.estimated_cost !== undefined && (
                    <div className="flex justify-between">
                      <span>Estimated Cost:</span>
                      <span className="text-foreground font-semibold">${activeSuggestion.generation_metadata.estimated_cost.toFixed(6)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Action buttons (Accept, Reject, Regenerate) */}
            {activeSuggestion.status === 'pending' && (
              <div className="flex items-center gap-2 pt-2 border-t">
                <Button
                  size="sm"
                  variant="default"
                  onClick={async () => {
                    await acceptParagraphSuggestion(projectId, sceneId, paragraphId, activeSuggestion.suggestion_id)
                    setSelectedSuggestionId(null)
                  }}
                  className="flex-1 h-8 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 text-xs font-bold shadow-sm"
                  data-testid="accept-suggestion-btn"
                >
                  <Check className="h-4 w-4" />
                  Accept
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    await rejectParagraphSuggestion(projectId, sceneId, paragraphId, activeSuggestion.suggestion_id)
                  }}
                  className="h-8 border-rose-200 text-rose-700 hover:bg-rose-50 hover:text-rose-800 gap-1.5 text-xs font-bold"
                  data-testid="reject-suggestion-btn"
                >
                  <X className="h-4 w-4" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleAction(activeSuggestion.suggestion_type)}
                  className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground font-semibold"
                  title="Regenerate proposal"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Regenerate
                </Button>
              </div>
            )}

          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-center text-muted-foreground space-y-2">
            <div className="p-3 bg-muted rounded-full">
              <Sparkles className="h-6 w-6 text-muted-foreground/60" />
            </div>
            <span className="font-semibold text-foreground text-xs">No active suggestions</span>
            <p className="max-w-xs text-[10px] leading-relaxed">
              Use the assistant tools at the top to generate a prose proposal. Suggestions will accumulate below without overwriting your draft.
            </p>
          </div>
        )}
      </div>

      {/* 3. SUGGESTION HISTORY LEDGER */}
      <div className="p-3 border-t bg-muted/5 space-y-2">
        <span className="font-bold text-[10px] uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
          <History className="h-3.5 w-3.5 text-muted-foreground" />
          Suggestion Ledger History ({suggestions.length})
        </span>

        {suggestions.length > 0 ? (
          <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
            {suggestions.map((s) => {
              const active = s.suggestion_id === (activeSuggestion?.suggestion_id || '')
              return (
                <button
                  key={s.suggestion_id}
                  onClick={() => setSelectedSuggestionId(s.suggestion_id)}
                  className={`w-full flex items-center justify-between p-2 rounded border text-left text-[10px] font-medium leading-none transition-all ${
                    active 
                      ? 'bg-primary/5 border-primary/20 text-foreground ring-1 ring-primary/20' 
                      : 'bg-background hover:bg-muted/40 border-transparent text-muted-foreground'
                  }`}
                >
                  <div className="flex items-center gap-1.5 truncate">
                    <ChevronRight className={`h-3 w-3 shrink-0 text-muted-foreground transition-transform ${active ? 'rotate-90' : ''}`} />
                    <span className="capitalize font-semibold text-foreground">{s.suggestion_type}</span>
                    <span className="truncate opacity-75 font-normal">({s.proposed_prose.slice(0, 25)}...)</span>
                  </div>
                  
                  {/* Status Indicator */}
                  <span className={`text-[8px] px-1.5 py-0.5 rounded-full border shrink-0 font-bold uppercase ${
                    s.status === 'accepted' ? 'bg-emerald-100 text-emerald-800 border-emerald-200' :
                    s.status === 'rejected' ? 'bg-slate-100 text-slate-700 border-slate-200' :
                    'bg-amber-100 text-amber-800 border-amber-200'
                  }`}>
                    {s.status}
                  </span>
                </button>
              )
            })}
          </div>
        ) : (
          <div className="text-[10px] text-center text-muted-foreground py-2 italic">
            No history entries yet.
          </div>
        )}
      </div>

    </div>
  )
}
