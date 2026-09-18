import { AlertTriangle, ShieldCheck } from 'lucide-react'
import { Button, Dialog } from '..'
import { getErrorMessage } from '../../utils'

export function EvidenceVerificationDialog({ open, onOpenChange, submitting, error, onConfirm }: { open: boolean; onOpenChange: (open: boolean) => void; submitting: boolean; error: unknown; onConfirm: () => void }) {
  return <Dialog open={open} onOpenChange={onOpenChange} title="Verify evidence integrity" description="Recalculate SHA-256 from the controlled evidence copy and compare it with the recorded acquisition hash.">
    <div className="space-y-4"><p className="text-sm leading-6 text-text-secondary">Verification reads the stored evidence without modifying it. The backend records the calculated digest and authoritative match result.</p>
      {Boolean(error) && <div role="alert" className="flex gap-2 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger"><AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />{getErrorMessage(error)}</div>}
      <div className="flex flex-col-reverse gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:justify-end"><Button onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button><Button variant="primary" loading={submitting} leadingIcon={<ShieldCheck aria-hidden="true" className="size-4" />} onClick={onConfirm}>{submitting ? 'Verifying' : 'Verify integrity'}</Button></div>
    </div>
  </Dialog>
}
