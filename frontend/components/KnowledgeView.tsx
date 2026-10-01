import type { KnowledgeEntry } from '@/types'


const layers = [
  ['READER_KNOWLEDGE', 'Reader Knowledge'],
  ['CHARACTER_KNOWLEDGE', 'Character Knowledge'],
  ['WORLD_TRUTH', 'World Truth'],
] as const


export default function KnowledgeView({ entries }: { entries: KnowledgeEntry[] }) {
  return (
    <div className="grid gap-3 lg:grid-cols-3" data-testid="knowledge-view">
      {layers.map(([type, label]) => {
        const items = entries.filter((entry) => entry.knowledge_type === type)
        return (
          <section key={type} className="min-w-0 rounded-md border p-3" data-testid={`knowledge-layer-${type.toLowerCase()}`}>
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="font-semibold">{label}</h3>
              <span className="rounded bg-muted px-2 py-0.5 text-xs">{items.length}</span>
            </div>
            <div className="space-y-3">
              {items.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing recorded.</p>
              ) : items.map((entry) => (
                <article key={entry.entry_id} className="rounded-md bg-muted/50 p-3 text-sm">
                  <h4 className="font-semibold">{entry.title}</h4>
                  <p className="mt-1 break-words">{entry.content}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Knows: {entry.known_by?.join(', ') || 'No one explicitly'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Does not know: {entry.not_known_by?.join(', ') || 'Not specified'}
                  </p>
                  <p className="mt-1 text-xs">
                    Confidence {Math.round(Number(entry.confidence || 0) * 100)}%
                    {entry.is_false ? ' · False belief' : ''}
                  </p>
                </article>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
