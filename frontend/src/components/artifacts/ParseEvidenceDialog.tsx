import { useEffect, useState } from 'react'
import { AlertTriangle, ScanSearch } from 'lucide-react'
import { Button, Dialog, MonospaceValue } from '..'
import type { EvidenceRecord, ProductionArtifactType } from '../../types'
import { getErrorMessage } from '../../utils'

const ARTIFACT_TYPES: ProductionArtifactType[] = ['EVTX', 'REGISTRY', 'PREFETCH', 'LNK', 'NTFS_MFT']

export function ParseEvidenceDialog({ evidence, open, onOpenChange, submitting, error, onSubmit }: { evidence: EvidenceRecord; open: boolean; onOpenChange: (open: boolean) => void; submitting: boolean; error: unknown; onSubmit: (artifactType: ProductionArtifactType) => void }) {
  const [artifactType, setArtifactType] = useState<ProductionArtifactType>('EVTX')
  useEffect(() => { if (open) setArtifactType('EVTX') }, [open])
  return <Dialog open={open} onOpenChange={onOpenChange} title="Parse evidence" description="Run one registered read-only parser against the controlled evidence copy.">
    <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); onSubmit(artifactType) }}>
      <div className="rounded-md border border-border-subtle bg-surface-inset p-3"><span className="block text-[11px] font-semibold uppercase tracking-wide text-text-muted">Evidence source</span><MonospaceValue className="mt-1 block text-xs text-accent">{evidence.evidence_number}</MonospaceValue><p className="mt-1 break-all text-sm text-text-secondary">{evidence.name}</p></div>
      <label className="block text-sm font-medium text-text-primary" htmlFor="artifact-type">Artifact parser<span className="text-danger"> *</span><select id="artifact-type" className="field-input mt-1.5" value={artifactType} onChange={(event) => setArtifactType(event.target.value as ProductionArtifactType)}>{ARTIFACT_TYPES.map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ')}</option>)}</select></label>
      <p className="text-sm leading-6 text-text-secondary">Parsing is synchronous. It reads evidence without modifying it and creates a new historical artifact result on every run. No progress percentage is inferred.</p>
      {Boolean(error) && <div role="alert" className="flex gap-2 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger"><AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />{getErrorMessage(error)}</div>}
      <div className="flex flex-col-reverse gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:justify-end"><Button type="button" disabled={submitting} onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" variant="primary" loading={submitting} leadingIcon={<ScanSearch aria-hidden="true" className="size-4" />}>{submitting ? 'Parsing evidence' : 'Parse evidence'}</Button></div>
    </form>
  </Dialog>
}
