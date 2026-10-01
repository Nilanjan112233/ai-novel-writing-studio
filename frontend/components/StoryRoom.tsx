import type { StoryRoom as StoryRoomData } from '@/types'


function Lane({
  title,
  count,
  children,
}: {
  title: string
  count: number
  children: React.ReactNode
}) {
  return (
    <section className="min-w-0 rounded-md border p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="font-semibold">{title}</h3>
        <span className="rounded bg-muted px-2 py-0.5 text-xs">{count}</span>
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  )
}


export default function StoryRoom({ room }: { room: StoryRoomData | null }) {
  if (!room) {
    return <p className="text-sm text-muted-foreground">Story Room is synchronizing.</p>
  }
  return (
    <div className="space-y-4" data-testid="story-room">
      <div className="rounded-md border bg-muted/30 p-3">
        <p className="text-xs font-semibold uppercase text-muted-foreground">Current Arc</p>
        <p className="mt-1 text-lg font-semibold">{room.current_arc?.title || 'No current arc selected'}</p>
      </div>
      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
        <Lane title="Active Discussions" count={room.active_discussions.length}>
          {room.active_discussions.slice(0, 8).map((item) => (
            <p key={item.id} className="rounded bg-muted/40 p-2 text-sm">{item.summary || item.content}</p>
          ))}
        </Lane>
        <Lane title="Open Planning" count={room.open_planning_items.length}>
          {room.open_planning_items.slice(0, 12).map((item) => (
            <p key={item.item_id} className="rounded bg-muted/40 p-2 text-sm">
              {item.title} <span className="text-xs text-muted-foreground">({item.priority})</span>
            </p>
          ))}
        </Lane>
        <Lane title="Blocked" count={room.blocked_items.length}>
          {room.blocked_items.slice(0, 8).map((item) => (
            <p key={item.dependency_id} className="rounded bg-amber-50 p-2 text-sm text-amber-900">
              {item.validation_reason || item.dependency_type}
            </p>
          ))}
        </Lane>
        <Lane title="Agent Proposals" count={room.agent_proposals.length}>
          {room.agent_proposals.slice(0, 8).map((item) => (
            <p key={item.id} className="rounded bg-muted/40 p-2 text-sm">
              <strong>{item.author}</strong>: {item.summary || item.content}
            </p>
          ))}
        </Lane>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <Lane title="Draft Queue" count={room.draft_queue?.length || 0}>
          {(room.draft_queue || []).slice(0, 8).map((item) => (
            <p key={item.draft_id} className="rounded bg-muted/40 p-2 text-sm">
              Version {item.version_number} · {item.generated_by}
            </p>
          ))}
        </Lane>
        <Lane title="Review Queue" count={room.review_queue?.length || 0}>
          {(room.review_queue || []).slice(0, 8).map((item) => (
            <p key={item.draft_id} className="rounded bg-amber-50 p-2 text-sm text-amber-900">
              Version {item.version_number} · awaiting author approval
            </p>
          ))}
        </Lane>
        <Lane title="Continuity Warnings" count={room.continuity_warnings?.length || 0}>
          {(room.continuity_warnings || []).slice(0, 8).map((item) => (
            <p key={item.report_id || item.id} className="rounded bg-red-50 p-2 text-sm text-red-900">
              {item.result}: {[...(item.warnings || []), ...(item.contradictions || [])].join(' ') || 'Review required'}
            </p>
          ))}
        </Lane>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <Lane title="Editorial Queue" count={room.editorial_queue?.length || 0}>
          {(room.editorial_queue || []).slice(0, 8).map((item) => (
            <p key={`${item.subject_type}-${item.subject_id}`} className="rounded bg-muted/40 p-2 text-sm">
              {item.subject_type} · missing {item.missing_reviews.join(', ')}
            </p>
          ))}
        </Lane>
        <Lane title="Revision Queue" count={room.revision_queue?.length || 0}>
          {(room.revision_queue || []).slice(0, 8).map((item) => (
            <p key={item.branch_id} className="rounded bg-amber-50 p-2 text-sm text-amber-900">
              {item.title} · {item.status}
            </p>
          ))}
        </Lane>
        <Lane title="Editorial Blockers" count={room.editorial_blockers?.length || 0}>
          {(room.editorial_blockers || []).slice(0, 8).map((item) => (
            <p key={item.report_id} className="rounded bg-red-50 p-2 text-sm text-red-900">
              {item.subject_type} score {item.score}: {item.blockers.join(' ') || 'Editorial attention required'}
            </p>
          ))}
        </Lane>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        <Lane title="Manuscript Queue" count={room.manuscript_queue?.length || 0}>
          {(room.manuscript_queue || []).slice(0, 8).map((item) => (
            <p key={item.manuscript_id} className="rounded bg-muted/40 p-2 text-sm">
              {item.title} · {item.status} · version {item.version}
            </p>
          ))}
        </Lane>
        <Lane title="Canon Queue" count={room.canon_queue?.length || 0}>
          {(room.canon_queue || []).slice(0, 8).map((item) => (
            <p key={item.type} className="rounded bg-amber-50 p-2 text-sm text-amber-900">
              {item.title} · {item.open_conflicts} open conflicts
            </p>
          ))}
        </Lane>
        <Lane title="Canon Conflicts" count={room.conflict_queue?.length || 0}>
          {(room.conflict_queue || []).slice(0, 8).map((item) => (
            <p key={item.conflict_id} className="rounded bg-red-50 p-2 text-sm text-red-900">
              {item.domain}: {item.message}
            </p>
          ))}
        </Lane>
      </div>
      <p className="text-xs text-muted-foreground">
        Generation history: {room.generation_history?.total_versions || 0} immutable versions
      </p>
    </div>
  )
}
