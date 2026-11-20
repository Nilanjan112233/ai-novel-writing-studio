import { useState } from 'react'
import { BookCheck, Download, FileArchive, History, Loader2, RotateCcw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { dataApi } from '@/lib/api'
import type {
  ChapterDraft,
  Manuscript,
  ManuscriptReport,
  ManuscriptVersion,
} from '@/types'


function resultTone(result: string) {
  if (result === 'PASS') return 'bg-emerald-100 text-emerald-800'
  if (result === 'FAIL') return 'bg-red-100 text-red-800'
  return 'bg-amber-100 text-amber-800'
}


export default function ManuscriptWorkspace({
  manuscripts,
  versions,
  reports,
  chapterDrafts,
  busyId,
  onCreate,
  onAssemble,
  onReview,
  onStatus,
  onRollback,
  onNavigate,
  projectId,
}: {
  manuscripts: Manuscript[]
  versions: ManuscriptVersion[]
  reports: ManuscriptReport[]
  chapterDrafts: ChapterDraft[]
  busyId?: string | null
  onCreate: (title?: string) => void
  onAssemble: (manuscriptId: string, chapterDraftIds: string[]) => void
  onReview: (manuscriptId: string) => void
  onStatus: (manuscriptId: string, status: string) => void
  onRollback: (manuscriptId: string, versionId: string) => void
  onNavigate?: (destination: string) => void
  projectId?: string
}) {
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const [publicationBlockers, setPublicationBlockers] = useState<Array<{ explanation: string; why_it_matters?: string; action: string; destination: string }>>([])
  const [publication, setPublication] = useState<{
    export_id: string
    artifacts: Record<string, { filename: string; bytes: number }>
    warnings?: string[]
  } | null>(null)
  const active = manuscripts.find((item) => item.active) || manuscripts[0]
  const approvedChapterIds = chapterDrafts
    .filter((item) => item.active && item.status === 'approved')
    .map((item) => item.draft_id)
  const manuscriptVersions = versions
    .filter((item) => item.manuscript_id === active?.manuscript_id)
    .sort((left, right) => right.version_number - left.version_number)
  const currentVersion = manuscriptVersions.find(
    (item) => item.version_id === active?.current_version_id,
  )
  const currentReports = reports.filter(
    (item) => !active || item.manuscript_id === active.manuscript_id,
  )

  const createPublicationPackage = async () => {
    if (!projectId || !active) return
    setExporting(true)
    setExportError('')
    try {
      const preflight = await dataApi.getPublicationPreflight(projectId, active.manuscript_id)
      if (!preflight.ready) {
        setPublicationBlockers(preflight.blocker_details || [])
        setExportError((preflight.blockers || []).join(' '))
        return
      }
      const result = await dataApi.createPublicationExport(projectId, active.manuscript_id)
      setPublication(result)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Publication export failed')
    } finally {
      setExporting(false)
    }
  }

  const checkPublicationReadiness = async () => {
    if (!projectId || !active) return
    setExporting(true)
    setExportError('')
    try {
      const preflight = await dataApi.getPublicationPreflight(projectId, active.manuscript_id)
      setPublicationBlockers(preflight.blocker_details || [])
      if (preflight.ready) setExportError('Publication checks passed. Approve the manuscript to create the export package.')
      else setExportError('Publication is waiting on the items below. Your manuscript is unchanged.')
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export checks could not run. Your book is unchanged.')
    } finally {
      setExporting(false)
    }
  }

  const downloadArtifact = async (kind: string, filename: string) => {
    if (!projectId || !publication) return
    const blob = await dataApi.downloadPublicationExport(projectId, publication.export_id, kind)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  }

  if (!active) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed bg-muted/30 px-6 py-10 text-center" data-testid="manuscript-workspace">
        <p className="text-base font-semibold">Put your book together</p>
        <p className="mt-1 max-w-lg text-sm leading-6 text-muted-foreground">
          This collects your approved chapters, in order, into one book. You can then have the AI read it through, approve it and export it as DOCX, EPUB, PDF, HTML, Markdown or plain text.
        </p>
        <Button className="mt-4" onClick={() => onCreate()}>Create the book</Button>
      </div>
    )
  }

  return (
    <div className="space-y-5" data-testid="manuscript-workspace">
      <div className="rounded-md border bg-muted/30 p-3 text-sm">
        <strong>Your approved chapters are copied in exactly as written.</strong>{' '}
        Editing a chapter later does not change this book until you assemble it again.
      </div>

      <section className="rounded-md border p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">{active.title}</h3>
            <p className="text-sm text-muted-foreground">
              {active.status} · active version {active.version || 'not assembled'}
            </p>
          </div>
          {currentVersion ? (
            <span className={`rounded px-2 py-1 text-sm font-semibold ${resultTone(currentVersion.validation_result)}`}>
              {currentVersion.validation_result}
            </span>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            disabled={busyId === active.manuscript_id || !approvedChapterIds.length}
            onClick={() => onAssemble(active.manuscript_id, approvedChapterIds)}
          >
            <BookCheck className="mr-1 h-4 w-4" /> Assemble Approved Chapters
          </Button>
          {currentVersion ? (
            <Button
              variant="outline"
              disabled={busyId === active.manuscript_id}
              onClick={() => onReview(active.manuscript_id)}
            >
              Review Manuscript
            </Button>
          ) : null}
          {active.status === 'draft' && currentVersion ? (
            <Button variant="outline" onClick={() => onStatus(active.manuscript_id, 'review')}>Begin Review</Button>
          ) : null}
          {active.status === 'review' && currentVersion?.validation_result !== 'FAIL' ? (
            <Button variant="outline" onClick={() => onStatus(active.manuscript_id, 'validated')}>Mark Validated</Button>
          ) : null}
          {active.status === 'validated' ? (
            <Button onClick={() => onStatus(active.manuscript_id, 'approved')}>Approve Manuscript</Button>
          ) : null}
          {active.status !== 'archived' ? (
            <Button variant="outline" onClick={() => onStatus(active.manuscript_id, 'archived')}>Archive</Button>
          ) : null}
          {busyId === active.manuscript_id ? <Loader2 className="h-4 w-4 animate-spin self-center" /> : null}
        </div>
      </section>

      <section className="rounded-md border border-violet-200 bg-violet-50/40 p-4" data-testid="publication-export">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold">Publication Export</h3>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Export only the approved, validated manuscript version. NovelForge includes a provenance manifest and never exports draft analysis caches.
            </p>
          </div>
          <Button
            disabled={!projectId || active.status !== 'approved' || !currentVersion || exporting}
            onClick={() => void createPublicationPackage()}
            data-testid="create-publication-export"
          >
            {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileArchive className="mr-2 h-4 w-4" />}
            Create Publication Package
          </Button>
          <Button variant="outline" disabled={!projectId || exporting} onClick={() => void checkPublicationReadiness()}>
            Check publication readiness
          </Button>
        </div>
        {active.status !== 'approved' ? <p className="mt-3 text-sm text-amber-800">Review, check and approve the book to unlock export.</p> : null}
        {exportError ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-800" role="alert">{exportError}</p> : null}
        {publicationBlockers.length ? <div className="mt-3 space-y-2" data-testid="publication-blockers">
          {publicationBlockers.map((blocker, index) => <article key={`${blocker.destination}-${index}`} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
            <p className="font-semibold">{blocker.explanation}</p>
            {blocker.why_it_matters ? <p className="mt-1 text-xs">Why it matters: {blocker.why_it_matters}</p> : null}
            {onNavigate ? <Button className="mt-2" size="sm" variant="outline" onClick={() => onNavigate(blocker.destination)}>{blocker.action}</Button> : null}
          </article>)}
        </div> : null}
        {publication ? (
          <div className="mt-4">
            <p className="text-sm font-medium">Export ready. Choose a format:</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(publication.artifacts).map(([kind, artifact]) => (
                <Button key={kind} size="sm" variant={kind === 'package' ? 'default' : 'outline'} onClick={() => void downloadArtifact(kind, artifact.filename)}>
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  {kind === 'package' ? 'Complete Package' : kind.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <section>
        <h3 className="mb-3 font-semibold">Version History</h3>
        <div className="space-y-2">
          {manuscriptVersions.map((version) => (
            <article key={version.version_id} className="rounded-md border p-3 text-sm" data-testid="manuscript-version">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold">
                  <History className="mr-1 inline h-4 w-4" />
                  Version {version.version_number} · {version.chapter_count} chapters
                </p>
                <span className={`rounded px-2 py-1 text-xs ${resultTone(version.validation_result)}`}>
                  {version.validation_result}
                </span>
              </div>
              {active.current_version_id !== version.version_id ? (
                <Button
                  className="mt-2"
                  size="sm"
                  variant="outline"
                  onClick={() => onRollback(active.manuscript_id, version.version_id)}
                >
                  <RotateCcw className="mr-1 h-3.5 w-3.5" /> Activate Version
                </Button>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-semibold">Validation And Review Reports</h3>
        <div className="grid gap-3 lg:grid-cols-2">
          {currentReports.map((report) => (
            <article key={report.report_id} className="rounded-md border p-3 text-sm" data-testid="manuscript-report">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold">{report.report_type.replaceAll('_', ' ')}</p>
                <span className={`rounded px-2 py-1 text-xs ${resultTone(report.result)}`}>{report.result}</span>
              </div>
              <p className="mt-2 text-muted-foreground">
                {report.findings.length} findings
                {report.recommendations?.length ? ` · ${report.recommendations.join(' ')}` : ''}
              </p>
              {report.findings.length ? <div className="mt-2 space-y-2">{report.findings.slice(0, 8).map((finding, index) => {
                const item = finding as Record<string, unknown>
                return <div key={index} className="rounded bg-muted/40 p-2"><p>{String(item.message || item.explanation || 'Review this publication check.')}</p>{item.action ? <p className="mt-1 text-xs font-medium">Next: {String(item.action)}</p> : null}</div>
              })}</div> : null}
            </article>
          ))}
          {!currentReports.length ? <p className="text-sm text-muted-foreground">No manuscript reports yet.</p> : null}
        </div>
      </section>
    </div>
  )
}
