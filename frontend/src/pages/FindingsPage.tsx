import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, GitCompareArrows } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Button, EmptyState, ErrorState, LoadingState, NotFoundState, PageHeader } from '../components'
import { FindingFiltersPanel } from '../components/findings/FindingFiltersPanel'
import { FindingRow } from '../components/findings/FindingRow'
import { useCase, useFindings } from '../hooks'
import type { FindingFilters } from '../types'
import { getErrorMessage } from '../utils'

const PAGE_SIZE = 25
const EMPTY_FILTERS: FindingFilters = {}

export function FindingsPage() {
  const { caseId = '' } = useParams()
  const [offset, setOffset] = useState(0)
  const [draft, setDraft] = useState<FindingFilters>(EMPTY_FILTERS)
  const [filters, setFilters] = useState<FindingFilters>(EMPTY_FILTERS)
  const parameters = useMemo(() => ({ ...filters, limit: PAGE_SIZE, offset }), [filters, offset])
  const caseQuery = useCase(caseId)
  const findingsQuery = useFindings(caseId, parameters)
  useEffect(() => { setOffset(0) }, [filters])
  if (caseQuery.isPending) return <LoadingState label="Loading findings workspace" />
  if (caseQuery.error instanceof ApiError && caseQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." />
  if (caseQuery.isError) return <ErrorState description={getErrorMessage(caseQuery.error)} onRetry={() => void caseQuery.refetch()} />
  const findings = findingsQuery.data
  const start = findings?.meta.total ? findings.meta.offset + 1 : 0
  const end = findings ? Math.min(findings.meta.offset + findings.data.length, findings.meta.total) : 0
  const filtered = Boolean(filters.status || filters.severity || filters.confidence || filters.ruleId)
  function clear() { setDraft(EMPTY_FILTERS); setFilters(EMPTY_FILTERS); setOffset(0) }
  return <div className="space-y-5"><PageHeader eyebrow="Analysis" title="Findings" description="Backend-generated analytical relationships with controlled analyst review metadata and evidence provenance." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Findings' }]} />
    <FindingFiltersPanel value={draft} onChange={setDraft} onApply={() => setFilters(draft)} onClear={clear} disabled={findingsQuery.isFetching} />
    {findingsQuery.isPending ? <LoadingState label="Loading findings" /> : findingsQuery.error instanceof ApiError && findingsQuery.error.status === 404 ? <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." /> : findingsQuery.isError ? <ErrorState title="Unable to load findings" description={getErrorMessage(findingsQuery.error)} onRetry={() => void findingsQuery.refetch()} /> : findings && findings.data.length === 0 ? <EmptyState title="No findings" description={filtered ? 'No backend-generated findings satisfy the active exact filters.' : 'Run deterministic correlation against the persisted case timeline to generate findings when a configured rule matches. No findings does not establish absence of activity.'} action={filtered ? <Button variant="secondary" onClick={clear}>Clear filters</Button> : <Link to={`/cases/${caseId}/correlations`}><Button leadingIcon={<GitCompareArrows aria-hidden="true" className="size-4" />}>Open correlation workspace</Button></Link>} /> : findings ? <section aria-labelledby="finding-list" className="rounded-md border border-border-subtle bg-surface-inset p-3 sm:p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 id="finding-list" className="text-sm font-semibold text-text-primary">Analytical findings</h2><p className="text-xs text-text-muted">Backend order preserved</p></div><ol className="space-y-2">{findings.data.map((finding) => <FindingRow key={finding.id} finding={finding} />)}</ol><div className="mt-5 flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {start}–{end} of {findings.meta.total} findings</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || findingsQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}>Previous</Button><Button disabled={offset + PAGE_SIZE >= findings.meta.total || findingsQuery.isFetching} onClick={() => setOffset((current) => current + PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div></section> : null}
  </div>
}
