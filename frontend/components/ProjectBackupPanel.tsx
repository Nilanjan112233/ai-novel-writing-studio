'use client'

import Link from 'next/link'
import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Download, HardDriveDownload, Loader2, RotateCcw, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { operationsApi } from '@/lib/api'

type Backup = {
  backup_id: string
  created_at: string
  reason: string
  status: string
  archive_bytes: number
  document_count: number
  app_version: string
  schema_version: number
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url; link.download = filename
  document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url)
}

export default function ProjectBackupPanel({ projectId }: { projectId: string }) {
  const [backups, setBackups] = useState<Backup[]>([])
  const [busy, setBusy] = useState<string | null>('loading')
  const [selected, setSelected] = useState<Backup | null>(null)
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const [restoreTitle, setRestoreTitle] = useState('')
  const [restored, setRestored] = useState<{ project_id: string; project_title: string } | null>(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const restoreRequestId = useRef<string | null>(null)

  const refresh = useCallback(async () => {
    try { const result = await operationsApi.listBackups(projectId); setBackups(result.backups) }
    catch { setError('Backup history could not be loaded. Your project is unchanged.') }
    finally { setBusy(null) }
  }, [projectId])
  useEffect(() => { void refresh() }, [refresh])

  const create = async () => {
    setBusy('create'); setError(''); setNotice('')
    let result: { backup_id: string; project_title: string } | null = null
    try {
      result = await operationsApi.createBackup(projectId, 'manual author backup')
    } catch {
      setError('The backup could not be created. Your current project remains unchanged. Check storage and try again.')
      setBusy(null)
      return
    }
    if (!result) {
      setError('The backup response was incomplete. Your current project remains unchanged; try again.')
      setBusy(null)
      return
    }
    try {
      const blob = await operationsApi.downloadBackup(result.backup_id)
      downloadBlob(blob, `${result.project_title.replace(/[^a-z0-9]+/gi, '-') || 'novel'}.novelforge-backup`)
      setNotice('Backup verified and downloaded. It contains editable project state, not just the publication manuscript.')
    } catch {
      setError('The backup was created and remains available below, but the browser download could not start. Use Download backup to try again.')
    }
    await refresh()
    setBusy(null)
  }

  const validate = async (backup: Backup) => {
    setBusy(backup.backup_id); setError(''); setNotice(''); setRestored(null)
    try { setPreview(await operationsApi.validateBackup(backup.backup_id)); setSelected(backup); restoreRequestId.current = null }
    catch { setPreview(null); setSelected(null); setError('This backup did not pass its integrity check, so NovelForge will not restore it.') }
    finally { setBusy(null) }
  }

  const restore = async () => {
    if (!selected || !preview) return
    setBusy('restore'); setError(''); setNotice('')
    try {
      restoreRequestId.current ||= globalThis.crypto?.randomUUID?.() || `restore-${Date.now()}-${Math.random().toString(16).slice(2)}`
      const result = await operationsApi.restoreBackup(selected.backup_id, restoreTitle, restoreRequestId.current)
      setRestored(result)
      setSelected(null)
      setPreview(null)
      setRestoreTitle('')
      restoreRequestId.current = null
      setNotice('The backup was restored as a separate project and verified. Your original project was not changed.')
    } catch { setError('Restore could not be completed. The original project is unchanged and any incomplete copy was removed.') }
    finally { setBusy(null) }
  }

  const download = async (backup: Backup) => {
    setBusy(`download:${backup.backup_id}`); setError(''); setNotice('')
    try {
      const blob = await operationsApi.downloadBackup(backup.backup_id)
      downloadBlob(blob, `novelforge-${backup.backup_id.slice(0, 8)}.novelforge-backup`)
      setNotice('Backup downloaded. Keep this file somewhere separate from your NovelForge installation.')
    } catch {
      setError('This backup could not be downloaded. Your project and the stored backup remain unchanged; try again.')
    } finally { setBusy(null) }
  }

  const importBackup = async (file?: File) => {
    if (!file) return
    setBusy('import'); setError(''); setNotice(''); setRestored(null)
    try {
      const result = await operationsApi.importBackup(file)
      setSelected({
        backup_id: String(result.backup_id),
        created_at: String(result.created_at),
        reason: 'imported recovery backup',
        status: 'available',
        archive_bytes: Number(result.archive_bytes || file.size),
        document_count: Number(result.document_count || 0),
        app_version: String(result.app_version || 'unknown'),
        schema_version: Number(result.schema_version || 0),
      })
      setPreview(result)
      setNotice('Backup imported and verified. Review the restore preview before creating a separate project copy.')
    } catch { setError('This file could not be imported or did not pass validation. No project data was changed.') }
    finally { setBusy(null) }
  }

  return (
    <section className="mt-5 rounded-xl border bg-muted/20 p-4 space-y-4" data-testid="project-backups">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">Project backup and recovery</h3><p className="mt-1 text-sm text-muted-foreground">Protect plans, drafts, versions, decisions, canon, Story Bible and approvals. This is separate from publication export.</p></div><div className="flex flex-wrap gap-2"><label className="inline-flex h-10 cursor-pointer items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent focus-within:ring-2 focus-within:ring-ring"><Upload className="mr-2 h-4 w-4" />{busy === 'import' ? 'Checking file…' : 'Import backup'}<input className="sr-only" type="file" accept=".novelforge-backup,.zip,application/zip" aria-label="Import NovelForge backup" disabled={busy !== null} onChange={(event) => { void importBackup(event.target.files?.[0]); event.currentTarget.value = '' }} /></label><Button onClick={() => void create()} disabled={busy !== null}><HardDriveDownload className="mr-2 h-4 w-4" />{busy === 'create' ? 'Creating safely…' : 'Back up and download'}</Button></div></div>
      {error ? <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900"><AlertTriangle className="mr-2 inline h-4 w-4" />{error}</div> : null}
      {notice ? <div role="status" className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900"><CheckCircle2 className="mr-2 inline h-4 w-4" />{notice}{restored ? <Button asChild variant="link" size="sm"><Link href={`/project/${restored.project_id}`}>Open {restored.project_title}</Link></Button> : null}</div> : null}
      {busy === 'loading' ? <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading backup history…</div> : backups.length === 0 ? <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">No project backup yet. Create one before a major revision or application update.</div> : (
        <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-sm"><thead><tr className="border-b text-left"><th className="py-2">Created</th><th>Contents</th><th>Release</th><th>Status</th><th className="text-right">Actions</th></tr></thead><tbody>{backups.map((backup) => <tr key={backup.backup_id} className="border-b"><td className="py-3">{new Date(backup.created_at).toLocaleString()}</td><td>{backup.document_count.toLocaleString()} records · {(backup.archive_bytes / 1024).toFixed(1)} KB</td><td>{backup.app_version}</td><td className="capitalize">{backup.status}</td><td><div className="flex justify-end gap-2"><Button size="sm" variant="outline" onClick={() => void download(backup)} disabled={backup.status !== 'available' || busy !== null}><Download className="h-4 w-4" /><span className="sr-only">Download backup</span></Button><Button size="sm" variant="outline" onClick={() => void validate(backup)} disabled={backup.status !== 'available' || busy !== null}><RotateCcw className="mr-2 h-4 w-4" />Check for restore</Button></div></td></tr>)}</tbody></table></div>
      )}
      {selected && preview ? <div className="rounded-lg border border-violet-200 bg-violet-50/60 p-4" data-testid="restore-preview"><h4 className="font-semibold">Restore preview</h4><p className="mt-1 text-sm">Integrity passed. NovelForge will create a separate copy with {Number(preview.document_count || 0).toLocaleString()} records. The current project and approved prose will remain unchanged.</p><Input className="mt-3 max-w-md bg-background" value={restoreTitle} onChange={(event) => setRestoreTitle(event.target.value)} placeholder="Optional name for restored copy" aria-label="Restored project name" /><Button className="mt-3" onClick={() => void restore()} disabled={busy !== null}><RotateCcw className="mr-2 h-4 w-4" />{busy === 'restore' ? 'Restoring and verifying…' : 'Restore as new project'}</Button></div> : null}
    </section>
  )
}
