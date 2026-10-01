import type { ReadinessItem, ReadinessReport, StoryArc } from '@/types'


export default function ReadinessDashboard({
  items,
  reports,
  arcs,
}: {
  items: ReadinessItem[]
  reports: ReadinessReport[]
  arcs: StoryArc[]
}) {
  const ready = items.filter((item) => ['approved', 'ready'].includes(item.status))
  const blocked = items.filter(
    (item) => item.blocking && !['approved', 'ready'].includes(item.status),
  )
  const missing = items.filter((item) => item.status === 'missing')
  const recommended = items.filter(
    (item) => item.priority === 'recommended' && !['approved', 'ready'].includes(item.status),
  )
  const groups = [
    ['Ready', ready],
    ['Blocked', blocked],
    ['Missing', missing],
    ['Recommended', recommended],
  ] as const

  return (
    <div className="space-y-4" data-testid="readiness-dashboard">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {groups.map(([label, values]) => (
          <div key={label} className="rounded-md border p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-semibold">{values.length}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {reports.length === 0 ? (
          <p className="text-sm text-muted-foreground">No arc readiness reports yet.</p>
        ) : reports.map((report) => {
          const arc = arcs.find((item) => item.arc_id === report.arc_id)
          return (
            <div key={report.arc_id || 'project'} className="rounded-md border p-3" data-testid="readiness-report">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold">{arc?.title || 'Project readiness'}</h3>
                <span className={`rounded px-2 py-1 text-xs font-semibold ${report.status === 'READY' ? 'bg-emerald-100 text-emerald-800' : report.status === 'PARTIALLY_READY' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'}`}>
                  {report.status}
                </span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {report.satisfied_required_items}/{report.required_items} required items satisfied
              </p>
              <p className="mt-1 text-sm font-medium">
                Drafting: {report.drafting_eligible ? 'Eligible' : 'Blocked'}
              </p>
              {report.blockers.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {report.blockers.map((item) => (
                    <span key={item.item_id} className="rounded bg-muted px-2 py-1 text-xs">
                      {item.title}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
