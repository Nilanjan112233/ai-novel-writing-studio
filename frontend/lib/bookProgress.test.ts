import { describe, expect, it } from 'vitest'
import { computeBookProgress, computeNextStep } from './bookProgress'
import type { WritingState } from '@/types'

function chapter(number: number, status: string, words: number) {
  return {
    chapter_number: number,
    title: `Chapter ${number}`,
    workflow_mode: 'discovery',
    status,
    active_version: 1,
    version_count: 1,
    draft_id: `d${number}`,
    word_count: words,
    extraction: { status: 'candidate', candidate_count: 0 },
    intelligence: { status: 'ready', finding_count: 0 },
  }
}

function state(chapters: ReturnType<typeof chapter>[]): WritingState {
  return {
    project_id: 'p',
    workflow_mode: 'discovery',
    chapter_count: chapters.length,
    chapters,
    structured: { chapter_plans: 0, scene_plans: 0 },
    pending: { review: 0, enrichment: 0, canon_proposals: 0, author_decisions: 0 },
    next_action: { label: '', target: '' },
  }
}

const base = { hasPremise: true, characterCount: 0, arcCount: 0, plannedChapters: 0, pendingFacts: 0, blockingQuestions: 0 }

describe('computeBookProgress', () => {
  it('starts in planning with nothing written', () => {
    const progress = computeBookProgress({ ...base, writingState: state([]) })
    expect(progress.stage).toBe('plan')
    expect(progress.words).toBe(0)
    expect(progress.percent).toBeNull()
  })

  it('counts words and approved chapters against the plan', () => {
    const progress = computeBookProgress({
      ...base,
      characterCount: 2,
      plannedChapters: 4,
      writingState: state([chapter(1, 'approved', 500), chapter(2, 'review', 620)]),
    })
    expect(progress.stage).toBe('write')
    expect(progress.words).toBe(1120)
    expect(progress.chaptersApproved).toBe(1)
    expect(progress.chaptersInReview).toBe(1)
    expect(progress.percent).toBe(25)
    expect(progress.nextChapter).toBe(3)
    expect(progress.stepsDone.plan).toBe(true)
  })

  it('moves to review, then finish, once every planned chapter is approved', () => {
    const chapters = [chapter(1, 'approved', 500), chapter(2, 'approved', 500)]
    expect(computeBookProgress({ ...base, arcCount: 1, plannedChapters: 2, pendingFacts: 3, writingState: state(chapters) }).stage).toBe('review')
    expect(computeBookProgress({ ...base, arcCount: 1, plannedChapters: 2, writingState: state(chapters) }).stage).toBe('finish')
    expect(computeBookProgress({ ...base, arcCount: 1, plannedChapters: 2, writingState: state(chapters), manuscriptStatus: 'approved' }).stage).toBe('done')
  })
})

describe('computeNextStep', () => {
  it('asks for blocking decisions first', () => {
    const progress = computeBookProgress({ ...base, writingState: state([]) })
    expect(computeNextStep(progress, { ...base, blockingQuestions: 2 }).section).toBe('questions')
  })

  it('suggests building the plan, then writing, then reviewing', () => {
    const planning = computeBookProgress({ ...base, writingState: state([]) })
    expect(computeNextStep(planning, base).section).toBeNull()

    const ready = computeBookProgress({ ...base, characterCount: 1, writingState: state([]) })
    expect(computeNextStep(ready, { ...base, characterCount: 1 }).label).toBe('Write Chapter 1')

    const reviewing = computeBookProgress({ ...base, characterCount: 1, writingState: state([chapter(1, 'draft', 300)]) })
    expect(computeNextStep(reviewing, { ...base, characterCount: 1 }).section).toBe('writing')

    const facts = computeBookProgress({ ...base, characterCount: 1, pendingFacts: 2, writingState: state([chapter(1, 'approved', 300)]) })
    expect(computeNextStep(facts, { ...base, characterCount: 1 }).section).toBe('facts')
  })
})
