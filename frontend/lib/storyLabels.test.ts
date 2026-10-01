import { describe, expect, it } from 'vitest'

import { numberedTitle, withoutNumberedPrefix } from './storyLabels'

describe('withoutNumberedPrefix', () => {
  it('prevents generated chapter and scene titles from repeating their labels', () => {
    expect(withoutNumberedPrefix('Chapter 1: The Last Bus', 'chapter')).toBe('The Last Bus')
    expect(withoutNumberedPrefix('Scene 2 — The Empty Road', 'scene')).toBe('The Empty Road')
  })

  it('preserves ordinary author titles', () => {
    expect(withoutNumberedPrefix('Rain over the Station', 'chapter')).toBe('Rain over the Station')
  })

  it('does not repeat a bare generated chapter label', () => {
    expect(numberedTitle('chapter', 1, 'Chapter 1')).toBe('Chapter 1')
  })
})
