'use client'

import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Download, Loader2, RefreshCw, Send, ShieldCheck, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { operationsApi } from '@/lib/api'

type Readiness = {
  status: string
  summary: string
  app_version: string
  schema_version: number
  last_backup_at?: string | null
  checks: Record<string, { status: string; explanation: string; action?: string | null }>
}

type PrivacySummary = {
  locations?: { backup_folder?: string; support_folder?: string; project_storage?: string }
  hosted_saas_supported?: boolean
}

const labels: Record<string, string> = {
  database: 'Project storage',
  database_version: 'Data compatibility',
  backup_storage: 'Backup storage',
  export_storage: 'Publication storage',
  ai: 'AI assistance',
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function OperationalReadinessPanel() {
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [privacy, setPrivacy] = useState<PrivacySummary | null>(null)
  const [busy, setBusy] = useState<string | null>('readiness')
  const [category, setCategory] = useState('bug')
  const [message, setMessage] = useState('')
  const [includeDiagnostics, setIncludeDiagnostics] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setBusy('readiness'); setError('')
    try {
      const [nextReadiness, nextPrivacy] = await Promise.all([operationsApi.getReadiness(), operationsApi.getPrivacy()])
      setReadiness(nextReadiness); setPrivacy(nextPrivacy)
    } catch {
      setError('NovelForge could not check local readiness. Your existing work has not been changed.')
    } finally { setBusy(null) }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const createSupportBundle = async () => {
    setBusy('support'); setError(''); setNotice('')
    try {
      const result = await operationsApi.createSupportBundle()
      const blob = await operationsApi.downloadSupportBundle(result.support_id)
      downloadBlob(blob, `novelforge-support-${result.support_id.slice(0, 8)}.zip`)
      setNotice(`Diagnostic bundle created. Story content and credentials were not included. Support reference: ${result.support_id}`)
    } catch { setError('The diagnostic bundle could not be created. No data was shared.') }
    finally { setBusy(null) }
  }

  const submitFeedback = async () => {
    if (message.trim().length < 3) return
    setBusy('feedback'); setError(''); setNotice('')
    try {
      const result = await operationsApi.submitFeedback({ category, message: message.trim(), include_diagnostics: includeDiagnostics })
      setNotice(`${result.explanation} Reference: ${result.feedback_id}`)
      setMessage('')
    } catch { setError('Feedback could not be saved. Your story work is unchanged; copy your message before retrying.') }
    finally { setBusy(null) }
  }

  const createAllBackups = async () => {
    setBusy('all-backups'); setError(''); setNotice('')
    try {
      const result = await operationsApi.createAllBackups()
      setNotice(result.complete
        ? `${result.succeeded} project backup${result.succeeded === 1 ? '' : 's'} completed in the protected backup folder.`
        : `${result.succeeded} backups completed; ${result.failed} need attention. Existing work was not changed.`)
    } catch {
      setError('NovelForge could not complete the all-project backup. Existing projects are unchanged; retry after checking storage.')
    } finally { setBusy(null) }
  }

  return (
    <section className="rounded-xl border bg-card p-5 space-y-5" data-testid="operational-readiness">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="text-xl font-semibold">NovelForge readiness</h2><p className="mt-1 text-sm text-muted-foreground">Check what is ready locally, what needs attention, and whether AI is available. AI outages never hide existing projects.</p></div>
        <Button size="sm" variant="outline" onClick={() => void refresh()} disabled={busy !== null}><RefreshCw className={`mr-2 h-4 w-4 ${busy === 'readiness' ? 'animate-spin' : ''}`} />Check again</Button>
      </div>
      {error ? <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900"><AlertTriangle className="mr-2 inline h-4 w-4" />{error}</div> : null}
      {notice ? <div role="status" className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900">{notice}</div> : null}
      {!readiness ? <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Checking local services…</div> : (
        <>
          <div className={`rounded-lg border p-4 ${readiness.status === 'ready' ? 'border-emerald-200 bg-emerald-50/60' : readiness.status === 'blocked' ? 'border-red-200 bg-red-50/60' : 'border-amber-200 bg-amber-50/60'}`}>
            <div className="flex items-start gap-3">{readiness.status === 'ready' ? <CheckCircle2 className="h-5 w-5 text-emerald-700" /> : readiness.status === 'blocked' ? <AlertTriangle className="h-5 w-5 text-red-700" /> : <WifiOff className="h-5 w-5 text-amber-700" />}<div><p className="font-semibold">{readiness.summary}</p><p className="mt-1 text-xs text-muted-foreground">NovelForge {readiness.app_version} · data format {readiness.schema_version}</p></div></div>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {Object.entries(readiness.checks).map(([key, check]) => (
              <div key={key} className="rounded-lg border p-3"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-semibold">{labels[key] || key}</h3><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${check.status === 'ready' ? 'bg-emerald-100 text-emerald-800' : check.status === 'blocked' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>{check.status.replace(/_/g, ' ')}</span></div><p className="mt-2 text-xs text-muted-foreground">{check.explanation}</p></div>
            ))}
          </div>
        </>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border p-4"><div className="flex items-start gap-3"><ShieldCheck className="h-5 w-5 text-violet-600" /><div><h3 className="font-semibold">Private by default</h3><p className="mt-1 text-sm text-muted-foreground">Projects live in local MongoDB. AI receives only the context needed when you start an AI action. Diagnostic bundles omit story text, prompts, responses and credentials.</p></div></div>{privacy ? <><p className="mt-3 break-all text-xs text-muted-foreground">Project backups: {privacy.locations?.backup_folder || 'the configured local backup folder'}</p><p className="mt-1 text-xs text-muted-foreground">Hosted multi-tenant use is not supported by this beta.</p></> : null}<div className="mt-4 flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void createAllBackups()} disabled={busy !== null}>{busy === 'all-backups' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}{busy === 'all-backups' ? 'Backing up projects…' : 'Back up all projects'}</Button><Button size="sm" variant="outline" onClick={() => void createSupportBundle()} disabled={busy !== null}><Download className="mr-2 h-4 w-4" />{busy === 'support' ? 'Preparing…' : 'Download safe diagnostics'}</Button></div></div>
        <div className="rounded-lg border p-4"><h3 className="font-semibold">Private-beta feedback</h3><p className="mt-1 text-sm text-muted-foreground">Saved locally for this beta installation. Diagnostics are optional; story content is never attached automatically.</p><label className="mt-3 block text-xs font-semibold text-muted-foreground" htmlFor="beta-feedback-category">Feedback type</label><select id="beta-feedback-category" className="mt-1 h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}><option value="bug">Bug</option><option value="confusing-ux">Confusing experience</option><option value="ai-quality">AI quality problem</option><option value="performance">Performance problem</option><option value="feature-request">Feature request</option><option value="other">Other</option></select><Input className="mt-3" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="What happened, what did you expect, and what were you doing?" aria-label="Private beta feedback" /><label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={includeDiagnostics} onChange={(event) => setIncludeDiagnostics(event.target.checked)} />Include sanitized diagnostics</label><Button className="mt-3" size="sm" onClick={() => void submitFeedback()} disabled={busy !== null || message.trim().length < 3}><Send className="mr-2 h-4 w-4" />{busy === 'feedback' ? 'Saving…' : 'Save feedback locally'}</Button></div>
      </div>
    </section>
  )
}
