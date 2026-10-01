import { useEffect, useMemo, useState } from 'react'
import { Loader2, ScanSearch, Search, ShieldCheck } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { CanonConflict, CanonRecord, ManuscriptReport } from '@/types'
import { dataApi } from '@/lib/api'
import { authorText, EvidenceList } from '@/components/AuthorValue'


export default function CanonDashboard({
  projectId,
  records,
  conflicts,
  reports,
  busyId,
  onValidate,
  onReview,
  onConflictStatus,
  onRecordActive,
  onOpenQueue,
}: {
  projectId?: string
  records: CanonRecord[]
  conflicts: CanonConflict[]
  reports: ManuscriptReport[]
  busyId?: string | null
  onValidate: () => void
  onReview: () => void
  onConflictStatus: (conflictId: string, status: string) => void
  onRecordActive: (canonId: string, active: boolean) => void
  onOpenQueue?: () => void
}) {
  const [explorerRecords, setExplorerRecords] = useState<CanonRecord[]>(records)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [selected, setSelected] = useState<CanonRecord | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<Record<string, unknown> | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [proposedValue, setProposedValue] = useState('')
  const [proposalNotice, setProposalNotice] = useState('')
  const [recordLimit, setRecordLimit] = useState(60)
  useEffect(() => { setExplorerRecords(records) }, [records])
  useEffect(() => {
    if (!projectId) return
    let active = true
    dataApi.getCanonExplorer(projectId).then((value) => active && setExplorerRecords(value.records || [])).catch(() => undefined)
    return () => { active = false }
  }, [projectId])
  const types = useMemo(() => [...new Set(explorerRecords.map((item) => item.canon_type || 'general'))].sort(), [explorerRecords])
  const visible = explorerRecords.filter((item) => {
    const haystack = `${item.subject || ''} ${item.field || ''} ${item.fact || ''} ${JSON.stringify(item.value ?? '')}`.toLowerCase()
    return (!search || haystack.includes(search.toLowerCase()))
      && (typeFilter === 'all' || item.canon_type === typeFilter)
      && (statusFilter === 'all' || (statusFilter === 'active' ? item.active : !item.active))
  })
  const open = conflicts.filter((item) => item.status !== 'resolved')
  const grouped = visible.slice(0, recordLimit).reduce<Record<string, CanonRecord[]>>((result, record) => {
    const type = record.canon_type || 'general'
    result[type] = [...(result[type] || []), record]
    return result
  }, {})
  const proposeEdit = async () => {
    if (!projectId || !selected || !proposedValue.trim()) return
    await dataApi.proposeCanonExplorerEdit(projectId, selected.canon_id, { value: proposedValue, evidence: ['Author-proposed Canon Explorer edit'] })
    setProposalNotice('Impact preview created. The change is waiting in the Canon Proposal queue and has not been applied.')
    setProposedValue('')
  }
  const inspectRecord = async (item: CanonRecord) => {
    setSelected(item)
    setSelectedDetail(null)
    setProposalNotice('')
    if (!projectId) return
    setDetailLoading(true)
    try {
      setSelectedDetail(await dataApi.getCanonExplorerDetail(projectId, item.canon_id) as Record<string, unknown>)
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="space-y-5" data-testid="canon-dashboard">
      <div className="flex flex-wrap gap-2">
        <Button disabled={busyId === 'canon'} onClick={onValidate}>
          <ShieldCheck className="mr-1 h-4 w-4" /> Validate Canon
        </Button>
        <Button variant="outline" disabled={busyId === 'canon'} onClick={onReview}>
          <ScanSearch className="mr-1 h-4 w-4" /> Agent Review
        </Button>
        {onOpenQueue ? <Button variant="outline" onClick={onOpenQueue}>Review Canon Queue</Button> : null}
        {busyId === 'canon' ? <Loader2 className="h-4 w-4 animate-spin self-center" /> : null}
      </div>

      <section className="rounded-md border p-3" data-testid="canon-explorer-controls">
        <div className="flex items-center gap-2"><Search className="h-4 w-4 text-muted-foreground" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search all official canon" aria-label="Search all official canon" className="min-w-0 flex-1 rounded border bg-background px-3 py-2 text-sm" /></div>
        <div className="mt-2 flex flex-wrap gap-2">
          <select aria-label="Filter canon type" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)} className="rounded border bg-background px-2 py-1 text-sm"><option value="all">All types</option>{types.map((type) => <option key={type} value={type}>{type}</option>)}</select>
          <select aria-label="Filter canon status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)} className="rounded border bg-background px-2 py-1 text-sm"><option value="all">Active and inactive</option><option value="active">Active</option><option value="inactive">Inactive</option></select>
          <span className="self-center text-xs text-muted-foreground">{visible.length} of {explorerRecords.length} facts visible</span>
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-semibold">Official Canon Registry</h3>
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {Object.entries(grouped).map(([domain, items]) => (
            <article key={domain} className="rounded-md border p-3" data-testid="canon-domain">
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold capitalize">{domain}</p>
                <span className="rounded bg-muted px-2 py-0.5 text-xs">{items.length}</span>
              </div>
              <div className="mt-2 space-y-1 text-sm">
                {items.map((item) => (
                  <div key={item.canon_id || `${item.subject}:${item.field}`} className="rounded bg-muted/40 p-2">
                    <p><strong>{item.subject || 'Story fact'}</strong> — {(item.field || 'story fact').replaceAll('_', ' ')}</p>
                    <p className="mt-1 break-words text-xs text-muted-foreground">{item.fact || authorText(item.value)}</p>
                    <p className="mt-1 text-xs">Approved story source · confidence {Math.round(Number(item.confidence ?? (item.authority_level === 'approved' ? 1 : .9)) * 100)}%</p>
                    <div className="mt-1 flex gap-1"><Button size="sm" variant="outline" onClick={() => void inspectRecord(item)}>Inspect</Button><Button size="sm" variant="outline" onClick={() => onRecordActive(item.canon_id, !item.active)}>{item.active ? 'Deactivate' : 'Reactivate'}</Button></div>
                  </div>
                ))}
              </div>
            </article>
          ))}
          {!visible.length ? <p className="text-sm text-muted-foreground">No canon facts match these filters.</p> : null}
        </div>
        {visible.length > recordLimit ? <Button className="mt-3" variant="outline" onClick={() => setRecordLimit((value) => value + 60)}>Show 60 more canon facts</Button> : null}
      </section>

      {selected ? <section className="rounded-md border p-4" data-testid="canon-record-detail">
        <div className="flex justify-between gap-2"><div><p className="text-xs uppercase text-muted-foreground">Authoritative fact detail</p><h3 className="font-semibold">{selected.subject || 'Story fact'} — {(selected.field || 'story fact').replaceAll('_', ' ')}</h3></div><Button variant="outline" size="sm" onClick={() => setSelected(null)}>Close</Button></div>
        <dl className="mt-3 grid gap-2 text-sm md:grid-cols-2"><div><dt className="font-semibold">Value</dt><dd>{authorText(selected.value ?? selected.fact)}</dd></div><div><dt className="font-semibold">Origin</dt><dd>{selected.source_collection ? selected.source_collection.replaceAll('_', ' ') : 'Approved story content'}</dd></div><div><dt className="font-semibold">Version</dt><dd>{selected.source_version || 1}</dd></div><div><dt className="font-semibold">Status</dt><dd>{selected.active ? 'Active official canon' : 'Inactive history'}</dd></div></dl>
        <details className="mt-3 text-sm" open><summary className="cursor-pointer font-semibold">Evidence and approval history</summary>
          {detailLoading ? <p className="mt-2 text-muted-foreground" role="status">Loading source evidence…</p> : <div className="mt-2 space-y-3">
            <div><p className="font-medium">Supporting evidence</p><EvidenceList values={(selectedDetail?.evidence as unknown[]) || selected.evidence || [selected.fact]} /></div>
            {selectedDetail?.originating_chapter ? <p><strong>Originating chapter:</strong> Chapter {String(selectedDetail.originating_chapter)}</p> : null}
            <div><p className="font-medium">Approval history</p>{Array.isArray(selectedDetail?.approval_history) && selectedDetail.approval_history.length
              ? <EvidenceList values={selectedDetail.approval_history.map((item) => {
                  const row = item as Record<string, unknown>
                  return `${String(row.status || row.decision || 'Reviewed')} · ${String(row.review_note || row.note || row.source_type || 'Canon proposal review')}`
                })} />
              : <p className="text-muted-foreground">This fact came directly from approved story content; no separate proposal decisions are recorded.</p>}
            </div>
            {Array.isArray(selectedDetail?.versions) ? <p><strong>Recorded versions:</strong> {selectedDetail.versions.length}</p> : null}
          </div>}
        </details>
        {projectId ? <div className="mt-3 rounded border p-3"><p className="text-sm font-semibold">Propose a governed edit</p><p className="text-xs text-muted-foreground">An impact preview and proposal are created first. Official canon is never overwritten here.</p><div className="mt-2 flex gap-2"><input value={proposedValue} onChange={(event) => setProposedValue(event.target.value)} aria-label="Proposed canon value" className="min-w-0 flex-1 rounded border bg-background px-2 py-1 text-sm" /><Button size="sm" onClick={() => void proposeEdit()}>Preview & propose</Button></div>{proposalNotice ? <p className="mt-2 text-xs text-emerald-700">{proposalNotice}</p> : null}</div> : null}
      </section> : null}

      <section>
        <h3 className="mb-3 font-semibold">Conflicts</h3>
        <div className="space-y-2">
          {open.map((conflict) => (
            <article key={conflict.conflict_id} className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-950" data-testid="canon-conflict">
              <p className="font-semibold">{(conflict.conflict_type || 'canon conflict').replaceAll('_', ' ')}</p>
              <p className="mt-1">{conflict.message}</p>
              <p className="mt-1 text-xs">{conflict.subject}.{conflict.field} · {conflict.severity}</p>
              {conflict.impact ? <p className="mt-2 rounded bg-white/70 p-2"><strong>Impact:</strong> {conflict.impact}</p> : null}
              {conflict.original_source ? (
                <details className="mt-2">
                  <summary className="cursor-pointer font-medium">Original and conflicting evidence</summary>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    <div className="rounded bg-white/70 p-2 text-xs"><strong>Original</strong><p className="mt-1">{authorText(conflict.original_source)}</p></div>
                    <div className="rounded bg-white/70 p-2 text-xs"><strong>Conflicting</strong><div className="mt-1"><EvidenceList values={conflict.conflicting_sources || []} /></div></div>
                  </div>
                  {conflict.affected_locations?.length ? <p className="mt-2 text-xs">Affected: {conflict.affected_locations.join(', ')}</p> : null}
                </details>
              ) : null}
              <div className="mt-2 flex gap-2">
                {conflict.status === 'open' ? (
                  <Button size="sm" variant="outline" onClick={() => onConflictStatus(conflict.conflict_id, 'acknowledged')}>
                    Acknowledge
                  </Button>
                ) : null}
                <Button size="sm" variant="outline" onClick={() => onConflictStatus(conflict.conflict_id, 'resolved')}>
                  Mark Resolved
                </Button>
              </div>
            </article>
          ))}
          {!open.length ? <p className="text-sm text-muted-foreground">No open canon conflicts.</p> : null}
        </div>
      </section>

      <section>
        <h3 className="mb-3 font-semibold">Canon Review History</h3>
        {reports.map((report) => (
          <article key={report.report_id} className="mb-2 rounded-md border p-3 text-sm">
            <strong>{report.result}</strong> · {report.findings.length} findings
            {report.recommendations?.length ? <p className="mt-1 text-muted-foreground">{report.recommendations.join(' ')}</p> : null}
          </article>
        ))}
      </section>
    </div>
  )
}
