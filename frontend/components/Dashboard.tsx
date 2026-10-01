'use client'

import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, BookOpen, CheckCircle2, Circle, HelpCircle, Loader2, Map, ShieldCheck, Sparkles, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { projectsApi } from '@/lib/api'
import type { AIInsights, Project, Question, ReadinessReport, Run, StoryArc, StoryHealth, StoryRoom, WritingState } from '@/types'

interface DashboardProps {
  project: Project | null
  storyHealth: StoryHealth | null
  storyRoom: StoryRoom | null
  storyArcs: StoryArc[]
  questions: Question[]
  readinessReports: ReadinessReport[]
  aiInsights: AIInsights | null
  currentRun: Run | null
  hasScenePlan: boolean
  activeDraftStatus?: string
  onRunCycle: () => void
  onNavigate: (section: string) => void
  busy: boolean
  writingState?: WritingState | null
  onProjectUpdated?: (project: Project) => void
}

export function readinessLabel(status: string | undefined, requiredItems?: number): string {
  if (!status || !requiredItems) return 'Not evaluated'
  if (status === 'READY') return 'Ready to Draft'
  if (status === 'PARTIALLY_READY') return 'Partially Ready'
  return 'Not Ready'
}

export function readinessSummary(report: ReadinessReport | null): string {
  if (!report || !report.required_items) return 'Evaluate the current arc'
  return `${report.satisfied_required_items}/${report.required_items} current-arc requirements`
}

