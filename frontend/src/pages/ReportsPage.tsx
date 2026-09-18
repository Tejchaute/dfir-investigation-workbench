import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, FilePlus2 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Button, EmptyState, ErrorState, LoadingState, NotFoundState, PageHeader } from '../components'
import { GenerateReportDialog } from '../components/reports/GenerateReportDialog'
import { ReportRow } from '../components/reports/ReportRow'
import { useCase, useCreateReport, useReports } from '../hooks'
import type { ReportCreateRequest } from '../types'
import { getErrorMessage } from '../utils'

const PAGE_SIZE = 25

export function ReportsPage() {
  const { caseId = '' } = useParams()
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const parameters = useMemo(() => ({ limit: PAGE_SIZE, offset }), [offset])
  const caseQuery = useCase(caseId)
  const reportsQuery = useReports(caseId, parameters)
  const createMutation = useCreateReport(caseId)
  if (caseQuery.isPending) return <LoadingState label="Loading reports workspace" />
  if (caseQuery.error instanceof ApiError && caseQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." />
  if (caseQuery.isError) return <ErrorState description={getErrorMessage(caseQuery.error)} onRetry={() => void caseQuery.refetch()} />
  const reports = reportsQuery.data
  const start = reports?.meta.total ? reports.meta.offset + 1 : 0
  const end = reports ? Math.min(reports.meta.offset + reports.data.length, reports.meta.total) : 0
  function generate(payload: ReportCreateRequest) { createMutation.mutate(payload, { onSuccess: (report) => { setDialogOpen(false); navigate(`/cases/${caseId}/reports/${report.id}`) } }) }
  return <div className="space-y-5"><PageHeader eyebrow="Output" title="Reports" description="Immutable forensic report snapshots and their independently hashed rendered artifacts." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Reports' }]} actions={<Button leadingIcon={<FilePlus2 aria-hidden="true" className="size-4" />} onClick={() => setDialogOpen(true)}>Generate report</Button>} />
    <section className="rounded-md border border-accent/20 bg-accent/5 p-3 text-sm text-text-secondary"><strong className="text-text-primary">Integrity distinction:</strong> report artifact SHA-256 values verify rendered report files. They are not evidence acquisition or verification hashes.</section>
    {reportsQuery.isPending ? <LoadingState label="Loading generated reports" /> : reportsQuery.error instanceof ApiError && reportsQuery.error.status === 404 ? <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." /> : reportsQuery.isError ? <ErrorState title="Unable to load reports" description={getErrorMessage(reportsQuery.error)} onRetry={() => void reportsQuery.refetch()} /> : reports && reports.data.length === 0 ? <EmptyState title="No reports generated" description="Generate an immutable report from the case's existing forensic observations and analytical records." action={<Button leadingIcon={<FilePlus2 aria-hidden="true" className="size-4" />} onClick={() => setDialogOpen(true)}>Generate report</Button>} /> : reports ? <section aria-labelledby="report-list" className="rounded-md border border-border-subtle bg-surface-inset p-3 sm:p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 id="report-list" className="text-sm font-semibold text-text-primary">Generated reports</h2><p className="text-xs text-text-muted">Newest backend snapshot first</p></div><ol className="space-y-2">{reports.data.map((report) => <ReportRow key={report.id} report={report} />)}</ol><div className="mt-5 flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {start}–{end} of {reports.meta.total} reports</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || reportsQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}>Previous</Button><Button disabled={offset + PAGE_SIZE >= reports.meta.total || reportsQuery.isFetching} onClick={() => setOffset((current) => current + PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div></section> : null}
    <GenerateReportDialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (open) createMutation.reset() }} pending={createMutation.isPending} error={createMutation.error} onGenerate={generate} />
  </div>
}
