import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, GitCompareArrows } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Badge, Button, EmptyState, ErrorState, LoadingState, MonospaceValue, NotFoundState, PageHeader, StatusBadge, SuccessNotice, TimestampValue } from '../components'
import { CorrelationFiltersPanel } from '../components/correlation/CorrelationFiltersPanel'
import { CorrelationMatchDrawer } from '../components/correlation/CorrelationMatchDrawer'
import { CorrelationMatchRow } from '../components/correlation/CorrelationMatchRow'
import { RunCorrelationDialog } from '../components/correlation/RunCorrelationDialog'
import { useCase, useCorrelations, useRunCorrelation } from '../hooks'
import type { CorrelationFilters, CorrelationMatchRecord, CorrelationRunRecord } from '../types'
import { getErrorMessage } from '../utils'

const PAGE_SIZE = 25
const EMPTY_FILTERS: CorrelationFilters = {}

export function CorrelationPage() {
  const { caseId = '' } = useParams()
  const [offset, setOffset] = useState(0)
  const [draft, setDraft] = useState<CorrelationFilters>(EMPTY_FILTERS)
  const [filters, setFilters] = useState<CorrelationFilters>(EMPTY_FILTERS)
  const [selected, setSelected] = useState<CorrelationMatchRecord | null>(null)
  const [runOpen, setRunOpen] = useState(false)
  const [lastRun, setLastRun] = useState<CorrelationRunRecord | null>(null)
  const parameters = useMemo(() => ({ ...filters, limit: PAGE_SIZE, offset }), [filters, offset])
  const caseQuery = useCase(caseId)
  const correlationsQuery = useCorrelations(caseId, parameters)
  const runMutation = useRunCorrelation(caseId)
  useEffect(() => { setSelected(null) }, [parameters])

  if (caseQuery.isPending) return <LoadingState label="Loading correlation workspace" />
  if (caseQuery.error instanceof ApiError && caseQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." />
  if (caseQuery.isError) return <ErrorState description={getErrorMessage(caseQuery.error)} onRetry={() => void caseQuery.refetch()} />
  const matches = correlationsQuery.data
  const start = matches?.meta.total ? matches.meta.offset + 1 : 0
  const end = matches ? Math.min(matches.meta.offset + matches.data.length, matches.meta.total) : 0
  const filtered = Boolean(filters.ruleId || filters.correlationRunId)
  function run() { runMutation.mutate(undefined, { onSuccess: (value) => { setLastRun(value); setOffset(0); setRunOpen(false) } }) }
  function clear() { setDraft(EMPTY_FILTERS); setFilters(EMPTY_FILTERS); setOffset(0) }

  return <div className="space-y-5"><PageHeader eyebrow="Analysis" title="Correlation Analysis" description="Explainable matches produced by backend-managed deterministic rules over persisted TimelineEvents." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Correlations' }]} actions={<Button leadingIcon={<GitCompareArrows aria-hidden="true" className="size-4" />} onClick={() => setRunOpen(true)}>Run correlation</Button>} />
    {lastRun && <RunSummary run={lastRun} caseId={caseId} />}
    {runMutation.isError && <ErrorState title="Correlation run failed" description={getErrorMessage(runMutation.error)} />}
    <CorrelationFiltersPanel value={draft} onChange={setDraft} onApply={() => { setFilters(draft); setOffset(0) }} onClear={clear} disabled={correlationsQuery.isFetching} />
    {correlationsQuery.isPending ? <LoadingState label="Loading correlation matches" /> : correlationsQuery.error instanceof ApiError && correlationsQuery.error.status === 404 ? <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." /> : correlationsQuery.isError ? <ErrorState title="Unable to load correlations" description={getErrorMessage(correlationsQuery.error)} onRetry={() => void correlationsQuery.refetch()} /> : matches && matches.data.length === 0 ? <EmptyState title="No correlation matches" description={filtered ? 'No persisted correlation matches satisfy the exact active filters.' : 'Run deterministic correlation against persisted timeline events to evaluate configured matching rules. Absence of a match does not establish absence of activity.'} action={filtered ? <Button variant="secondary" onClick={clear}>Clear filters</Button> : <Button leadingIcon={<GitCompareArrows aria-hidden="true" className="size-4" />} onClick={() => setRunOpen(true)}>Run correlation</Button>} /> : matches ? <section aria-labelledby="correlation-matches" className="rounded-md border border-border-subtle bg-surface-inset p-3 sm:p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h2 id="correlation-matches" className="text-sm font-semibold text-text-primary">Correlation matches</h2><p className="text-xs text-text-muted">Backend order preserved</p></div><ol className="space-y-2">{matches.data.map((match) => <CorrelationMatchRow key={match.id} match={match} selected={selected?.id === match.id} onSelect={() => setSelected(match)} />)}</ol><div className="mt-5 flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {start}–{end} of {matches.meta.total} matches</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || correlationsQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}>Previous</Button><Button disabled={offset + PAGE_SIZE >= matches.meta.total || correlationsQuery.isFetching} onClick={() => setOffset((current) => current + PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div></section> : null}
    <RunCorrelationDialog open={runOpen} onOpenChange={setRunOpen} pending={runMutation.isPending} onRun={run} />
    <CorrelationMatchDrawer match={selected} caseId={caseId} open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null) }} />
  </div>
}

function RunSummary({ run, caseId }: { run: CorrelationRunRecord; caseId: string }) { return <section aria-labelledby="latest-run" className="rounded-md border border-border-subtle bg-surface-base p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 id="latest-run" className="text-sm font-semibold text-text-primary">Latest run in this session</h2><MonospaceValue className="text-xs">{run.id}</MonospaceValue></div><StatusBadge status={run.status} /></div><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Metric label="Timeline events" value={run.event_count} /><Metric label="Matches created" value={run.matched_count} /><Metric label="Findings created" value={run.finding_count} /><Metric label="Temporal window" value={`${run.temporal_window_seconds}s`} /></div><dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2"><div><dt className="text-xs uppercase tracking-wide text-text-muted">Rule-set version</dt><dd><MonospaceValue>{run.rule_set_version}</MonospaceValue></dd></div><div><dt className="text-xs uppercase tracking-wide text-text-muted">Completed</dt><dd><TimestampValue value={run.completed_at} /></dd></div></dl><div className="mt-4 flex flex-wrap gap-2">{run.rules_evaluated.map((rule) => <Badge key={`${rule.rule_id}-${rule.rule_version}`}><span className="font-mono">{rule.rule_id}</span> v{rule.rule_version}</Badge>)}</div>{run.warnings.map((warning) => <p key={warning} className="mt-3 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm text-warning">Run warning: {warning}</p>)}{run.errors.map((error) => <p key={error} className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger">Run error: {error}</p>)}{run.event_count === 0 && <div className="mt-4"><SuccessNotice message="The backend considered zero TimelineEvents; no correlation relationship was evaluated." /><Link className="mt-3 inline-block" to={`/cases/${caseId}/timeline`}><Button variant="secondary">Go to Timeline</Button></Link></div>}<p className="mt-3 text-xs text-text-muted">Finding count is the immutable backend run statistic only. Finding management is not part of this workspace.</p></section> }
function Metric({ label, value }: { label: string; value: number | string }) { return <div className="rounded-md border border-border-subtle bg-surface-inset p-3"><p className="text-xs uppercase tracking-wide text-text-muted">{label}</p><p className="mt-1 font-mono text-lg text-text-primary">{value}</p></div> }
