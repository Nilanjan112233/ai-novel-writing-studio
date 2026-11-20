// Turns the project's saved data into a simple picture of "where is my book":
// the current stage on the guided path, chapters approved against the plan,
// total words, and the single most useful next step.

import type { WritingState } from '@/types'

export type BookStage = 'plan' | 'write' | 'review' | 'finish' | 'done'

export interface BookProgressInput {
  writingState?: WritingState | null
  hasPremise: boolean
  characterCount: number
  arcCount: number
  plannedChapters: number
  pendingFacts: number
  blockingQuestions: number
  manuscriptStatus?: string | null
}

export interface BookProgress {
  stage: BookStage
  chaptersWritten: number
  chaptersApproved: number
  chaptersInReview: number
  plannedChapters: number
  words: number
  pendingFacts: number
  /** 0-100, chapters approved against the plan; null when no target is known. */
  percent: number | null
  stepsDone: Record<'plan' | 'write' | 'review' | 'finish', boolean>
  nextChapter: number
}

export interface NextStep {
  title: string
  description: string
  label: string
  /** Section to open, or null when the action is "let AI build the plan". */
  section: string | null
}

export function computeBookProgress(input: BookProgressInput): BookProgress {
  const chapters = input.writingState?.chapters ?? []
  const chaptersApproved = chapters.filter((chapter) => chapter.status === 'approved').length
  const chaptersInReview = chapters.filter((chapter) => chapter.status !== 'approved').length
  const words = chapters.reduce((sum, chapter) => sum + (Number(chapter.word_count) || 0), 0)
  const plannedChapters = Math.max(0, Math.round(input.plannedChapters || 0))
  const lastNumber = chapters.reduce((max, chapter) => Math.max(max, Number(chapter.chapter_number) || 0), 0)

  const planDone = input.hasPremise && (input.characterCount > 0 || input.arcCount > 0)
  const writeDone = plannedChapters > 0 && chaptersApproved >= plannedChapters
  const nothingToReview = input.pendingFacts === 0 && chaptersInReview === 0
  const manuscript = input.manuscriptStatus || null
  const finishDone = manuscript === 'approved'

  let stage: BookStage
  if (finishDone) stage = 'done'
  else if (manuscript) stage = 'finish'
  else if (!planDone && chapters.length === 0) stage = 'plan'
  else if (writeDone) stage = nothingToReview ? 'finish' : 'review'
  else stage = 'write'

  return {
    stage,
    chaptersWritten: chapters.length,
    chaptersApproved,
    chaptersInReview,
    plannedChapters,
    words,
    pendingFacts: input.pendingFacts,
    percent: plannedChapters > 0 ? Math.min(100, Math.round((chaptersApproved / plannedChapters) * 100)) : null,
    stepsDone: {
      plan: planDone,
      write: writeDone,
      review: writeDone && nothingToReview,
      finish: finishDone,
    },
    nextChapter: lastNumber + 1,
  }
}

export function computeNextStep(progress: BookProgress, input: Pick<BookProgressInput, 'blockingQuestions' | 'hasPremise' | 'characterCount' | 'arcCount'>): NextStep {
  if (input.blockingQuestions > 0) {
    return {
      title: 'The AI needs your decision',
      description: `${input.blockingQuestions} story ${input.blockingQuestions === 1 ? 'choice needs' : 'choices need'} your answer before planning continues.`,
      label: 'Answer questions',
      section: 'questions',
    }
  }
  if (progress.stage === 'plan') {
    if (!input.hasPremise) {
      return { title: 'Describe your story idea', description: 'A few sentences about the premise is enough to start.', label: 'Add your idea', section: 'vision' }
    }
    return {
      title: 'Build the story plan',
      description: 'Let the AI suggest characters, world, plot threads and story arcs from your idea. You review and keep what you like.',
      label: 'Let AI build the plan',
      section: null,
    }
  }
  if (progress.chaptersInReview > 0) {
    return {
      title: 'Read and approve your latest chapter',
      description: `${progress.chaptersInReview} chapter${progress.chaptersInReview === 1 ? ' is' : 's are'} waiting for you to read and approve.`,
      label: 'Review chapters',
      section: 'writing',
    }
  }
  if (progress.pendingFacts > 0) {
    return {
      title: 'Confirm what the AI learned',
      description: `${progress.pendingFacts} new fact${progress.pendingFacts === 1 ? '' : 's'} from your chapters ${progress.pendingFacts === 1 ? 'is' : 'are'} waiting. Confirmed facts keep later chapters consistent.`,
      label: 'Confirm facts',
      section: 'facts',
    }
  }
  if (progress.stage === 'finish' || progress.stage === 'done') {
    return {
      title: progress.stage === 'done' ? 'Your book is approved' : 'Put your book together',
      description: progress.stage === 'done' ? 'Export it as DOCX, EPUB, PDF or another format.' : 'Assemble your approved chapters into a book, review it and export it.',
      label: progress.stage === 'done' ? 'Export the book' : 'Open Book & export',
      section: 'manuscript',
    }
  }
  return {
    title: progress.chaptersWritten === 0 ? 'Write your first chapter' : `Write Chapter ${progress.nextChapter}`,
    description: progress.chaptersWritten === 0
      ? 'Describe what should happen and the AI drafts it from your plan. You can edit every word.'
      : 'Describe what should happen next. The AI uses your approved chapters and confirmed facts.',
    label: progress.chaptersWritten === 0 ? 'Write Chapter 1' : `Write Chapter ${progress.nextChapter}`,
    section: 'write-next',
  }
}

export const STAGE_LABELS: Record<BookStage, string> = {
  plan: 'Planning',
  write: 'Writing',
  review: 'Reviewing',
  finish: 'Finishing',
  done: 'Complete',
}
