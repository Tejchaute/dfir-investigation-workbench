import type { FormEvent } from 'react'
import { RotateCcw, SlidersHorizontal } from 'lucide-react'
import { Button, FilterBar } from '..'
import type { EvidenceRecord, TimelineArtifactType, TimelineEventType, TimelineFilters } from '../../types'

const EVENTS: TimelineEventType[] = ['EVTX_EVENT', 'REGISTRY_KEY_LAST_WRITE', 'PREFETCH_EXECUTION', 'LNK_METADATA_CREATION', 'LNK_METADATA_ACCESS', 'LNK_METADATA_MODIFICATION', 'NTFS_SI_CREATION', 'NTFS_SI_MODIFICATION', 'NTFS_SI_MFT_CHANGE', 'NTFS_SI_ACCESS', 'NTFS_FN_CREATION', 'NTFS_FN_MODIFICATION', 'NTFS_FN_MFT_CHANGE', 'NTFS_FN_ACCESS']
const ARTIFACTS: TimelineArtifactType[] = ['EVTX', 'REGISTRY', 'PREFETCH', 'LNK', 'NTFS', 'NTFS_MFT']
const control = 'mt-1 h-9 w-full min-w-0 rounded-md border border-border-subtle bg-surface-inset px-3 text-sm text-text-primary hover:border-border-strong focus:border-accent'

export function TimelineFiltersPanel({ value, onChange, onApply, onClear, evidence, disabled }: { value: TimelineFilters; onChange: (value: TimelineFilters) => void; onApply: () => void; onClear: () => void; evidence: EvidenceRecord[]; disabled?: boolean }) {
  function submit(event: FormEvent) { event.preventDefault(); onApply() }
  return <form onSubmit={submit}><FilterBar><div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
    <Field label="Start time"><input className={`${control} font-mono text-xs`} value={value.startTime ?? ''} onChange={(event) => onChange({ ...value, startTime: event.target.value || undefined })} placeholder="ISO 8601 with timezone" aria-describedby="timeline-time-help" /></Field>
    <Field label="End time"><input className={`${control} font-mono text-xs`} value={value.endTime ?? ''} onChange={(event) => onChange({ ...value, endTime: event.target.value || undefined })} placeholder="ISO 8601 with timezone" aria-describedby="timeline-time-help" /></Field>
    <Field label="Event type"><select className={control} value={value.eventType ?? ''} onChange={(event) => onChange({ ...value, eventType: (event.target.value || undefined) as TimelineEventType | undefined })}><option value="">All event types</option>{EVENTS.map((type) => <option key={type}>{type}</option>)}</select></Field>
    <Field label="Artifact type"><select className={control} value={value.artifactType ?? ''} onChange={(event) => onChange({ ...value, artifactType: (event.target.value || undefined) as TimelineArtifactType | undefined })}><option value="">All artifact types</option>{ARTIFACTS.map((type) => <option key={type}>{type}</option>)}</select></Field>
    <Field label="Evidence"><select className={control} value={value.evidenceId ?? ''} onChange={(event) => onChange({ ...value, evidenceId: event.target.value || undefined })}><option value="">All evidence</option>{evidence.map((item) => <option key={item.id} value={item.id}>{item.evidence_number} — {item.name}</option>)}</select></Field>
    <Field label="Source identifier"><input className={`${control} font-mono text-xs`} value={value.sourceIdentifier ?? ''} onChange={(event) => onChange({ ...value, sourceIdentifier: event.target.value || undefined })} placeholder="Exact identifier" /></Field>
  </div><div className="flex shrink-0 gap-2 self-end"><Button type="button" variant="ghost" leadingIcon={<RotateCcw aria-hidden="true" className="size-4" />} onClick={onClear} disabled={disabled}>Clear</Button><Button type="submit" leadingIcon={<SlidersHorizontal aria-hidden="true" className="size-4" />} disabled={disabled}>Apply filters</Button></div><p id="timeline-time-help" className="basis-full text-xs text-text-muted">Time filters require an explicit timezone offset. Values are sent unchanged to the backend.</p></FilterBar></form>
}
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="min-w-0 text-xs font-semibold text-text-muted">{label}{children}</label> }
