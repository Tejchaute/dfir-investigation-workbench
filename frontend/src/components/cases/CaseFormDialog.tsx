import { useEffect, useId, useState, type FormEvent } from 'react'
import { Dialog } from '../ui/Overlays'
import { Button } from '../ui/Button'
import type { CaseCreateRequest, CaseRecord } from '../../types'
import { getErrorMessage } from '../../utils'

interface CaseFormDialogProps {
  mode: 'create' | 'edit'
  open: boolean
  onOpenChange: (open: boolean) => void
  initialCase?: CaseRecord
  submitting: boolean
  error?: unknown
  onSubmit: (payload: CaseCreateRequest) => void
}

export function CaseFormDialog({ mode, open, onOpenChange, initialCase, submitting, error, onSubmit }: CaseFormDialogProps) {
  const nameId = useId(); const descriptionId = useId(); const investigatorId = useId(); const errorId = useId()
  const [name, setName] = useState(''); const [description, setDescription] = useState(''); const [investigator, setInvestigator] = useState('')
  const [validation, setValidation] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setName(initialCase?.name ?? ''); setDescription(initialCase?.description ?? ''); setInvestigator(initialCase?.investigator ?? ''); setValidation(null)
  }, [initialCase, open])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedName = name.trim()
    if (!normalizedName) { setValidation('Case title is required.'); return }
    if (normalizedName.length > 255) { setValidation('Case title must be 255 characters or fewer.'); return }
    if (investigator.length > 255) { setValidation('Investigator must be 255 characters or fewer.'); return }
    setValidation(null)
    onSubmit({ name: normalizedName, description: description.trim() || null, investigator: investigator.trim() || null })
  }

  const requestError = error ? getErrorMessage(error) : null
  return <Dialog open={open} onOpenChange={(value) => !submitting && onOpenChange(value)} title={mode === 'create' ? 'Create investigation case' : 'Edit case metadata'} description={mode === 'create' ? 'The backend will assign the authoritative case number and initial OPEN status.' : 'Lifecycle status is controlled through dedicated case actions.'}><form onSubmit={submit} className="space-y-4" noValidate><Field label="Case title" htmlFor={nameId} required><input id={nameId} autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength={255} required aria-describedby={validation ? errorId : undefined} className="field-input" /></Field><Field label="Description" htmlFor={descriptionId}><textarea id={descriptionId} value={description} onChange={(event) => setDescription(event.target.value)} rows={4} className="field-input resize-y" /></Field><Field label="Investigator" htmlFor={investigatorId} hint="Optional. Stored exactly as case metadata; no authenticated identity is inferred."><input id={investigatorId} value={investigator} onChange={(event) => setInvestigator(event.target.value)} maxLength={255} className="field-input" /></Field>{(validation || requestError) && <p id={errorId} role="alert" className="rounded-md border border-danger/35 bg-danger/10 px-3 py-2 text-sm text-danger">{validation ?? requestError}</p>}<div className="flex flex-col-reverse gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:justify-end"><Button type="button" variant="ghost" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button><Button type="submit" variant="primary" loading={submitting}>{mode === 'create' ? 'Create Case' : 'Save Changes'}</Button></div></form></Dialog>
}

function Field({ label, htmlFor, hint, required, children }: { label: string; htmlFor: string; hint?: string; required?: boolean; children: React.ReactNode }) {
  return <div><label htmlFor={htmlFor} className="mb-1.5 block text-sm font-semibold text-text-primary">{label}{required && <span className="ml-1 text-danger" aria-hidden="true">*</span>}</label>{children}{hint && <p className="mt-1.5 text-xs leading-5 text-text-muted">{hint}</p>}</div>
}
