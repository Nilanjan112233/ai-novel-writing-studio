import type { StoryArc, TimelineEntryV2 } from '@/types'


const certaintyStyles = {
  known: 'border-emerald-300 bg-emerald-50',
  probable: 'border-amber-300 bg-amber-50',
  unknown: 'border-dashed border-slate-400 bg-slate-50',
}


export default function TimelineV2({
  entries,
  arcs,
}: {
  entries: TimelineEntryV2[]
  arcs: StoryArc[]
}) {
  const entryById = new Map(entries.map((entry) => [entry.entry_id, entry]))
  const arcIds = [
    ...arcs.map((arc) => arc.arc_id),
    ...entries.map((entry) => entry.arc_id || 'unassigned'),
  ].filter((value, index, values) => value && values.indexOf(value) === index)

  return (
    <div className="space-y-4" data-testid="timeline-v2">
      {arcIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">No timeline anchors yet. Unknown future space is valid.</p>
      ) : arcIds.map((arcId) => {
        const arc = arcs.find((item) => item.arc_id === arcId)
        const arcEntries = entries
          .filter((entry) => (entry.arc_id || 'unassigned') === arcId)
          .sort((left, right) => Number(left.order || 0) - Number(right.order || 0))
        return (
          <section key={arcId} className="rounded-md border p-4" data-testid="timeline-arc">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold">{arc?.title || 'Unassigned future'}</h3>
              <span className="text-xs text-muted-foreground">{arcEntries.length} anchors</span>
            </div>
            {arcEntries.length === 0 ? (
              <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                Placeholder: this arc is intentionally unknown.
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-3">
                {(['known', 'probable', 'unknown'] as const).map((certainty) => (
                  <div key={certainty}>
                    <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">{certainty}</p>
                    <div className="space-y-2">
                      {arcEntries.filter((entry) => entry.certainty === certainty).map((entry) => (
                        <article key={entry.entry_id} className={`rounded-md border p-3 text-sm ${certaintyStyles[certainty]}`} data-testid={`timeline-${certainty}`}>
                          <h4 className="font-semibold">{entry.title || 'Unknown future event'}</h4>
                          <p className="mt-1 break-words text-muted-foreground">
                            {entry.summary || (certainty === 'unknown' ? 'Details intentionally unresolved.' : 'No summary yet.')}
                          </p>
                          <p className="mt-2 text-xs">{entry.status} · {entry.importance}</p>
                          {(entry.dependencies || []).length ? (
                            <div className="mt-2 border-t pt-2 text-xs" data-testid="timeline-dependencies">
                              <p className="font-medium">Depends on</p>
                              <div className="mt-1 flex flex-wrap gap-1">
                                {(entry.dependencies || []).map((dependency) => {
                                  const source = entryById.get(dependency)
                                  return (
                                    <span key={dependency} className={`rounded px-2 py-1 ${source ? 'bg-white/70' : 'bg-rose-100 text-rose-800'}`}>
                                      {source?.title || `Missing: ${dependency}`} → {entry.title}
                                    </span>
                                  )
                                })}
                              </div>
                            </div>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}
