import type { FormEvent } from 'react'
import { RotateCcw, SlidersHorizontal } from 'lucide-react'
import { Button, FilterBar } from '..'
import type { FindingConfidence, FindingFilters, FindingSeverity, FindingStatus } from '../../types'

const control = 'mt-1 h-9 w-full min-w-0 rounded-md border border-border-subtle bg-surface-inset px-3 text-sm text-text-primary hover:border-border-strong focus:border-accent'
const statuses: FindingStatus[] = ['OPEN', 'REVIEWED', 'RESOLVED', 'DISMISSED']
const severities: FindingSeverity[] = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const confidences: FindingConfidence[] = ['LOW', 'MEDIUM', 'HIGH']

export function FindingFiltersPanel({ value, onChange, onApply, onClear, disabled }: { value: FindingFilters; onChange: (value: FindingFilters) => void; onApply: () => void; onClear: () => void; disabled?: boolean }) {
  function submit(event: FormEvent) { event.preventDefault(); onApply() }
  return <form onSubmit={submit}><FilterBar><div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"><Select label="Status" value={value.status ?? ''} values={statuses} onChange={(status) => onChange({ ...value, status: status as FindingStatus || undefined })} /><Select label="Severity" value={value.severity ?? ''} values={severities} onChange={(severity) => onChange({ ...value, severity: severity as FindingSeverity || undefined })} /><Select label="Confidence" value={value.confidence ?? ''} values={confidences} onChange={(confidence) => onChange({ ...value, confidence: confidence as FindingConfidence || undefined })} /><label className="min-w-0 text-xs font-semibold text-text-muted">Rule ID<input className={`${control} font-mono text-xs`} value={value.ruleId ?? ''} onChange={(event) => onChange({ ...value, ruleId: event.target.value || undefined })} placeholder="Exact rule ID" /></label></div><div className="flex shrink-0 gap-2 self-end"><Button type="button" variant="ghost" leadingIcon={<RotateCcw aria-hidden="true" className="size-4" />} disabled={disabled} onClick={onClear}>Clear</Button><Button type="submit" leadingIcon={<SlidersHorizontal aria-hidden="true" className="size-4" />} disabled={disabled}>Apply filters</Button></div><p className="basis-full text-xs text-text-muted">These are exact backend-supported classifications. Confidence remains textual and is not a probability.</p></FilterBar></form>
}
function Select({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) { return <label className="min-w-0 text-xs font-semibold text-text-muted">{label}<select className={control} value={value} onChange={(event) => onChange(event.target.value)}><option value="">All</option>{values.map((item) => <option key={item} value={item}>{item}</option>)}</select></label> }
