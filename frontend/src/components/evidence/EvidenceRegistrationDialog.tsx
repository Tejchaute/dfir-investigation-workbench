import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, Upload } from 'lucide-react'
import { Button, Dialog } from '..'
import type { EvidenceRegistrationRequest, EvidenceType } from '../../types'
import { getErrorMessage } from '../../utils'

const EVIDENCE_TYPES: EvidenceType[] = ['DISK_IMAGE', 'LOG_FILE', 'MEMORY_DUMP', 'REGISTRY_HIVE', 'FILE', 'DIRECTORY', 'OTHER']

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  submitting: boolean
  error: unknown
  onSubmit: (payload: EvidenceRegistrationRequest) => void
}

export function EvidenceRegistrationDialog({ open, onOpenChange, submitting, error, onSubmit }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [evidenceType, setEvidenceType] = useState<EvidenceType>('FILE')
  const [custodyPerson, setCustodyPerson] = useState('')
  const [description, setDescription] = useState('')
  const [collectedBy, setCollectedBy] = useState('')
  const [collectedAt, setCollectedAt] = useState('')
  const [custodyLocation, setCustodyLocation] = useState('')
  const [custodyNotes, setCustodyNotes] = useState('')

  useEffect(() => {
    if (!open) return
    setFile(null); setEvidenceType('FILE'); setCustodyPerson(''); setDescription(''); setCollectedBy(''); setCollectedAt(''); setCustodyLocation(''); setCustodyNotes('')
  }, [open])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file || !custodyPerson.trim()) return
    onSubmit({
      file,
      evidence_type: evidenceType,
      custody_person: custodyPerson.trim(),
      description: description.trim() || undefined,
      collected_by: collectedBy.trim() || undefined,
      collected_at: collectedAt ? new Date(collectedAt).toISOString() : undefined,
      custody_location: custodyLocation.trim() || undefined,
      custody_notes: custodyNotes.trim() || undefined,
    })
  }

  return <Dialog open={open} onOpenChange={onOpenChange} title="Register evidence" description="The backend creates a controlled forensic copy and computes the authoritative acquisition SHA-256.">
    <form className="space-y-4" onSubmit={submit}>
      <div><label className="text-sm font-medium text-text-primary" htmlFor="evidence-file">Evidence file <span className="text-danger">*</span></label><input id="evidence-file" name="file" type="file" required className="mt-1.5 block w-full rounded-md border border-border-subtle bg-surface-inset text-sm text-text-secondary file:mr-3 file:border-0 file:border-r file:border-border-subtle file:bg-surface-raised file:px-3 file:py-2.5 file:font-semibold file:text-text-primary hover:border-border-strong" onChange={(event) => setFile(event.target.files?.item(0) ?? null)} /><p className="mt-1.5 text-xs text-text-muted">The selected file is transmitted unchanged. The browser does not inspect or execute its contents.</p></div>
      <div className="grid gap-4 sm:grid-cols-2"><Field label="Evidence type" required><select className="field-input" value={evidenceType} onChange={(event) => setEvidenceType(event.target.value as EvidenceType)}>{EVIDENCE_TYPES.map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></Field><Field label="Custody person" required><input className="field-input" required maxLength={255} value={custodyPerson} onChange={(event) => setCustodyPerson(event.target.value)} /></Field></div>
      <Field label="Description"><textarea className="field-input min-h-20 resize-y" value={description} onChange={(event) => setDescription(event.target.value)} /></Field>
      <div className="grid gap-4 sm:grid-cols-2"><Field label="Collected by"><input className="field-input" maxLength={255} value={collectedBy} onChange={(event) => setCollectedBy(event.target.value)} /></Field><Field label="Collected at"><input className="field-input" type="datetime-local" value={collectedAt} onChange={(event) => setCollectedAt(event.target.value)} /><span className="mt-1 block text-xs text-text-muted">Entered in this workstation's local time and submitted with its UTC offset.</span></Field></div>
      <Field label="Custody location"><input className="field-input" maxLength={500} value={custodyLocation} onChange={(event) => setCustodyLocation(event.target.value)} /></Field>
      <Field label="Custody notes"><textarea className="field-input min-h-20 resize-y" value={custodyNotes} onChange={(event) => setCustodyNotes(event.target.value)} /></Field>
      {Boolean(error) && <div role="alert" className="flex gap-2 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger"><AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" /><span>{getErrorMessage(error)}</span></div>}
      <div className="flex flex-col-reverse gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:justify-end"><Button type="button" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button><Button type="submit" variant="primary" loading={submitting} leadingIcon={<Upload aria-hidden="true" className="size-4" />}>{submitting ? 'Registering evidence' : 'Register evidence'}</Button></div>
    </form>
  </Dialog>
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) { return <label className="block text-sm font-medium text-text-primary">{label}{required && <span className="text-danger"> *</span>}<span className="mt-1.5 block">{children}</span></label> }
