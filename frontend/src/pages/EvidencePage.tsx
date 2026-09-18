import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, ExternalLink, Plus } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Badge, Button, DataTable, EmptyState, ErrorState, MonospaceValue, NotFoundState, PageHeader, TimestampValue, type DataTableColumn } from '../components'
import { EvidenceListSkeleton } from '../components/evidence/EvidenceListSkeleton'
import { EvidenceRegistrationDialog } from '../components/evidence/EvidenceRegistrationDialog'
import { useCase, useCaseEvidence, useRegisterEvidence } from '../hooks'
import type { EvidenceRecord, EvidenceRegistrationRequest } from '../types'
import { formatBytes, getErrorMessage } from '../utils'

const PAGE_SIZE = 25

export function EvidencePage() {
  const { caseId = '' } = useParams()
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const [registerOpen, setRegisterOpen] = useState(false)
  const caseQuery = useCase(caseId)
  const evidenceQuery = useCaseEvidence(caseId, { limit: PAGE_SIZE, offset })
  const registration = useRegisterEvidence(caseId)

  const columns = useMemo<DataTableColumn<EvidenceRecord>[]>(() => [
    { id: 'number', header: 'Evidence number', cell: (record) => <Link className="inline-flex items-center gap-1.5 rounded-sm text-accent hover:text-focus" to={`/cases/${caseId}/evidence/${record.id}`}><MonospaceValue className="font-semibold text-accent">{record.evidence_number}</MonospaceValue><ExternalLink aria-hidden="true" className="size-3.5" /></Link> },
    { id: 'name', header: 'Name', cell: (record) => <div className="max-w-md"><p className="break-all font-medium text-text-primary">{record.name}</p>{record.description && <p className="mt-1 line-clamp-1 text-xs text-text-muted">{record.description}</p>}</div> },
    { id: 'type', header: 'Type', cell: (record) => <Badge>{record.evidence_type.replaceAll('_', ' ')}</Badge> },
    { id: 'size', header: 'Size', align: 'right', cell: (record) => <span className="forensic-mono whitespace-nowrap text-sm">{formatBytes(record.size_bytes)}</span> },
    { id: 'registered', header: 'Registered', cell: (record) => <TimestampValue value={record.created_at} /> },
  ], [caseId])

  function submitRegistration(payload: EvidenceRegistrationRequest) {
    registration.mutate(payload, { onSuccess: (created) => {
      setRegisterOpen(false)
      navigate(`/cases/${caseId}/evidence/${created.id}`, { state: { notice: `Evidence ${created.evidence_number} registered with an acquisition SHA-256.` } })
    } })
  }

  if (evidenceQuery.error instanceof ApiError && evidenceQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested case does not exist or is no longer available." />
  const data = evidenceQuery.data
  const pageStart = data?.meta.total ? data.meta.offset + 1 : 0
  const pageEnd = data ? Math.min(data.meta.offset + data.data.length, data.meta.total) : 0
  const canRegister = caseQuery.data?.status === 'OPEN'
  const registerHint = caseQuery.data && !canRegister ? `Evidence registration is unavailable while this case is ${caseQuery.data.status}.` : undefined

  return <div className="space-y-6"><PageHeader eyebrow="Case evidence" title="Evidence" description="Controlled evidence registration, integrity records, and custody history." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Evidence' }]} actions={<Button variant="primary" leadingIcon={<Plus aria-hidden="true" className="size-4" />} disabled={!canRegister} title={registerHint} onClick={() => setRegisterOpen(true)}>Register evidence</Button>} />
    {registerHint && <p className="rounded-md border border-warning/25 bg-warning/10 px-3 py-2 text-sm text-warning">{registerHint}</p>}
    {evidenceQuery.isPending ? <EvidenceListSkeleton /> : evidenceQuery.isError ? <ErrorState description={getErrorMessage(evidenceQuery.error)} onRetry={() => void evidenceQuery.refetch()} /> : data && data.data.length === 0 && offset === 0 ? <EmptyState title="No evidence registered" description="Register evidence to begin preserving and analyzing this investigation's source material." action={canRegister ? <Button variant="primary" leadingIcon={<Plus aria-hidden="true" className="size-4" />} onClick={() => setRegisterOpen(true)}>Register evidence</Button> : undefined} /> : data ? <>
      <div className="hidden md:block"><DataTable columns={columns} rows={data.data} getRowKey={(record) => record.id} caption="Registered evidence" /></div>
      <div className="space-y-3 md:hidden">{data.data.map((record) => <article key={record.id} className="rounded-md border border-border-subtle bg-surface-base p-4"><div className="flex items-start justify-between gap-3"><Link className="min-w-0 rounded-sm" to={`/cases/${caseId}/evidence/${record.id}`}><MonospaceValue className="font-semibold text-accent">{record.evidence_number}</MonospaceValue><h2 className="mt-1 break-all text-base font-semibold text-text-primary">{record.name}</h2></Link><Badge>{record.evidence_type.replaceAll('_', ' ')}</Badge></div>{record.description && <p className="mt-3 line-clamp-2 text-sm leading-6 text-text-secondary">{record.description}</p>}<dl className="mt-4 grid grid-cols-2 gap-3 border-t border-border-subtle pt-3 text-xs"><div><dt className="uppercase tracking-wide text-text-muted">Size</dt><dd className="forensic-mono mt-1 text-sm text-text-secondary">{formatBytes(record.size_bytes)}</dd></div><div><dt className="uppercase tracking-wide text-text-muted">Registered</dt><dd className="mt-1"><TimestampValue value={record.created_at} /></dd></div></dl></article>)}</div>
      <div className="flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {pageStart}–{pageEnd} of {data.meta.total} evidence items</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || evidenceQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}>Previous</Button><Button disabled={offset + PAGE_SIZE >= data.meta.total || evidenceQuery.isFetching} onClick={() => setOffset((current) => current + PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div>
    </> : null}
    <EvidenceRegistrationDialog open={registerOpen} onOpenChange={(open) => { setRegisterOpen(open); if (!open) registration.reset() }} submitting={registration.isPending} error={registration.error} onSubmit={submitRegistration} />
  </div>
}