export default function Dashboard({
  project,
  storyRoom,
  storyArcs,
  questions,
  readinessReports,
  currentRun,
  hasScenePlan,
  activeDraftStatus,
  onRunCycle,
  onNavigate,
  busy,
  writingState,
  onProjectUpdated,
}: DashboardProps) {
  const [projectName, setProjectName] = useState('')
  const [storyTitle, setStoryTitle] = useState('')
  const [identityBusy, setIdentityBusy] = useState(false)
  const [identityNotice, setIdentityNotice] = useState('')
  useEffect(() => {
    setProjectName(project?.project_name || project?.title || '')
    setStoryTitle(project?.story_title || '')
  }, [project?.id, project?.project_name, project?.title, project?.story_title])
  const activeArc = useMemo(
    () => storyRoom?.current_arc ?? storyArcs.find((arc) => arc.focus_role === 'current' || arc.approval_status === 'active') ?? storyArcs[0] ?? null,
    [storyRoom, storyArcs]
  )
  const openQuestions = useMemo(() => questions.filter((question) => !question.answered), [questions])
  const blockingQuestions = useMemo(() => openQuestions.filter((question) => question.blocking), [openQuestions])
  const optionalQuestions = useMemo(() => openQuestions.filter((question) => !question.blocking), [openQuestions])
  const latestReadiness = readinessReports[0] ?? null
  const isRunning = currentRun?.status === 'running'
  const reconsideration = project?.planning_reconsideration
  const needsReconsideration = reconsideration?.status === 'pending'

  const nextAction = useMemo(() => {
    if (writingState?.latest_approved_chapter) {
      return {
        title: `Continue with Chapter ${writingState.latest_approved_chapter.chapter_number + 1}`,
        description: `You have ${writingState.chapter_count} chapter${writingState.chapter_count === 1 ? '' : 's'} saved. Chapter ${writingState.latest_approved_chapter.chapter_number} is approved and ready to carry forward.`,
        label: `Open Chapter ${writingState.latest_approved_chapter.chapter_number + 1}`,
        section: 'writing',
      }
    }
    if (blockingQuestions.length > 0) {
      return {
        title: 'Your direction is needed',
        description: `${blockingQuestions.length} important story ${blockingQuestions.length === 1 ? 'choice needs' : 'choices need'} your answer before NovelForge continues.`,
        label: 'Review choices',
        section: 'questions',
      }
    }
    if (!activeArc) {
      return {
        title: 'Develop the story foundation',
        description: 'NovelForge can build the characters, world, themes, arcs, timeline, and scene plans from your story idea.',
        label: 'Develop my story',
        section: null,
      }
    }
    if (needsReconsideration) {
      return {
        title: 'Update the plan to match your change',
        description: reconsideration?.message || 'NovelForge found generated planning that should be reconsidered after your decision changed.',
        label: 'Reconsider affected planning',
        section: null,
      }
    }
    if (activeDraftStatus === 'draft') {
      return {
        title: 'Review your new scene',
        description: 'The draft is ready for you to read. Nothing becomes approved until you decide.',
        label: 'Review the draft',
        section: 'drafting',
      }
    }
    if (activeDraftStatus === 'review') {
      return {
        title: 'Revise or approve the scene',
        description: 'Choose a focused revision, create an alternative, or approve the version when it works for you.',
        label: 'Continue review',
        section: 'drafting',
      }
    }
    if (latestReadiness?.drafting_eligible) {
      if (!hasScenePlan) {
        return {
          title: 'Plan your first scene',
          description: 'The current arc is approved and ready. Let NovelForge propose the first scene, or describe it yourself.',
          label: 'Plan the first scene',
          section: 'drafting',
        }
      }
      return {
        title: 'Your next scene is ready',
        description: 'The current plan has enough detail to start writing. You can still change any part of it later.',
        label: 'Continue writing',
        section: 'drafting',
      }
    }
    if (activeArc) {
      return {
        title: 'Review the first story arc',
        description: 'NovelForge developed the arc. Confirm the supported planning choices and make it the current arc before scene planning begins.',
        label: 'Review the story arc',
        section: 'arc-development',
      }
    }
    return {
      title: 'Keep developing the plan',
      description: 'Let NovelForge run the right specialists, connect their work, and bring important choices back to you.',
      label: 'Develop my story',
      section: null,
    }
  }, [activeArc, latestReadiness, blockingQuestions.length, needsReconsideration, reconsideration?.message, hasScenePlan, activeDraftStatus, writingState])

  const completedWork = Number(currentRun?.metadata?.progress_completed || 0)
  const totalWork = Number(currentRun?.metadata?.progress_total || 0)
  const progressPercent = totalWork ? Math.min(100, Math.round((completedWork / totalWork) * 100)) : 8
  const authorPhase = String(currentRun?.metadata?.author_phase || 'Preparing the story team')
  const completedPasses = Number(currentRun?.metadata?.automatic_cycles_completed || 0)
  const maximumPasses = Number(currentRun?.metadata?.max_automatic_cycles || 0)

  const handleNextAction = () => {
    if (nextAction.section) onNavigate(nextAction.section)
    else onRunCycle()
  }

  const stages = [
    { label: 'Foundation', complete: Boolean(activeArc) },
    { label: 'Scene plan', complete: hasScenePlan },
    { label: 'Writing', complete: Boolean(activeDraftStatus) || Boolean(writingState?.chapter_count) },
    { label: 'Review', complete: ['review', 'approved'].includes(activeDraftStatus || '') },
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-in fade-in duration-300">
      {project ? <section className="rounded-xl border bg-card p-4" data-testid="project-identity"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Project identity</p><h2 className="mt-1 text-lg font-semibold">Workspace and novel title</h2><p className="mt-1 text-sm text-muted-foreground">The workspace name helps you find this project. The optional story title is what readers will see.</p></div><Button size="sm" variant="outline" disabled={identityBusy || !projectName.trim()} onClick={async () => { setIdentityBusy(true); setIdentityNotice(''); try { const updated = await projectsApi.update(project.id, { project_name: projectName.trim(), story_title: storyTitle.trim() || null }); onProjectUpdated?.(updated as Project); setIdentityNotice('Project identity saved.') } catch { setIdentityNotice('Identity could not be saved. Your story data is unchanged.') } finally { setIdentityBusy(false) } }}>{identityBusy ? 'Saving…' : 'Save identity'}</Button></div><div className="mt-4 grid gap-3 md:grid-cols-2"><div className="space-y-2"><Label htmlFor="dashboard-project-name">Project name</Label><Input id="dashboard-project-name" value={projectName} onChange={(event) => setProjectName(event.target.value)} /></div><div className="space-y-2"><Label htmlFor="dashboard-story-title">Story title <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="dashboard-story-title" placeholder="Untitled for now" value={storyTitle} onChange={(event) => setStoryTitle(event.target.value)} /></div></div>{identityNotice ? <p className="mt-2 text-xs text-muted-foreground" aria-live="polite">{identityNotice}</p> : null}</section> : null}
      <section className="overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-card via-card to-primary/10 p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              {isRunning ? 'Developing your story now' : 'Your writing home'}
            </div>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">{writingState?.latest_approved_chapter ? `Chapter ${writingState.latest_approved_chapter.chapter_number} approved` : project?.project_name || project?.title || 'Your Novel'}</h2>
            <p className="mt-3 max-w-xl text-base leading-7 text-muted-foreground">
              {writingState?.latest_approved_chapter ? `${writingState.chapter_count} chapters are saved in this project. Read, revise, or continue writing from your chapter library.` : 'Give NovelForge the big idea. It develops the connected plan automatically, while you stay in control of every important choice.'}
            </p>
          </div>
          <Button
            size="lg"
            onClick={onRunCycle}
            disabled={busy || isRunning}
            data-testid="dashboard-run-cycle"
            className="h-12 gap-2 rounded-xl px-6 shadow-lg shadow-primary/20"
          >
            {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isRunning ? 'Developing story…' : 'Develop My Story'}
          </Button>
        </div>
      </section>

      {isRunning && (
        <section className="rounded-2xl border border-primary/30 bg-primary/5 p-5" aria-live="polite" data-testid="development-progress">
          <div className="flex items-start gap-3">
            <Loader2 className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-primary" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">Your story team is working</p>
                  <p className="mt-1 text-sm text-muted-foreground">{authorPhase}</p>
                </div>
                {totalWork > 0 && <span className="text-sm font-medium">{completedWork} of {totalWork}</span>}
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-primary/10">
                <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${progressPercent}%` }} />
              </div>
              <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                {maximumPasses > 1 && <span>Development pass {Math.min(completedPasses + 1, maximumPasses)} of up to {maximumPasses}</span>}
                <span>Completed work is saved as it finishes.</span>
                <button type="button" onClick={() => onNavigate('workflow')} className="font-medium text-primary hover:underline">See activity and results</button>
              </div>
            </div>
          </div>
        </section>
      )}

      {currentRun?.status === 'failed' && (
        <section className="rounded-2xl border border-red-500/30 bg-red-500/5 p-5" role="alert" data-testid="development-failed">
          <p className="font-semibold">Story development needs attention</p>
          <p className="mt-1 text-sm text-muted-foreground">{currentRun.error || 'NovelForge could not finish the last development pass. Work that completed successfully was kept.'}</p>
          <div className="mt-4 flex gap-2"><Button onClick={onRunCycle}>Try again safely</Button><Button variant="outline" onClick={() => onNavigate('workflow')}>Review activity</Button></div>
        </section>
      )}

      {currentRun?.status === 'interrupted' && (
        <section className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5" role="status" data-testid="development-interrupted">
          <p className="font-semibold">Development stopped when NovelForge restarted</p>
          <p className="mt-1 text-sm text-muted-foreground">Completed work was kept. Continue when you are ready; NovelForge will reconsider what remains.</p>
          <div className="mt-4 flex gap-2"><Button onClick={onRunCycle}>Continue development</Button><Button variant="outline" onClick={() => onNavigate('workflow')}>Review saved work</Button></div>
        </section>
      )}

      {needsReconsideration && !isRunning && (
        <section className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5" role="status" data-testid="planning-reconsideration">
          <p className="font-semibold">Your story change is saved</p>
          <p className="mt-1 text-sm text-muted-foreground">{reconsideration?.message || 'Some generated planning no longer matches your decision.'} The earlier versions remain in history; develop the story again to replace only the affected work.</p>
          <Button className="mt-4" onClick={onRunCycle} disabled={busy}>Reconsider affected planning</Button>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <button
          type="button"
          onClick={handleNextAction}
          disabled={(busy || isRunning) && !nextAction.section}
          className="group rounded-2xl border border-primary/25 bg-primary/5 p-6 text-left transition hover:border-primary/50 hover:bg-primary/10 disabled:cursor-wait"
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">Best next step</p>
          <h3 className="mt-3 text-xl font-semibold">{nextAction.title}</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{nextAction.description}</p>
          <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-primary">
            {nextAction.label}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </button>

        <div className="rounded-2xl border border-border bg-card p-6">
          <h3 className="font-semibold">Story progress</h3>
          <div className="mt-5 space-y-4">
            {stages.map((stage, index) => (
              <div key={stage.label} className="flex items-center gap-3">
                {stage.complete ? <CheckCircle2 className="h-5 w-5 text-emerald-500" /> : <Circle className="h-5 w-5 text-muted-foreground/40" />}
                <span className={stage.complete ? 'text-sm font-medium' : 'text-sm text-muted-foreground'}>{stage.label}</span>
                {index === 0 && activeArc && <span className="ml-auto max-w-32 truncate text-xs text-muted-foreground">{activeArc.title}</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {writingState?.chapter_count ? (
        <section className="rounded-2xl border border-sky-200 bg-sky-50/50 p-5" data-testid="dashboard-writing-state">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="text-xs font-semibold uppercase tracking-wider text-sky-700">Writing state</p><h3 className="mt-1 text-lg font-semibold text-sky-950">{writingState.chapter_count} chapter{writingState.chapter_count === 1 ? '' : 's'} saved</h3><p className="mt-1 text-sm text-sky-900/80">Latest approved: Chapter {writingState.latest_approved_chapter?.chapter_number || 'none'} · {writingState.pending.review} waiting for review</p></div>
            <Button variant="outline" onClick={() => onNavigate('writing')}>Open chapter library <ArrowRight className="ml-1.5 h-4 w-4" /></Button>
          </div>
        </section>
      ) : null}

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Open a workspace</h3>
          <button type="button" onClick={() => onNavigate('story-health')} className="text-xs font-medium text-primary hover:underline">See story checks</button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Story plan', description: 'See arcs and scene direction', section: 'arc-development', icon: Map },
            { label: 'Characters', description: 'Review people and relationships', section: 'characters', icon: Users },
            { label: 'Continue writing', description: 'Draft and review scenes', section: 'drafting', icon: BookOpen },
            { label: 'Story checks', description: 'Find continuity issues', section: 'story-health', icon: ShieldCheck },
          ].map(({ label, description, section, icon: Icon }) => (
            <button key={section} type="button" onClick={() => onNavigate(section)} className="group rounded-xl border border-border bg-card p-4 text-left transition hover:border-primary/40 hover:shadow-sm">
              <Icon className="h-5 w-5 text-primary" />
              <p className="mt-3 text-sm font-semibold">{label}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
            </button>
          ))}
        </div>
      </section>

      {blockingQuestions.length > 0 && (
        <button type="button" onClick={() => onNavigate('questions')} className="flex w-full items-center gap-3 rounded-xl border border-amber-500/25 bg-amber-500/5 p-4 text-left">
          <HelpCircle className="h-5 w-5 shrink-0 text-amber-500" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">NovelForge needs your direction</p>
            <p className="truncate text-xs text-muted-foreground">{blockingQuestions[0]?.text ?? 'Review the important story choices.'}</p>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </button>
      )}
      {blockingQuestions.length === 0 && optionalQuestions.length > 0 && (
        <button type="button" onClick={() => onNavigate('questions')} className="flex w-full items-center gap-3 rounded-xl border border-border bg-card p-4 text-left">
          <HelpCircle className="h-5 w-5 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1"><p className="text-sm font-semibold">Optional ideas to consider</p><p className="truncate text-xs text-muted-foreground">{optionalQuestions.length} question{optionalQuestions.length === 1 ? '' : 's'} can deepen the story, but development does not have to stop.</p></div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </button>
      )}
    </div>
  )
}
