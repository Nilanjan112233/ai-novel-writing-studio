import { describe, expect, it } from 'vitest'

import type { ReadinessReport } from '@/types'
import { readinessLabel, readinessSummary } from './Dashboard'

describe('Dashboard readiness language', () => {
  it('does not call an empty readiness report Not Ready', () => {
    const emptyReport = {
      status: 'NOT_READY',
      required_items: 0,
      satisfied_required_items: 0,
    }

    expect(readinessLabel(emptyReport.status, emptyReport.required_items)).toBe('Not evaluated')
    expect(readinessSummary(emptyReport as ReadinessReport)).toBe('Evaluate the current arc')
  })

  it('qualifies evaluated readiness as current-arc readiness', () => {
    const report = {
      status: 'PARTIALLY_READY',
      required_items: 5,
      satisfied_required_items: 3,
    }

    expect(readinessLabel(report.status, report.required_items)).toBe('Partially Ready')
    expect(readinessSummary(report as ReadinessReport)).toBe('3/5 current-arc requirements')
  })
})
