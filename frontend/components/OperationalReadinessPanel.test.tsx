import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import OperationalReadinessPanel from './OperationalReadinessPanel'

const { getReadiness, getPrivacy, createSupportBundle, downloadSupportBundle, submitFeedback, createAllBackups } = vi.hoisted(() => ({
  getReadiness: vi.fn(),
  getPrivacy: vi.fn(),
  createSupportBundle: vi.fn(),
  downloadSupportBundle: vi.fn(),
  submitFeedback: vi.fn(),
  createAllBackups: vi.fn(),
}))

vi.mock('@/lib/api', () => ({
  operationsApi: {
    getReadiness,
    getPrivacy,
    createSupportBundle,
    downloadSupportBundle,
    submitFeedback,
    createAllBackups,
  },
}))

describe('OperationalReadinessPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getReadiness.mockResolvedValue({
      status: 'offline_ready',
      summary: 'Your projects are available. AI assistance needs attention.',
      app_version: '2.0.0-rc9',
      schema_version: 9,
      checks: {
        database: { status: 'ready', explanation: 'Local project storage is ready.' },
        ai: { status: 'unavailable', explanation: 'AI is unavailable. Existing projects remain readable and editable.' },
      },
    })
    getPrivacy.mockResolvedValue({ excluded_from_support_bundles: ['story prose'] })
    createSupportBundle.mockResolvedValue({ support_id: 'support-12345678' })
    downloadSupportBundle.mockResolvedValue(new Blob(['safe']))
    submitFeedback.mockResolvedValue({ feedback_id: 'feedback-1', explanation: 'Feedback was saved locally.' })
    createAllBackups.mockResolvedValue({ succeeded: 2, failed: 0, complete: true })
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: vi.fn(() => 'blob:support'),
      revokeObjectURL: vi.fn(),
    })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  })

  it('keeps existing work explicitly available when AI is offline', async () => {
    render(<OperationalReadinessPanel />)
    expect(await screen.findByText('Your projects are available. AI assistance needs attention.')).toBeInTheDocument()
    expect(screen.getByText('AI is unavailable. Existing projects remain readable and editable.')).toBeInTheDocument()
    expect(screen.getByText('Private by default')).toBeInTheDocument()
  })

  it('creates opt-in diagnostics and saves feedback locally', async () => {
    render(<OperationalReadinessPanel />)
    await screen.findByText('Your projects are available. AI assistance needs attention.')

    fireEvent.click(screen.getByRole('button', { name: 'Download safe diagnostics' }))
    await waitFor(() => expect(createSupportBundle).toHaveBeenCalledOnce())
    expect(await screen.findByText(/Story content and credentials were not included/)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Private beta feedback'), { target: { value: 'The startup message was unclear.' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Include sanitized diagnostics' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save feedback locally' }))
    await waitFor(() => expect(submitFeedback).toHaveBeenCalledWith({
      category: 'bug',
      message: 'The startup message was unclear.',
      include_diagnostics: true,
    }))
  })

  it('creates a bounded local backup for every project', async () => {
    render(<OperationalReadinessPanel />)
    await screen.findByText('Your projects are available. AI assistance needs attention.')
    fireEvent.click(screen.getByRole('button', { name: 'Back up all projects' }))
    await waitFor(() => expect(createAllBackups).toHaveBeenCalledOnce())
    expect(await screen.findByText(/2 project backups completed/)).toBeInTheDocument()
  })

  it('shows a durable author-facing recovery message when readiness cannot be checked', async () => {
    getReadiness.mockRejectedValue(new Error('connection refused'))
    render(<OperationalReadinessPanel />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Your existing work has not been changed.')
  })
})
