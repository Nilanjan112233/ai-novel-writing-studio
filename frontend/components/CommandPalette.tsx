'use client'

/**
 * CommandPalette — Phase 5B
 *
 * Cmd/Ctrl+K command palette for keyboard-driven navigation.
 * - Fuzzy search over commands
 * - Navigate to paragraphs by number
 * - Toggle focus/inspector/assistant/history/comments panels
 * - Common editor actions
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Search,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  MessageSquare,
  History,
  Sparkles,
  Eye,
  Save,
  BarChart2,
  X,
} from 'lucide-react'

// ── Command registry ───────────────────────────────────────────────────────

type CommandCategory = 'navigate' | 'panels' | 'editor' | 'view'

interface Command {
  id: string
  label: string
  description?: string
  category: CommandCategory
  icon: React.ReactNode
  shortcut?: string
  action: () => void
}

const CATEGORY_LABELS: Record<CommandCategory, string> = {
  navigate: 'Navigation',
  panels: 'Panels',
  editor: 'Editor',
  view: 'View',
}

function fuzzyMatch(query: string, target: string): boolean {
  const q = query.toLowerCase()
  const t = target.toLowerCase()
  let qi = 0
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++
  }
  return qi === q.length
}

// ── Main component ─────────────────────────────────────────────────────────

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  paragraphCount: number
  activeParagraphIndex: number
  onNavigate: (idx: number) => void
  onToggleFocus: () => void
  onToggleOutline: () => void
  onToggleInspector: () => void
  onSwitchTab: (tab: 'inspector' | 'suggestions' | 'history' | 'comments' | 'analytics') => void
  onManualSave: () => void
  onToggleDevMode: () => void
}

export default function CommandPalette({
  isOpen,
  onClose,
  paragraphCount,
  activeParagraphIndex,
  onNavigate,
  onToggleFocus,
  onToggleOutline,
  onToggleInspector,
  onSwitchTab,
  onManualSave,
  onToggleDevMode,
}: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Scroll active item into view
  useEffect(() => {
    const selectedEl = listRef.current?.querySelector('[data-selected="true"]')
    if (selectedEl) {
      selectedEl.scrollIntoView({
        block: 'nearest',
      })
    }
  }, [selectedIdx])

  // Build dynamic commands
  const commands: Command[] = [
    {
      id: 'prev-para',
      label: 'Previous Paragraph',
      category: 'navigate',
      icon: <ArrowLeft className="h-3.5 w-3.5" />,
      shortcut: '←',
      action: () => {
        if (activeParagraphIndex > 0) onNavigate(activeParagraphIndex - 1)
      },
    },
    {
      id: 'next-para',
      label: 'Next Paragraph',
      category: 'navigate',
      icon: <ArrowRight className="h-3.5 w-3.5" />,
      shortcut: '→',
      action: () => {
        if (activeParagraphIndex < paragraphCount - 1) onNavigate(activeParagraphIndex + 1)
      },
    },
    // Dynamic: jump to paragraph N
    ...Array.from({ length: paragraphCount }, (_, i) => ({
      id: `goto-para-${i + 1}`,
      label: `Go to Paragraph ${i + 1}`,
      description: `Jump to ¶${i + 1}`,
      category: 'navigate' as CommandCategory,
      icon: <BookOpen className="h-3.5 w-3.5" />,
      action: () => onNavigate(i),
    })),
    {
      id: 'toggle-focus',
      label: 'Toggle Focus Mode',
      description: 'Collapse all panels for distraction-free writing',
      category: 'view',
      icon: <Eye className="h-3.5 w-3.5" />,
      shortcut: 'F',
      action: onToggleFocus,
    },
    {
      id: 'toggle-outline',
      label: 'Toggle Outline Panel',
      category: 'panels',
      icon: <BookOpen className="h-3.5 w-3.5" />,
      action: onToggleOutline,
    },
    {
      id: 'toggle-inspector',
      label: 'Toggle Inspector Panel',
      category: 'panels',
      icon: <BookOpen className="h-3.5 w-3.5" />,
      action: onToggleInspector,
    },
    {
      id: 'show-inspector',
      label: 'Show Narrative Inspector',
      category: 'panels',
      icon: <BookOpen className="h-3.5 w-3.5" />,
      action: () => onSwitchTab('inspector'),
    },
    {
      id: 'show-assistant',
      label: 'Show Writing Assistant',
      category: 'panels',
      icon: <Sparkles className="h-3.5 w-3.5" />,
      action: () => onSwitchTab('suggestions'),
    },
    {
      id: 'show-history',
      label: 'Show Version History',
      category: 'panels',
      icon: <History className="h-3.5 w-3.5" />,
      action: () => onSwitchTab('history'),
    },
    {
      id: 'show-comments',
      label: 'Show Comments',
      category: 'panels',
      icon: <MessageSquare className="h-3.5 w-3.5" />,
      action: () => onSwitchTab('comments'),
    },
    {
      id: 'show-analytics',
      label: 'Show Writing Analytics',
      category: 'panels',
      icon: <BarChart2 className="h-3.5 w-3.5" />,
      action: () => onSwitchTab('analytics'),
    },
    {
      id: 'manual-save',
      label: 'Save Version',
      description: 'Create a named checkpoint of the current prose',
      category: 'editor',
      icon: <Save className="h-3.5 w-3.5" />,
      shortcut: 'Ctrl+S',
      action: onManualSave,
    },
    {
      id: 'toggle-devmode',
      label: 'Toggle Developer Mode',
      description: 'Show performance diagnostics and telemetry',
      category: 'view',
      icon: <Eye className="h-3.5 w-3.5" />,
      shortcut: 'Ctrl+Alt+Shift+D',
      action: onToggleDevMode,
    },
  ]

  const filtered = query.trim()
    ? commands.filter((c) => fuzzyMatch(query, c.label) || fuzzyMatch(query, c.description || ''))
    : commands.slice(0, 20)

  // Group by category
  const grouped = filtered.reduce<Record<string, Command[]>>((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = []
    acc[cmd.category].push(cmd)
    return acc
  }, {})

  const flatFiltered = filtered

  useEffect(() => {
    setSelectedIdx(0)
  }, [query])

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
      setQuery('')
      setSelectedIdx(0)
    }
  }, [isOpen])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIdx((i) => Math.min(i + 1, flatFiltered.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIdx((i) => Math.max(i - 1, 0))
        return
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        const cmd = flatFiltered[selectedIdx]
        if (cmd) {
          cmd.action()
          onClose()
        }
      }
    },
    [flatFiltered, selectedIdx, onClose]
  )

  if (!isOpen) return null

  let globalIdx = -1

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4"
      data-testid="command-palette-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="command-palette-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative z-10 w-full max-w-xl rounded-xl border bg-card shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-200"
        data-testid="command-palette"
      >
        <h2 id="command-palette-title" className="sr-only">Command Palette</h2>

        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search commands…"
            role="combobox"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-controls="command-palette-results"
            className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
            data-testid="command-palette-input"
          />
          <button
            onClick={onClose}
            aria-label="Close command palette"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results */}
        <div
          ref={listRef}
          id="command-palette-results"
          role="listbox"
          aria-label="Command results"
          className="max-h-[60vh] overflow-y-auto py-2"
        >
          {flatFiltered.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No commands found for &ldquo;{query}&rdquo;
            </div>
          )}

          {Object.entries(grouped).map(([category, cmds]) => (
            <div key={category}>
              <div className="px-4 py-1.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground/60">
                {CATEGORY_LABELS[category as CommandCategory] || category}
              </div>
              {cmds.map((cmd) => {
                globalIdx++
                const isSelected = globalIdx === selectedIdx
                return (
                  <button
                    key={cmd.id}
                    role="option"
                    aria-selected={isSelected ? 'true' : 'false'}
                    data-selected={isSelected ? 'true' : 'false'}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                      isSelected ? 'bg-primary/5 text-foreground' : 'hover:bg-muted/30 text-foreground'
                    }`}
                    onClick={() => {
                      cmd.action()
                      onClose()
                    }}
                    onMouseEnter={() => setSelectedIdx(globalIdx)}
                  >
                    <span
                      className={`shrink-0 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`}
                    >
                      {cmd.icon}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="text-[13px] font-medium block truncate">{cmd.label}</span>
                      {cmd.description && (
                        <span className="text-[11px] text-muted-foreground block truncate">
                          {cmd.description}
                        </span>
                      )}
                    </span>
                    {cmd.shortcut && (
                      <span className="text-[10px] font-mono text-muted-foreground bg-muted/50 border rounded px-1.5 py-0.5 shrink-0">
                        {cmd.shortcut}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 px-4 py-2 border-t bg-muted/5 text-[10px] text-muted-foreground">
          <span>↑↓ navigate</span>
          <span>·</span>
          <span>↵ execute</span>
          <span>·</span>
          <span>Esc close</span>
        </div>
      </div>
    </div>
  )
}
