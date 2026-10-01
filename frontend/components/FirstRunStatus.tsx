'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Loader2, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { operationsApi } from '@/lib/api'

type Readiness = {
  status: 'ready' | 'offline_ready' | 'blocked'
  summary: string
  first_run: boolean
  existing_work_available: boolean
  app_version: string
  checks: Record<string, { status: string; explanation: string; destination?: string | null }>
}

export default function FirstRunStatus() {
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    operationsApi.getReadiness()
      .then((value) => active && setReadiness(value))
      .catch(() => active && setFailed(true))
    return () => { active = false }
  }, [])

  if (!readiness && !failed) {
    return <div className="mx-auto mt-10 flex max-w-3xl items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/10 p-4 text-sm text-slate-200" aria-live="polite"><Loader2 className="h-4 w-4 animate-spin" />Checking local readiness…</div>
  }
  if (failed) {
    return (
      <div className="mx-auto mt-10 max-w-3xl rounded-xl border border-red-300/40 bg-red-950/40 p-5 text-left text-red-100" role="alert" data-testid="first-run-unavailable">
        <div className="flex gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" /><div><h2 className="font-semibold">NovelForge could not reach its local service</h2><p className="mt-1 text-sm">Your stored work has not been changed. Start NovelForge and MongoDB, then reload this page.</p></div></div>
      </div>
    )
  }
  const ai = readiness!.checks.ai
  const ready = readiness!.status === 'ready'
  return (
    <section className="mx-auto mt-10 max-w-3xl rounded-xl border border-white/20 bg-white/10 p-5 text-left text-white shadow-xl backdrop-blur" data-testid="first-run-status" aria-live="polite">
      <div className="flex items-start gap-3">
        {ready ? <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-emerald-300" /> : <WifiOff className="mt-0.5 h-6 w-6 shrink-0 text-amber-300" />}
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{readiness!.first_run ? 'Welcome — let’s get NovelForge ready' : readiness!.summary}</h2>
          <p className="mt-1 text-sm text-slate-200">{ai.explanation}</p>
          {!ready && readiness!.existing_work_available ? <p className="mt-2 text-sm font-medium text-emerald-200">Your existing projects remain available while AI is offline or being configured.</p> : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <Button asChild size="sm"><Link href="/projects">{readiness!.first_run ? 'Create your first project' : 'Open projects'}</Link></Button>
            {ai.status !== 'ready' ? <Button asChild size="sm" variant="outline" className="border-white/30 bg-white/10 hover:bg-white/20"><Link href="/settings#ai-provider">Set up AI</Link></Button> : null}
          </div>
        </div>
        <span className="text-xs text-slate-300">{readiness!.app_version}</span>
      </div>
    </section>
  )
}

