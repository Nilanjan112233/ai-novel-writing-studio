import type { StoryArc } from '@/types'


const columns = [
  ['idea', 'Idea'],
  ['discussion', 'Discussion'],
  ['outline', 'Outline'],
  ['development', 'Development'],
  ['approved', 'Approved'],
  ['active', 'Active'],
  ['draftable', 'Draftable'],
  ['completed', 'Completed'],
  ['archived', 'Archived'],
] as const

function lifecycle(arc: StoryArc) {
  if (arc.development_status) return arc.development_status
  const compatibility = {
    draft: 'idea',
    discussed: 'discussion',
    approved: 'approved',
    active: 'active',
    completed: 'completed',
    archived: 'archived',
  } as const
  return compatibility[arc.approval_status || 'draft']
}


export default function ArcBoard({ arcs }: { arcs: StoryArc[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5" data-testid="arc-board">
      {columns.map(([status, label]) => {
        const entries = arcs.filter((arc) => lifecycle(arc) === status)
        return (
          <section key={status} className="min-w-0 rounded-md border bg-muted/30 p-3" data-testid={`arc-column-${status}`}>
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="font-semibold">{label}</h3>
              <span className="rounded bg-background px-2 py-0.5 text-xs">{entries.length}</span>
            </div>
            <div className="space-y-2">
              {entries.length === 0 ? (
                <p className="text-xs text-muted-foreground">No arcs</p>
              ) : entries.map((arc) => (
                <article key={arc.arc_id || arc.title} className="rounded-md border bg-background p-3">
                  <h4 className="break-words text-sm font-semibold">{arc.title}</h4>
                  <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">{arc.goal || arc.purpose || 'Goal remains open.'}</p>
                  <div className="mt-3 flex flex-wrap gap-1 text-[11px]">
                    <span className="rounded bg-muted px-2 py-1">{(arc.focus_role || 'future').toUpperCase()}</span>
                    <span className="rounded bg-muted px-2 py-1">Maturity {arc.arc_maturity_score || 0}</span>
                    <span className="rounded bg-muted px-2 py-1">{arc.readiness_status || 'NOT_READY'}</span>
                    <span className="rounded bg-muted px-2 py-1">
                      Chapters {arc.chapter_range?.length === 2 ? `${arc.chapter_range[0] ?? '?'}-${arc.chapter_range[1] ?? '?'}` : 'unknown'}
                    </span>
                    {arc.drafting_eligible ? <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">Draftable</span> : null}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
