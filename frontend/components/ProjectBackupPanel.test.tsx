import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProjectBackupPanel from './ProjectBackupPanel'
import { operationsApi } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  operationsApi: {
    listBackups: vi.fn(),
    createBackup: vi.fn(),
    downloadBackup: vi.fn(),
    validateBackup: vi.fn(),
    restoreBackup: vi.fn(),
    importBackup: vi.fn(),
  },
}))

const backup = {
  backup_id: 'backup-1234',
  created_at: '2026-08-02T10:00:00Z',
  reason: 'manual',
  status: 'available',
  archive_bytes: 2048,
  document_count: 42,
  app_version: '2.0.0-rc9',
  schema_version: 9,
}

describe('ProjectBackupPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(operationsApi.listBackups).mockResolvedValue({ backups: [backup] })
  })

  it('explains backup scope and requires validation before non-destructive restore', async () => {
    vi.mocked(operationsApi.validateBackup).mockResolvedValue({ valid: true, document_count: 42 })
    vi.mocked(operationsApi.restoreBackup).mockResolvedValue({ project_id: 'restored-id', project_title: 'Restored Story' })
    render(<ProjectBackupPanel projectId="project-id" />)
    expect(await screen.findByText(/42 records/)).toBeTruthy()
    expect(screen.getByText(/separate from publication export/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /check for restore/i }))
    await waitFor(() => expect(screen.getByTestId('restore-preview')).toBeTruthy())
    expect(screen.getByText(/current project and approved prose will remain unchanged/i)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Restored project name'), { target: { value: 'Restored Story' } })
    fireEvent.click(screen.getByRole('button', { name: /restore as new project/i }))
    await waitFor(() => expect(operationsApi.restoreBackup).toHaveBeenCalledWith(
      'backup-1234',
      'Restored Story',
      expect.any(String),
    ))
    expect(await screen.findByText(/original project was not changed/i)).toBeTruthy()
    expect(screen.queryByTestId('restore-preview')).toBeNull()
  })

  it('does not offer restore when integrity validation fails', async () => {
    vi.mocked(operationsApi.validateBackup).mockRejectedValue(new Error('damaged'))
    render(<ProjectBackupPanel projectId="project-id" />)
    fireEvent.click(await screen.findByRole('button', { name: /check for restore/i }))
    expect((await screen.findByRole('alert')).textContent).toContain('will not restore it')
    expect(screen.queryByRole('button', { name: /restore as new project/i })).toBeNull()
  })

  it('imports and validates a downloaded backup before offering restore', async () => {
    vi.mocked(operationsApi.importBackup).mockResolvedValue({
      ...backup,
      valid: true,
      imported: true,
    })
    render(<ProjectBackupPanel projectId="project-id" />)
    const file = new File(['backup bytes'], 'story.novelforge-backup', { type: 'application/zip' })
    fireEvent.change(screen.getByLabelText('Import NovelForge backup'), { target: { files: [file] } })
    await waitFor(() => expect(operationsApi.importBackup).toHaveBeenCalledWith(file))
    expect(await screen.findByTestId('restore-preview')).toBeTruthy()
    expect(screen.getByText(/imported and verified/i)).toBeTruthy()
  })

  it('keeps a failed download visible and explains that saved work is safe', async () => {
    vi.mocked(operationsApi.downloadBackup).mockRejectedValue(new Error('disk blocked'))
    render(<ProjectBackupPanel projectId="project-id" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Download backup' }))
    expect((await screen.findByRole('alert')).textContent).toContain('project and the stored backup remain unchanged')
  })

  it('explains when a newly created archive is safe but its automatic download fails', async () => {
    vi.mocked(operationsApi.createBackup).mockResolvedValue({
      ...backup,
      project_title: 'Recovery Story',
    })
    vi.mocked(operationsApi.downloadBackup).mockRejectedValue(new Error('download blocked'))
    render(<ProjectBackupPanel projectId="project-id" />)
    fireEvent.click(await screen.findByRole('button', { name: /back up and download/i }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('backup was created and remains available')
    expect(alert.textContent).toContain('Use Download backup')
  })

  it('reuses the same restore request identity after a lost response', async () => {
    vi.mocked(operationsApi.validateBackup).mockResolvedValue({ valid: true, document_count: 42 })
    vi.mocked(operationsApi.restoreBackup)
      .mockRejectedValueOnce(new Error('response lost'))
      .mockResolvedValueOnce({ project_id: 'restored-id', project_title: 'Recovered Story' })
    render(<ProjectBackupPanel projectId="project-id" />)
    fireEvent.click(await screen.findByRole('button', { name: /check for restore/i }))
    await screen.findByTestId('restore-preview')
    fireEvent.change(screen.getByLabelText('Restored project name'), { target: { value: 'Recovered Story' } })
    fireEvent.click(screen.getByRole('button', { name: /restore as new project/i }))
    await screen.findByRole('alert')
    const firstRequestId = vi.mocked(operationsApi.restoreBackup).mock.calls[0][2]
    fireEvent.click(screen.getByRole('button', { name: /restore as new project/i }))
    await screen.findByText(/original project was not changed/i)
    expect(vi.mocked(operationsApi.restoreBackup).mock.calls[1][2]).toBe(firstRequestId)
  })
})
