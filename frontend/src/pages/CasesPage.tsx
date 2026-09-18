import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, ExternalLink, Plus } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, DataTable, EmptyState, ErrorState, MonospaceValue, PageHeader, StatusBadge, TimestampValue, type DataTableColumn } from '../components'
import { CaseFormDialog } from '../components/cases/CaseFormDialog'
import { CaseListSkeleton } from '../components/cases/CaseListSkeleton'
import { useCases, useCreateCase } from '../hooks'
import type { CaseCreateRequest, CaseRecord } from '../types'
import { getErrorMessage } from '../utils'

const PAGE_SIZE = 25

export function CasesPage() {
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const [createOpen, setCreateOpen] = useState(false)
  const casesQuery = useCases({ limit: PAGE_SIZE, offset })
  const createCase = useCreateCase()

  const columns = useMemo<DataTableColumn<CaseRecord>[]>(() => [
    { id: 'number', header: 'Case number', cell: (record) => <Link className="inline-flex items-center gap-1.5 rounded-sm text-accent hover:text-focus" to={`/cases/${record.id}/overview`}><MonospaceValue className="font-semibold text-accent">{record.case_number}</MonospaceValue><ExternalLink aria-hidden="true" className="size-3.5" /></Link> },
    { id: 'title', header: 'Title', cell: (record) => <div className="max-w-xl"><p className="font-medium text-text-primary">{record.name}</p>{record.description && <p className="mt-1 line-clamp-1 text-xs text-text-muted">{record.description}</p>}{record.investigator && <p className="mt-1 text-xs text-text-secondary">Investigator: {record.investigator}</p>}</div> },
    { id: 'status', header: 'Status', cell: (record) => <StatusBadge status={record.status} /> },
    { id: 'created', header: 'Created', cell: (record) => <TimestampValue value={record.created_at} /> },
    { id: 'updated', header: 'Updated', cell: (record) => <TimestampValue value={record.updated_at} /> },
  ], [])

  function submitCreate(payload: CaseCreateRequest) {
    createCase.mutate(payload, { onSuccess: (created) => {
      setCreateOpen(false)
      navigate(`/cases/${created.id}/overview`, { state: { notice: `Case ${created.case_number} created successfully.` } })
    } })
  }

  const data = casesQuery.data
  const pageStart = data?.meta.total ? data.meta.offset + 1 : 0
  const pageEnd = data ? Math.min(data.meta.offset + data.data.length, data.meta.total) : 0

  return <div className="space-y-6"><PageHeader eyebrow="Investigations" title="Cases" description="Investigation case management" actions={<Button variant="primary" leadingIcon={<Plus aria-hidden="true" className="size-4" />} onClick={() => setCreateOpen(true)}>New Case</Button>} />
    {casesQuery.isPending ? <CaseListSkeleton /> : casesQuery.isError ? <ErrorState description={getErrorMessage(casesQuery.error)} onRetry={() => void casesQuery.refetch()} /> : data && data.data.length === 0 && offset === 0 ? <EmptyState title="No investigation cases" description="Create a case to begin an investigation." action={<Button variant="primary" leadingIcon={<Plus aria-hidden="true" className="size-4" />} onClick={() => setCreateOpen(true)}>Create Case</Button>} /> : data ? <>
      <div className="hidden md:block"><DataTable columns={columns} rows={data.data} getRowKey={(record) => record.id} caption="Investigation cases" /></div>
      <div className="space-y-3 md:hidden">{data.data.map((record) => <article key={record.id} className="rounded-md border border-border-subtle bg-surface-base p-4"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><Link className="rounded-sm" to={`/cases/${record.id}/overview`}><MonospaceValue className="font-semibold text-accent">{record.case_number}</MonospaceValue><h2 className="mt-1 text-base font-semibold text-text-primary">{record.name}</h2></Link></div><StatusBadge status={record.status} /></div>{record.description && <p className="mt-3 line-clamp-2 text-sm leading-6 text-text-secondary">{record.description}</p>}<dl className="mt-4 grid gap-3 border-t border-border-subtle pt-3 text-xs"><div><dt className="uppercase tracking-wide text-text-muted">Created</dt><dd className="mt-1"><TimestampValue value={record.created_at} /></dd></div>{record.investigator && <div><dt className="uppercase tracking-wide text-text-muted">Investigator</dt><dd className="mt-1 text-sm text-text-secondary">{record.investigator}</dd></div>}</dl></article>)}</div>
      <div className="flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {pageStart}–{pageEnd} of {data.meta.total} cases</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || casesQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}>Previous</Button><Button disabled={offset + PAGE_SIZE >= data.meta.total || casesQuery.isFetching} onClick={() => setOffset((current) => current + PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div>
    </> : null}
    <CaseFormDialog mode="create" open={createOpen} onOpenChange={(open) => { setCreateOpen(open); if (!open) createCase.reset() }} submitting={createCase.isPending} error={createCase.error} onSubmit={submitCreate} />
  </div>
}
