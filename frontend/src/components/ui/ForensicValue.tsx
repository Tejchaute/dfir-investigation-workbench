import type { HTMLAttributes } from 'react'
import { cn } from '../../utils'

export function MonospaceValue({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <code className={cn('forensic-mono text-sm text-text-primary', className)} {...props} />
}

export function HashValue({ value, label = 'SHA-256' }: { value: string; label?: string }) {
  return <span className="inline-flex max-w-full items-baseline gap-2"><span className="shrink-0 text-xs font-semibold uppercase text-text-muted">{label}</span><MonospaceValue>{value}</MonospaceValue></span>
}

export function TimestampValue({ value, semantics }: { value: string | null; semantics?: string }) {
  if (!value) return <span className="text-sm text-text-muted">Timestamp unavailable</span>
  return <span className="inline-flex flex-col gap-0.5"><time className="forensic-mono text-sm" dateTime={value}>{value}</time>{semantics && <span className="text-xs text-text-muted">{semantics}</span>}</span>
}
