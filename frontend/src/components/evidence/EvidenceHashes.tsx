import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Badge, EmptyState, ErrorState, IconButton, MonospaceValue, TimestampValue } from '..'
import type { EvidenceHashRecord } from '../../types'
import { getErrorMessage } from '../../utils'

export function EvidenceHashes({ records, error, onRetry }: { records?: EvidenceHashRecord[]; error?: unknown; onRetry: () => void }) {
  const [copied, setCopied] = useState<string | null>(null)
  if (error) return <ErrorState title="Unable to load evidence hashes" description={getErrorMessage(error)} onRetry={onRetry} />
  if (!records?.length) return <EmptyState title="No hash records" description="No evidence hash records are available." />
  async function copy(record: EvidenceHashRecord) { await navigator.clipboard.writeText(record.digest); setCopied(record.id); window.setTimeout(() => setCopied(null), 1500) }
  return <div className="space-y-3">{records.map((record) => <article key={record.id} className="rounded-md border border-border-subtle bg-surface-inset p-4"><div className="flex items-center justify-between gap-3"><div className="flex flex-wrap items-center gap-2"><Badge>{record.purpose}</Badge><span className="text-xs font-semibold text-text-secondary">{record.algorithm}</span></div><IconButton label={`Copy ${record.purpose.toLowerCase()} hash`} onClick={() => void copy(record)}>{copied === record.id ? <Check aria-hidden="true" className="size-4 text-success" /> : <Copy aria-hidden="true" className="size-4" />}</IconButton></div><MonospaceValue className="mt-3 block break-all text-xs leading-5">{record.digest}</MonospaceValue><div className="mt-3 border-t border-border-subtle pt-3"><TimestampValue value={record.computed_at} semantics={`${record.purpose.toLowerCase()} hash computed`} /></div>{copied === record.id && <span className="sr-only" role="status">Hash copied</span>}</article>)}</div>
}
