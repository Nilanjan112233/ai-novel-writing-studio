'use client'

import { AlertTriangle, RotateCcw, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { OperationFailure } from '@/store/projectStore'

export default function OperationFailureBanner({
  failure,
  developerMode = false,
  onRetry,
  onDismiss,
  onNavigate,
}: {
  failure: OperationFailure | null
  developerMode?: boolean
  onRetry: () => Promise<void>
  onDismiss: () => void
  onNavigate: (destination: string) => void
}) {
  if (!failure) return null
  return (
    <section
      className="mx-3 mt-3 rounded-xl border border-red-300 bg-red-50 p-4 text-red-950 shadow-sm sm:mx-6 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100"
      role="alert"
      aria-live="assertive"
      data-testid="operation-failure"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold">{failure.operation} needs your attention</h2>
          <p className="mt-1 text-sm">{failure.explanation}</p>
          <p className="mt-1 text-sm font-medium">{failure.safety}</p>
          {failure.referenceId ? (
            <p className="mt-2 text-xs text-red-800 dark:text-red-200">
              Support reference: <span className="font-mono">{failure.referenceId}</span>
            </p>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2">
            {failure.retry ? (
              <Button size="sm" onClick={() => void onRetry()}>
                <RotateCcw className="mr-2 h-4 w-4" />Retry safely
              </Button>
            ) : null}
            {failure.destination ? (
              <Button size="sm" variant="outline" onClick={() => onNavigate(failure.destination!)}>
                Open the blocking item
              </Button>
            ) : null}
            <Button size="sm" variant="ghost" onClick={onDismiss}>Acknowledge</Button>
          </div>
          {developerMode && failure.technicalDetails ? (
            <details className="mt-3 text-xs" data-testid="operation-failure-technical">
              <summary className="cursor-pointer font-medium">Technical details</summary>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-red-200 bg-background/70 p-2">
                {failure.technicalDetails}
              </pre>
            </details>
          ) : null}
        </div>
        <button type="button" onClick={onDismiss} aria-label="Acknowledge operation failure" className="rounded p-1 hover:bg-red-100 dark:hover:bg-red-900/50">
          <X className="h-4 w-4" />
        </button>
      </div>
    </section>
  )
}
