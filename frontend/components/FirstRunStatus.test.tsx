import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import FirstRunStatus from './FirstRunStatus'
import { operationsApi } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  operationsApi: { getReadiness: vi.fn() },
}))

describe('FirstRunStatus', () => {
  beforeEach(() => vi.clearAllMocks())

  it('guides a new author to projects and AI setup without hiding local availability', async () => {
    vi.mocked(operationsApi.getReadiness).mockResolvedValue({
      status: 'offline_ready',
      summary: 'Your local projects are ready. AI assistance needs setup or recovery.',
      first_run: true,
      existing_work_available: true,
      app_version: '2.0.0-rc9',
      checks: {
        ai: { status: 'needs_setup', explanation: 'Your projects are available, but AI writing needs setup.' },
      },
    })
    render(<FirstRunStatus />)
    await waitFor(() => expect(screen.getByTestId('first-run-status')).toBeTruthy())
    expect(screen.getByText(/let’s get NovelForge ready/i)).toBeTruthy()
    expect(screen.getByText(/existing projects remain available/i)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Create your first project' }).getAttribute('href')).toBe('/projects')
    expect(screen.getByRole('link', { name: 'Set up AI' }).getAttribute('href')).toBe('/settings#ai-provider')
  })

  it('explains a local-service startup failure without implying data loss', async () => {
    vi.mocked(operationsApi.getReadiness).mockRejectedValue(new Error('offline'))
    render(<FirstRunStatus />)
    await waitFor(() => expect(screen.getByTestId('first-run-unavailable')).toBeTruthy())
    expect(screen.getByRole('alert').textContent).toContain('stored work has not been changed')
  })
})

