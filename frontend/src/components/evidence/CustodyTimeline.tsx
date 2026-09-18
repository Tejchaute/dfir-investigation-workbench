import { motion, useReducedMotion } from 'motion/react'
import { MapPin, UserRound } from 'lucide-react'
import { EmptyState, ErrorState, MonospaceValue, TimestampValue } from '..'
import type { CustodyEntry } from '../../types'
import { getErrorMessage } from '../../utils'

export function CustodyTimeline({ entries, error, onRetry }: { entries?: CustodyEntry[]; error?: unknown; onRetry: () => void }) {
  const reduceMotion = useReducedMotion()
  if (error) return <ErrorState title="Unable to load chain of custody" description={getErrorMessage(error)} onRetry={onRetry} />
  if (!entries?.length) return <EmptyState title="No custody history" description="No chain-of-custody entries are available for this evidence." />
  return <ol className="space-y-0">{entries.map((entry, index) => <motion.li key={entry.id} className="relative grid grid-cols-[1.25rem_minmax(0,1fr)] gap-3 pb-5 last:pb-0" initial={reduceMotion ? false : { opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: reduceMotion ? 0 : Math.min(index * 0.035, 0.18), duration: reduceMotion ? 0 : 0.18 }}><div className="flex flex-col items-center"><span className="mt-1.5 size-2.5 rounded-full border-2 border-accent bg-surface-base" />{index < entries.length - 1 && <span aria-hidden="true" className="mt-1 w-px grow bg-border-strong" />}</div><article className="min-w-0 rounded-md border border-border-subtle bg-surface-inset p-4"><div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-sm font-semibold text-text-primary">{entry.action}</p><p className="mt-1 flex items-center gap-1.5 text-sm text-text-secondary"><UserRound aria-hidden="true" className="size-3.5" />{entry.person}</p></div><TimestampValue value={entry.timestamp} semantics="custody event" /></div>{entry.location && <p className="mt-3 flex items-start gap-1.5 text-sm text-text-secondary"><MapPin aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />{entry.location}</p>}{entry.notes && <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-text-secondary">{entry.notes}</p>}<MonospaceValue className="mt-3 block text-[11px] text-text-muted">Entry {entry.id}</MonospaceValue></article></motion.li>)}</ol>
}
