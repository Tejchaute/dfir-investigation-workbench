import { Badge } from '..'
import type { TimelineEventType } from '../../types'
export function TimelineEventTypeBadge({ type }: { type: TimelineEventType }) { return <Badge title={type} className="border-border-strong bg-surface-inset text-text-secondary">{type.replaceAll('_', ' ')}</Badge> }
