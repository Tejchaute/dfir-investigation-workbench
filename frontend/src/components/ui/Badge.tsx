import type { HTMLAttributes } from 'react'
import { cn } from '../../utils'

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn('inline-flex items-center gap-1.5 rounded-sm border border-border-strong bg-surface-inset px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-text-secondary', className)} {...props} />
}

type Lifecycle = 'OPEN' | 'CLOSED' | 'ARCHIVED' | 'REVIEWED' | 'RESOLVED' | 'DISMISSED'
type ParserState = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED' | 'UNSUPPORTED'
type IntegrityState = 'MATCH' | 'MISMATCH' | 'UNKNOWN'
type ReportState = 'GENERATED' | 'FAILED'

const statusClasses: Record<Lifecycle | ParserState | IntegrityState | ReportState, string> = {
  OPEN: 'border-status-open/35 text-status-open', CLOSED: 'border-status-closed/35 text-status-closed', ARCHIVED: 'border-status-archived/35 text-status-archived',
  REVIEWED: 'border-accent/35 text-accent', RESOLVED: 'border-success/35 text-success', DISMISSED: 'border-text-muted/35 text-text-muted',
  PENDING: 'border-text-muted/35 text-text-secondary', RUNNING: 'border-parser-running/35 text-parser-running', COMPLETED: 'border-parser-complete/35 text-parser-complete',
  COMPLETED_WITH_WARNINGS: 'border-parser-warning/35 text-parser-warning', FAILED: 'border-parser-failed/35 text-parser-failed', UNSUPPORTED: 'border-text-muted/35 text-text-muted',
  MATCH: 'border-integrity-match/35 text-integrity-match', MISMATCH: 'border-integrity-mismatch/35 text-integrity-mismatch', UNKNOWN: 'border-integrity-unknown/35 text-integrity-unknown',
  GENERATED: 'border-success/35 text-success',
}

export function StatusBadge({ status }: { status: Lifecycle | ParserState | IntegrityState | ReportState }) { return <Badge className={statusClasses[status]}><span aria-hidden="true" className="size-1.5 rounded-full bg-current" />{status.replaceAll('_', ' ')}</Badge> }

export type Severity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
const severityClasses: Record<Severity, string> = { INFO: 'text-severity-info', LOW: 'text-severity-low', MEDIUM: 'text-severity-medium', HIGH: 'text-severity-high', CRITICAL: 'text-severity-critical' }
export function SeverityBadge({ severity }: { severity: Severity }) { return <Badge className={severityClasses[severity]}>Severity: {severity}</Badge> }

export type Confidence = 'LOW' | 'MEDIUM' | 'HIGH'
const confidenceClasses: Record<Confidence, string> = { LOW: 'text-confidence-low', MEDIUM: 'text-confidence-medium', HIGH: 'text-confidence-high' }
export function ConfidenceBadge({ confidence }: { confidence: Confidence }) { return <Badge className={confidenceClasses[confidence]}>Confidence: {confidence}</Badge> }
