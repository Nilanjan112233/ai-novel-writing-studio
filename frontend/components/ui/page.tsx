// Shared layout building blocks so every screen uses the same spacing,
// type scale, cards and states.

import type { ReactNode } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <header className={cn('flex flex-wrap items-start justify-between gap-4', className)}>
      <div className="min-w-0 max-w-3xl">
        {eyebrow ? <p className="mb-1 text-sm font-medium text-primary">{eyebrow}</p> : null}
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? <p className="mt-1.5 text-[15px] leading-6 text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  )
}

export function Card({
  children,
  className,
  as: Tag = 'section',
  testId,
}: {
  children: ReactNode
  className?: string
  as?: 'section' | 'div' | 'article'
  testId?: string
}) {
  return (
    <Tag className={cn('min-w-0 rounded-xl border bg-card p-5 text-card-foreground shadow-soft', className)} data-testid={testId}>
      {children}
    </Tag>
  )
}

export function CardTitle({ children, description, action }: { children: ReactNode; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-lg font-semibold leading-tight">{children}</h2>
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action}
    </div>
  )
}

const badgeTones = {
  neutral: 'bg-muted text-muted-foreground',
  success: 'bg-success/15 text-success',
  warning: 'bg-warning/15 text-warning',
  danger: 'bg-destructive/15 text-destructive',
  info: 'bg-primary/10 text-primary',
} as const

export function StatusBadge({ tone = 'neutral', children, className }: { tone?: keyof typeof badgeTones; children: ReactNode; className?: string }) {
  return <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium', badgeTones[tone], className)}>{children}</span>
}

export function ProgressBar({ value, className, label }: { value: number; className?: string; label?: string }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div
      className={cn('h-2 w-full overflow-hidden rounded-full bg-muted', className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped}
      aria-label={label}
    >
      <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${clamped}%` }} />
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center rounded-xl border border-dashed bg-muted/30 px-6 py-10 text-center', className)} data-testid="empty-state">
      {icon ? <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">{icon}</div> : null}
      <p className="text-base font-semibold">{title}</p>
      {description ? <p className="mt-1 max-w-md text-sm leading-6 text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-4 flex flex-wrap justify-center gap-2">{action}</div> : null}
    </div>
  )
}

export function LoadingState({ children = 'Loading…', className }: { children?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex min-h-32 items-center justify-center gap-2 rounded-xl text-sm text-muted-foreground', className)} role="status" aria-live="polite">
      <Loader2 className="h-4 w-4 animate-spin" />
      {children}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  onRetry,
  className,
}: {
  title?: ReactNode
  description?: ReactNode
  onRetry?: () => void
  className?: string
}) {
  return (
    <div className={cn('flex items-start gap-3 rounded-xl border border-warning/40 bg-warning/10 p-4 text-sm', className)} role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        {description ? <p className="mt-1 text-muted-foreground">{description}</p> : null}
        <p className="mt-1 text-muted-foreground">Your saved work is safe.</p>
        {onRetry ? <Button className="mt-3" size="sm" variant="outline" onClick={onRetry}>Try again</Button> : null}
      </div>
    </div>
  )
}
