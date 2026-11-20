"use client"

// The frame around every project screen: a sidebar with the guided path,
// a top bar that always shows how far the book is, tabs for the sections of
// the current step, and a footer that points to the next step.

import Link from 'next/link'
import type { ReactNode } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Cpu,
  Home,
  Menu,
  MessageCircle,
  Settings,
  Wrench,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ProgressBar } from '@/components/ui/page'
import ThemeToggle from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'
import { GUIDED_STEPS, STEPS, nextGuidedStep, stepById, type StepId, type StepInfo } from '@/lib/workspaceNav'
import { STAGE_LABELS, type BookProgress } from '@/lib/bookProgress'

type Navigate = (sectionId: string) => void

function stepIsCurrent(step: StepInfo, progress: BookProgress) {
  if (progress.stage === 'done') return false
  return step.id === progress.stage
}

export function WorkspaceSidebar({
  projectName,
  activeStep,
  activeSection,
  progress,
  badges,
  moreOpen,
  onToggleMore,
  onStep,
  onNavigate,
  mobileOpen,
  onCloseMobile,
}: {
  projectName: string
  activeStep: StepId
  activeSection: string
  progress: BookProgress
  badges: Partial<Record<StepId, number>>
  moreOpen: boolean
  onToggleMore: () => void
  onStep: (step: StepId) => void
  onNavigate: Navigate
  mobileOpen: boolean
  onCloseMobile: () => void
}) {
  const more = stepById('more')
  const itemClass = (active: boolean) => cn(
    'group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
    active ? 'bg-primary/10 font-medium text-primary' : 'text-muted-foreground hover:bg-accent hover:text-foreground',
  )
  return (
    <>
      {mobileOpen ? <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={onCloseMobile} aria-hidden="true" /> : null}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r bg-sidebar transition-transform lg:static lg:translate-x-0',
          mobileOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full',
        )}
        data-testid="workspace-sidebar"
        aria-label="Project navigation"
      >
        <div className="border-b px-4 pb-4 pt-4">
          <div className="flex items-center justify-between">
            <Link href="/projects" className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground" data-testid="back-to-projects">
              <ArrowLeft className="h-3.5 w-3.5" />All projects
            </Link>
            <button type="button" className="rounded p-1 text-muted-foreground hover:bg-accent lg:hidden" onClick={onCloseMobile} aria-label="Close navigation"><X className="h-4 w-4" /></button>
          </div>
          <p className="mt-3 line-clamp-2 text-[15px] font-semibold leading-snug" title={projectName}>{projectName}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{STAGE_LABELS[progress.stage]}{progress.words ? ` · ${progress.words.toLocaleString()} words` : ''}</p>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-3">
          <button type="button" className={itemClass(activeStep === 'overview')} onClick={() => onStep('overview')} data-testid="nav-overview" aria-current={activeStep === 'overview' ? 'page' : undefined}>
            <Home className="h-4 w-4 shrink-0" />Overview
          </button>

          <p className="mb-1 mt-5 px-3 text-xs font-medium text-muted-foreground">Your book</p>
          <ol className="space-y-0.5">
            {GUIDED_STEPS.map((step) => {
              const done = progress.stepsDone[step.id as 'plan' | 'write' | 'review' | 'finish']
              const current = stepIsCurrent(step, progress)
              const active = activeStep === step.id
              const badge = badges[step.id]
              return (
                <li key={step.id}>
                  <button type="button" className={itemClass(active)} onClick={() => onStep(step.id)} data-testid={`nav-${step.id}`} aria-current={active ? 'page' : undefined}>
                    <span
                      className={cn(
                        'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
                        done ? 'border-success bg-success text-white' : current ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground',
                      )}
                      aria-hidden="true"
                    >
                      {done ? <Check className="h-3.5 w-3.5" /> : step.number}
                    </span>
                    <span className="flex-1">{step.label}</span>
                    {badge ? <span className="rounded-full bg-warning/20 px-2 text-xs font-semibold text-warning" aria-label={`${badge} waiting`}>{badge}</span> : null}
                  </button>
                </li>
              )
            })}
          </ol>

          <div className="mt-5 border-t pt-3">
            <button type="button" className={itemClass(false)} onClick={onToggleMore} aria-expanded={moreOpen} data-testid="nav-more">
              <Wrench className="h-4 w-4 shrink-0" />
              <span className="flex-1">More tools</span>
              <ChevronDown className={cn('h-4 w-4 transition-transform', moreOpen ? 'rotate-180' : '')} />
            </button>
            {moreOpen ? (
              <ul className="mt-1 space-y-0.5 pl-3" data-testid="advanced-tools">
                {more.sections.map((section) => (
                  <li key={section.id}>
                    <button
                      type="button"
                      onClick={() => onNavigate(section.id)}
                      className={cn('w-full rounded-md px-3 py-1.5 text-left text-[13px] transition-colors', activeSection === section.id ? 'bg-accent font-medium text-foreground' : 'text-muted-foreground hover:bg-accent hover:text-foreground')}
                      data-testid={`section-${section.id}`}
                      title={section.description}
                    >
                      {section.label}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </nav>

        <div className="space-y-0.5 border-t px-3 py-3">
          <button type="button" className={itemClass(activeStep === 'settings')} onClick={() => onStep('settings')} data-testid="nav-settings">
            <Settings className="h-4 w-4 shrink-0" />Project settings
          </button>
          <Link href="/settings" className={itemClass(false)} data-testid="nav-ai-settings">
            <Cpu className="h-4 w-4 shrink-0" />AI settings
          </Link>
          <ThemeToggle showLabel className="w-full px-3" />
        </div>
      </aside>
    </>
  )
}

export function BookProgressBar({
  progress,
  onOpenMenu,
  onAsk,
  onStep,
}: {
  progress: BookProgress
  onOpenMenu: () => void
  onAsk: () => void
  onStep: (step: StepId) => void
}) {
  const chapterText = progress.plannedChapters
    ? `${progress.chaptersApproved} of ${progress.plannedChapters} chapters approved`
    : `${progress.chaptersApproved} chapter${progress.chaptersApproved === 1 ? '' : 's'} approved`
  return (
    <div className="flex items-center gap-3 border-b bg-background/95 px-4 py-2.5 backdrop-blur sm:px-6" data-testid="book-progress">
      <button type="button" className="rounded-md p-1.5 text-muted-foreground hover:bg-accent lg:hidden" onClick={onOpenMenu} aria-label="Open navigation" data-testid="open-navigation">
        <Menu className="h-5 w-5" />
      </button>
      <ol className="hidden items-center gap-1 md:flex" aria-label="Book stages">
        {GUIDED_STEPS.map((step, index) => {
          const done = progress.stepsDone[step.id as 'plan' | 'write' | 'review' | 'finish']
          const current = stepIsCurrent(step, progress)
          return (
            <li key={step.id} className="flex items-center gap-1">
              {index > 0 ? <span className="h-px w-4 bg-border" aria-hidden="true" /> : null}
              <button
                type="button"
                onClick={() => onStep(step.id)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
                  current ? 'bg-primary text-primary-foreground' : done ? 'text-success hover:bg-accent' : 'text-muted-foreground hover:bg-accent',
                )}
                aria-current={current ? 'step' : undefined}
              >
                {done ? <Check className="h-3 w-3" /> : null}
                {step.label}
              </button>
            </li>
          )
        })}
      </ol>
      <div className="ml-auto flex min-w-0 items-center gap-4">
        <div className="hidden min-w-0 text-right sm:block">
          <p className="truncate text-xs font-medium" data-testid="book-progress-chapters">{chapterText}</p>
          <p className="truncate text-xs text-muted-foreground" data-testid="book-progress-words">{progress.words.toLocaleString()} words</p>
        </div>
        {progress.percent !== null ? <ProgressBar value={progress.percent} className="hidden w-24 sm:block" label="Chapters approved" /> : null}
        <Button size="sm" variant="outline" onClick={onAsk} data-testid="nav-assistant" className="gap-1.5">
          <MessageCircle className="h-4 w-4" />Ask AI
        </Button>
      </div>
    </div>
  )
}

export function StepTabs({ step, activeSection, onNavigate, counts }: { step: StepInfo; activeSection: string; onNavigate: Navigate; counts?: Record<string, number> }) {
  if (step.sections.length < 2 || step.id === 'more') return null
  return (
    <div className="-mx-1 mt-5 overflow-x-auto border-b" role="tablist" aria-label={`${step.label} sections`}>
      <div className="flex min-w-max gap-1 px-1">
        {step.sections.map((section) => {
          const active = section.id === activeSection
          const count = counts?.[section.id]
          return (
            <button
              key={section.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onNavigate(section.id)}
              className={cn(
                '-mb-px inline-flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm transition-colors',
                active ? 'border-primary font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
              data-testid={`section-${section.id}`}
            >
              {section.label}
              {count ? <span className="rounded-full bg-warning/20 px-1.5 text-xs font-semibold text-warning">{count}</span> : null}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function NextStepFooter({ step, onStep, hint }: { step: StepInfo; onStep: (step: StepId) => void; hint?: ReactNode }) {
  const next = nextGuidedStep(step.id)
  if (!next) return null
  return (
    <div className="mt-8 flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-muted/40 px-5 py-4" data-testid="next-step-footer">
      <div className="min-w-0">
        <p className="text-sm font-medium">Next: {next.title}</p>
        <p className="text-sm text-muted-foreground">{hint || next.description}</p>
      </div>
      <Button variant="outline" onClick={() => onStep(next.id)} className="gap-1.5">
        Go to {next.label}<ArrowRight className="h-4 w-4" />
      </Button>
    </div>
  )
}

export { STEPS }
