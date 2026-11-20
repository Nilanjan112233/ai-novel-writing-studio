"use client"

import { ArrowRight, BookOpen, CheckCircle2, Circle, Feather, Loader2, PenLine, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardTitle, ProgressBar, StatusBadge } from '@/components/ui/page'
import { cn } from '@/lib/utils'
import type { BookProgress, NextStep } from '@/lib/bookProgress'
import type { StepId } from '@/lib/workspaceNav'
import type { Run, WritingState } from '@/types'

export default function BookOverview({
  bookTitle,
  premise,
  progress,
  nextStep,
  counts,
  currentRun,
  busy,
  writingState,
  manuscriptStatus,
  onNavigate,
  onStep,
  onDevelop,
  guidance,
  setup,
}: {
  bookTitle: string
  premise?: string
  progress: BookProgress
  nextStep: NextStep
  counts: { characters: number; arcs: number; threads: number; openQuestions: number }
  currentRun: Run | null
  busy: boolean
  writingState: WritingState | null
  manuscriptStatus?: string | null
  onNavigate: (section: string) => void
  onStep: (step: StepId) => void
  onDevelop: () => void
  guidance?: ReactNode
  /** Step-by-step setup, shown while the plan is still empty. */
  setup?: ReactNode
}) {
  const running = currentRun?.status === 'running' || currentRun?.status === 'queued'
  const completedWork = Number(currentRun?.metadata?.progress_completed || 0)
  const totalWork = Number(currentRun?.metadata?.progress_total || 0)
  const runPercent = totalWork ? Math.min(100, Math.round((completedWork / totalWork) * 100)) : 8
  const runNextStep = () => (nextStep.section ? onNavigate(nextStep.section) : onDevelop())
  const recentChapters = [...(writingState?.chapters ?? [])].sort((a, b) => b.chapter_number - a.chapter_number).slice(0, 4)

  const milestones: Array<{ step: StepId; title: string; detail: string; done: boolean }> = [
    {
      step: 'plan',
      title: 'Plan',
      detail: `${counts.characters} character${counts.characters === 1 ? '' : 's'} · ${counts.threads} plot thread${counts.threads === 1 ? '' : 's'} · ${counts.arcs} arc${counts.arcs === 1 ? '' : 's'}`,
      done: progress.stepsDone.plan,
    },
    {
      step: 'write',
      title: 'Write',
      detail: progress.plannedChapters
        ? `${progress.chaptersApproved} of ${progress.plannedChapters} chapters approved`
        : `${progress.chaptersWritten} chapter${progress.chaptersWritten === 1 ? '' : 's'} written`,
      done: progress.stepsDone.write,
    },
    {
      step: 'review',
      title: 'Review',
      detail: progress.pendingFacts || progress.chaptersInReview
        ? [progress.chaptersInReview ? `${progress.chaptersInReview} chapter${progress.chaptersInReview === 1 ? '' : 's'} to read` : '', progress.pendingFacts ? `${progress.pendingFacts} fact${progress.pendingFacts === 1 ? '' : 's'} to confirm` : ''].filter(Boolean).join(' · ')
        : 'Nothing waiting',
      done: progress.stepsDone.review,
    },
    {
      step: 'finish',
      title: 'Finish',
      detail: manuscriptStatus ? `Book ${manuscriptStatus === 'approved' ? 'approved' : `in ${manuscriptStatus}`}` : 'Not started',
      done: progress.stepsDone.finish,
    },
  ]

  return (
    <div className="space-y-6" data-testid="primary-project-dashboard">
      <header>
        <p className="text-sm font-medium text-primary">Overview</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl" data-testid="overview-title">{bookTitle}</h1>
        {premise ? <p className="mt-2 line-clamp-2 max-w-3xl text-[15px] leading-6 text-muted-foreground">{premise}</p> : null}
      </header>

      {running ? (
        <Card className="border-primary/30 bg-primary/5" testId="development-progress">
          <div className="flex items-start gap-3" aria-live="polite">
            <Loader2 className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-primary" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">The AI is building your plan</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{String(currentRun?.metadata?.author_phase || 'Getting started')}</p>
                </div>
                {totalWork > 0 ? <span className="text-sm font-medium">{completedWork} of {totalWork}</span> : null}
              </div>
              <ProgressBar value={runPercent} className="mt-3" label="Planning progress" />
              <p className="mt-2 text-xs text-muted-foreground">Finished parts are saved as they complete. You can keep working meanwhile.</p>
            </div>
          </div>
        </Card>
      ) : null}

      {currentRun?.status === 'failed' ? (
        <Card className="border-destructive/30 bg-destructive/5" testId="development-failed">
          <p className="font-semibold">The AI could not finish planning</p>
          <p className="mt-1 text-sm text-muted-foreground">{currentRun.error || 'Anything that finished was saved.'} You can try again; nothing is lost.</p>
          <div className="mt-3 flex flex-wrap gap-2"><Button onClick={onDevelop}>Try again</Button><Button variant="outline" onClick={() => onNavigate('workflow')}>See what happened</Button></div>
        </Card>
      ) : null}

      {currentRun?.status === 'interrupted' ? (
        <Card className="border-warning/40 bg-warning/10" testId="development-interrupted">
          <p className="font-semibold">Planning stopped when the app restarted</p>
          <p className="mt-1 text-sm text-muted-foreground">Finished parts were kept. Continue when you are ready.</p>
          <Button className="mt-3" onClick={onDevelop}>Continue planning</Button>
        </Card>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section className="flex flex-col rounded-xl border border-primary/20 bg-gradient-to-br from-primary/10 via-card to-card p-6 shadow-soft" data-testid="next-step-card">
          <div>
            <p className="inline-flex items-center gap-1.5 text-sm font-medium text-primary"><Sparkles className="h-4 w-4" />Your next step</p>
            <h2 className="mt-3 text-xl font-semibold sm:text-2xl">{nextStep.title}</h2>
            <p className="mt-2 max-w-xl text-[15px] leading-6 text-muted-foreground">{nextStep.description}</p>
          </div>
          <div className="mt-6">
            <Button size="lg" onClick={runNextStep} disabled={busy && !nextStep.section} className="gap-2" data-testid="next-step-action">
              {busy && !nextStep.section ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {nextStep.label}<ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </section>

        <Card testId="overview-progress">
          <CardTitle description={progress.percent !== null ? `${progress.percent}% of planned chapters approved` : 'Set the number of chapters in your story arcs to track a target.'}>Your progress</CardTitle>
          {progress.percent !== null ? <ProgressBar value={progress.percent} className="mb-5" label="Book progress" /> : null}
          <ol className="space-y-1">
            {milestones.map((item) => (
              <li key={item.step}>
                <button type="button" onClick={() => onStep(item.step)} className="flex w-full items-start gap-3 rounded-lg px-2 py-2 text-left hover:bg-accent">
                  {item.done ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-success" /> : <Circle className={cn('mt-0.5 h-5 w-5 shrink-0', progress.stage === item.step ? 'text-primary' : 'text-muted-foreground/40')} />}
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">{item.title}{progress.stage === item.step ? <StatusBadge tone="info" className="ml-2">Now</StatusBadge> : null}</span>
                    <span className="block truncate text-xs text-muted-foreground">{item.detail}</span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      {progress.stage === 'plan' && setup ? setup : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat icon={<BookOpen className="h-4 w-4" />} label="Chapters" value={String(progress.chaptersWritten)} />
        <Stat icon={<Feather className="h-4 w-4" />} label="Words" value={progress.words.toLocaleString()} />
        <Stat icon={<CheckCircle2 className="h-4 w-4" />} label="Waiting for you" value={String(progress.pendingFacts + progress.chaptersInReview + counts.openQuestions)} />
      </div>

      <Card>
        <CardTitle
          description="Open a chapter to read, edit or approve it."
          action={<Button variant="outline" size="sm" onClick={() => onNavigate('writing')}>All chapters</Button>}
        >
          Recent chapters
        </CardTitle>
        {recentChapters.length ? (
          <ul className="divide-y">
            {recentChapters.map((chapter) => (
              <li key={chapter.draft_id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">Chapter {chapter.chapter_number}{chapter.title && chapter.title !== `Chapter ${chapter.chapter_number}` ? ` · ${chapter.title}` : ''}</p>
                  <p className="text-xs text-muted-foreground">{chapter.word_count.toLocaleString()} words</p>
                </div>
                <StatusBadge tone={chapter.status === 'approved' ? 'success' : 'warning'}>{chapter.status === 'approved' ? 'Approved' : 'To review'}</StatusBadge>
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted/40 p-4">
            <p className="text-sm text-muted-foreground">No chapters yet. When your plan feels right, write the first one.</p>
            <Button size="sm" onClick={() => onNavigate('write-next')}><PenLine className="mr-1.5 h-4 w-4" />Write Chapter 1</Button>
          </div>
        )}
      </Card>

      <Card>
        <CardTitle description="The AI reads your idea and suggests characters, world, plot threads and story arcs. You review everything it adds.">AI planning</CardTitle>
        <Button variant="outline" onClick={onDevelop} disabled={busy} data-testid="dashboard-run-cycle" className="gap-2">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {busy ? 'AI is planning…' : progress.stepsDone.plan ? 'Let AI improve the plan' : 'Let AI build the plan'}
        </Button>
      </Card>

      {guidance}
    </div>
  )
}

function Stat({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-4 shadow-soft">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">{icon}</span>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-lg font-semibold leading-tight">{value}</p>
      </div>
    </div>
  )
}
