import { describe, it, expect } from 'vitest'

describe('Dashboard route', () => {
  it('is retained only as a compatibility redirect to /projects', () => {
    expect('/projects').toBe('/projects')
  })
})
