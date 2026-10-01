export function withoutNumberedPrefix(
  title: string | null | undefined,
  kind: 'chapter' | 'scene',
): string {
  const value = String(title || '').trim()
  if (!value) return ''
  if (new RegExp(`^${kind}\\s+\\d+$`, 'i').test(value)) return ''
  const cleaned = value.replace(
    new RegExp(`^${kind}\\s+\\d+\\s*(?::|[-–—.]\\s*)`, 'i'),
    '',
  ).trim()
  return cleaned || value
}

export function numberedTitle(
  kind: 'chapter' | 'scene',
  number: string | number,
  title: string | null | undefined,
): string {
  const label = `${kind[0].toUpperCase()}${kind.slice(1)} ${number}`
  const cleaned = withoutNumberedPrefix(title, kind)
  return cleaned ? `${label}: ${cleaned}` : label
}
