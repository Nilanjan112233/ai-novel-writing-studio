"use client"

import { useState } from 'react'
import { ChevronDown, CircleHelp, Compass } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { ApplicationSurface } from '@/types'


export default function PageGuidance({ surface, onNavigate, onAsk }: { surface?: ApplicationSurface | null; onNavigate: (target: string) => void; onAsk: () => void }) {
  const [open, setOpen] = useState(false)
  if (!surface) return null
  return (
    <section className="border-b bg-sky-50/70 px-3 py-2 text-sky-950 sm:px-6" data-testid="page-guidance">
      <div className="flex min-w-0 items-center gap-3">
        <Compass className="h-4 w-4 shrink-0 text-sky-700" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{surface.label}</p>
          <p className="truncate text-xs text-sky-800">{surface.purpose}</p>
        </div>
        <Button size="sm" variant="ghost" onClick={onAsk}><CircleHelp className="mr-1 h-4 w-4" />Ask</Button>
        <button type="button" aria-label={`${open ? 'Hide' : 'Show'} page guidance`} aria-expanded={open} onClick={() => setOpen((value) => !value)} className="rounded-md p-2 hover:bg-sky-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600">
          <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>
      {open ? (
        <div className="mt-3 grid gap-3 text-sm lg:grid-cols-3" data-testid="page-guidance-detail">
          <div><strong>Why it matters</strong><p className="mt-1 text-sky-800">{surface.why_it_matters}</p></div>
          <div><strong>What to do here</strong><p className="mt-1 text-sky-800">{surface.what_to_do}</p></div>
          <div><strong>What happens next</strong><p className="mt-1 text-sky-800">{surface.what_happens_next}</p></div>
          {surface.actions.length ? <div className="flex flex-wrap gap-2 lg:col-span-3">{surface.actions.map((action) => <Button key={`${action.destination}-${action.label}`} size="sm" variant="outline" onClick={() => onNavigate(action.destination)}>{action.label}</Button>)}</div> : null}
        </div>
      ) : null}
    </section>
  )
}
