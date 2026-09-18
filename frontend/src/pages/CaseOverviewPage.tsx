import { useEffect, useState } from 'react'
import { Archive, Edit3, LockKeyhole } from 'lucide-react'
import { useLocation, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Button, ErrorState, LoadingState, MonospaceValue, NotFoundState, PageHeader, StatusBadge, SuccessNotice, TimestampValue } from '../components'
import { CaseFormDialog } from '../components/cases/CaseFormDialog'
import { CaseLifecycleDialog } from '../components/cases/CaseLifecycleDialog'
import { useArchiveCase, useCase, useCloseCase, useUpdateCase } from '../hooks'
import type { CaseCreateRequest } from '../types'
import { getErrorMessage } from '../utils'

type LifecycleAction = 'close' | 'archive'

export function CaseOverviewPage() {
  const { caseId = '' } = useParams()
  const location = useLocation()
  const caseQuery = useCase(caseId)
  const updateCase = useUpdateCase(caseId)
  const closeCase = useCloseCase(caseId)
  const archiveCase = useArchiveCase(caseId)
  const [editOpen, setEditOpen] = useState(false)
  const [lifecycleAction, setLifecycleAction] = useState<LifecycleAction | null>(null)
  const [notice, setNotice] = useState<string | null>((location.state as { notice?: string } | null)?.notice ?? null)

  useEffect(() => { if (notice) window.history.replaceState({}, document.title) }, [notice])
  if (caseQuery.isPending) return <LoadingState label="Loading case record" />
  if (caseQuery.error instanceof ApiError && caseQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested case does not exist or is no longer available." />
  if (caseQuery.isError) return <ErrorState description={getErrorMessage(caseQuery.error)} onRetry={() => void caseQuery.refetch()} />
  const record = caseQuery.data
  if (!record) return null

  function submitEdit(payload: CaseCreateRequest) { updateCase.mutate(payload, { onSuccess: () => { setEditOpen(false); setNotice('Case metadata updated successfully.') } }) }
  function confirmLifecycle() {
    if (lifecycleAction === 'close') closeCase.mutate(undefined, { onSuccess: () => { setLifecycleAction(null); setNotice('Case transitioned to CLOSED.') } })
    if (lifecycleAction === 'archive') archiveCase.mutate(undefined, { onSuccess: () => { setLifecycleAction(null); setNotice('Case transitioned to ARCHIVED.') } })
  }
  const activeMutation = lifecycleAction === 'close' ? closeCase : archiveCase

  return <div className="space-y-6"><PageHeader eyebrow="Case" title={record.name} description="Authoritative case metadata and lifecycle state." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: record.case_number }]} actions={<>{record.status === 'OPEN' && <><Button leadingIcon={<Edit3 aria-hidden="true" className="size-4" />} onClick={() => setEditOpen(true)}>Edit</Button><Button leadingIcon={<LockKeyhole aria-hidden="true" className="size-4" />} onClick={() => setLifecycleAction('close')}>Close</Button></>}{record.status === 'CLOSED' && <Button variant="primary" leadingIcon={<Archive aria-hidden="true" className="size-4" />} onClick={() => setLifecycleAction('archive')}>Archive</Button>}</>} />
    {notice && <SuccessNotice message={notice} />}
    <section aria-labelledby="case-identification" className="rounded-md border border-border-subtle bg-surface-base"><header className="flex flex-col gap-3 border-b border-border-subtle px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">Case identification</p><h2 id="case-identification" className="mt-1"><MonospaceValue className="text-lg font-semibold text-accent">{record.case_number}</MonospaceValue></h2></div><StatusBadge status={record.status} /></header><dl className="grid gap-px bg-border-subtle sm:grid-cols-2 xl:grid-cols-4"><Info label="Case ID"><MonospaceValue className="text-xs">{record.id}</MonospaceValue></Info><Info label="Status"><span className="font-semibold text-text-primary">{record.status}</span></Info><Info label="Created"><TimestampValue value={record.created_at} /></Info><Info label="Updated"><TimestampValue value={record.updated_at} /></Info></dl></section>
    <section aria-labelledby="case-information" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 id="case-information" className="text-sm font-semibold uppercase tracking-wide text-text-primary">Case information</h2><dl className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(15rem,1fr)]"><div><dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Description</dt><dd className="mt-2 whitespace-pre-wrap text-sm leading-6 text-text-secondary">{record.description || 'No description provided.'}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">Investigator</dt><dd className="mt-2 text-sm text-text-secondary">{record.investigator || 'Not specified'}</dd></div></dl></section>
    {record.status === 'ARCHIVED' && <div className="rounded-md border border-status-archived/30 bg-status-archived/10 px-4 py-3 text-sm text-status-archived">This case is archived and read-only. No lifecycle actions are available.</div>}
    <CaseFormDialog mode="edit" open={editOpen} onOpenChange={(open) => { setEditOpen(open); if (!open) updateCase.reset() }} initialCase={record} submitting={updateCase.isPending} error={updateCase.error} onSubmit={submitEdit} />
    {lifecycleAction && <CaseLifecycleDialog action={lifecycleAction} open onOpenChange={(open) => { if (!open) { setLifecycleAction(null); activeMutation.reset() } }} submitting={activeMutation.isPending} error={activeMutation.error} onConfirm={confirmLifecycle} />}
  </div>
}

function Info({ label, children }: { label: string; children: React.ReactNode }) { return <div className="min-w-0 bg-surface-base px-4 py-3"><dt className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">{label}</dt><dd className="mt-1.5 min-w-0 text-sm text-text-secondary">{children}</dd></div> }
