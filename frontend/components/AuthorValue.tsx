import type { ReactNode } from 'react'


export function authorText(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not recorded yet'
  if (typeof value === 'string') {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
      ? 'Linked story record'
      : value
  }
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.map(authorText).filter(Boolean).join(' · ')
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    const preferred = ['name', 'title', 'summary', 'description', 'fact', 'value', 'message', 'excerpt']
    for (const key of preferred) {
      if (source[key] !== undefined && typeof source[key] !== 'object') return authorText(source[key])
    }
    return Object.entries(source)
      .filter(([key]) => !(
        key === 'id'
        || key === '_id'
        || key.endsWith('_id')
        || key.endsWith('_ids')
        || ['metadata', 'payload', 'raw', 'chronology_position', 'execution_trace', 'cycle_number'].includes(key)
      ))
      .slice(0, 6)
      .map(([key, item]) => `${key.replaceAll('_', ' ')}: ${authorText(item)}`)
      .join(' · ') || 'Supporting project evidence'
  }
  return String(value)
}

export function EvidenceList({ values, empty = 'No supporting evidence was recorded.' }: { values?: unknown[]; empty?: ReactNode }) {
  const items = (values || []).filter((value) => value !== null && value !== undefined)
  if (!items.length) return <p className="text-sm text-muted-foreground">{empty}</p>
  return (
    <ul className="space-y-2 text-sm">
      {items.map((value, index) => (
        <li key={`${authorText(value).slice(0, 80)}-${index}`} className="rounded-md bg-muted/60 p-2">{authorText(value)}</li>
      ))}
    </ul>
  )
}
