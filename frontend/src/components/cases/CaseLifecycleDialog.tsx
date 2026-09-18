import { AlertTriangle } from 'lucide-react'
import { Dialog } from '../ui/Overlays'
import { Button } from '../ui/Button'
import { getErrorMessage } from '../../utils'

export function CaseLifecycleDialog({ action, open, onOpenChange, submitting, error, onConfirm }: { action: 'close' | 'archive'; open: boolean; onOpenChange: (open: boolean) => void; submitting: boolean; error?: unknown; onConfirm: () => void }) {
  const isClose = action === 'close'
  return <Dialog open={open} onOpenChange={(value) => !submitting && onOpenChange(value)} title={isClose ? 'Close this investigation case?' : 'Archive this investigation case?'} description={isClose ? 'The case will transition from OPEN to CLOSED.' : 'The case will transition from CLOSED to ARCHIVED.'}><div className="space-y-4"><div className="flex gap-3 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm leading-6 text-text-secondary"><AlertTriangle aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-warning" /><p>This lifecycle action does not delete evidence or alter forensic records. The backend will validate the transition.</p></div>{Boolean(error) && <p role="alert" className="rounded-md border border-danger/35 bg-danger/10 px-3 py-2 text-sm text-danger">{getErrorMessage(error)}</p>}<div className="flex flex-col-reverse gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:justify-end"><Button variant="ghost" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button><Button variant={isClose ? 'secondary' : 'primary'} loading={submitting} onClick={onConfirm}>{isClose ? 'Close Case' : 'Archive Case'}</Button></div></div></Dialog>
}
