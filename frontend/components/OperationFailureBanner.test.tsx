import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import OperationFailureBanner from './OperationFailureBanner'

const failure = {
  operation: 'Chapter assembly',
  explanation: 'This chapter cannot be assembled because Scene 3 needs approval.',
  safety: 'Your existing prose is unchanged and remains safe.',
  destination: 'drafting',
  technicalDetails: 'scene_id=8dd32da4-1c03-4e4e-bbce-7d2527fc94c6',
  occurredAt: new Date().toISOString(),
  referenceId: 'support-ref-1234',
  retry: vi.fn(),
}

describe('OperationFailureBanner', () => {
  it('announces the author-language failure and hides machine details normally', () => {
    render(
      <OperationFailureBanner
        failure={failure}
        onRetry={vi.fn()}
        onDismiss={vi.fn()}
        onNavigate={vi.fn()}
      />
    )
    expect(screen.getByRole('alert').textContent).toContain('Chapter assembly needs your attention')
    expect(screen.getByRole('alert').textContent).toContain('existing prose is unchanged')
    expect(screen.getByRole('alert').textContent).toContain('support-ref-1234')
    expect(screen.queryByText(/8dd32da4/)).toBeNull()
  })

  it('offers retry, navigation, acknowledgement, and developer-only details', () => {
    const retry = vi.fn().mockResolvedValue(undefined)
    const navigate = vi.fn()
    const dismiss = vi.fn()
    render(
      <OperationFailureBanner
        failure={failure}
        developerMode
        onRetry={retry}
        onDismiss={dismiss}
        onNavigate={navigate}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Retry safely' }))
    fireEvent.click(screen.getByRole('button', { name: 'Open the blocking item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge' }))
    expect(retry).toHaveBeenCalledOnce()
    expect(navigate).toHaveBeenCalledWith('drafting')
    expect(dismiss).toHaveBeenCalledOnce()
    expect(screen.getByTestId('operation-failure-technical')).toBeTruthy()
  })
})
