import { useEffect, useMemo, useState } from 'react'
import { Activity, ChevronLeft, ChevronRight } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Button, EmptyState, ErrorState, LoadingState, NotFoundState, PageHeader, SuccessNotice } from '../components'
import { GenerateTimelineDialog } from '../components/timeline/GenerateTimelineDialog'
import { TimelineEventDrawer } from '../components/timeline/TimelineEventDrawer'
import { TimelineEventRow } from '../components/timeline/TimelineEventRow'
import { TimelineFiltersPanel } from '../components/timeline/TimelineFiltersPanel'
import { useCase, useCaseEvidence, useGenerateTimeline, useTimeline } from '../hooks'
import type { TimelineEventRecord, TimelineFilters, TimelineGenerationResult } from '../types'
import { getErrorMessage } from '../utils'

const PAGE_SIZE = 25
const EMPTY_FILTERS: TimelineFilters = {}

export function TimelinePage() {
  const { caseId = '' } = useParams()
  const [offset, setOffset] = useState(0)
  const [draft, setDraft] = useState<TimelineFilters>(EMPTY_FILTERS)
  const [filters, setFilters] = useState<TimelineFilters>(EMPTY_FILTERS)
  const [selected, setSelected] = useState<TimelineEventRecord | null>(null)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [result, setResult] = useState<TimelineGenerationResult | null>(null)
  const parameters = useMemo(() => ({ ...filters, limit: PAGE_SIZE, offset }), [filters, offset])
  const caseQuery = useCase(caseId)
  const evidenceQuery = useCaseEvidence(caseId, { limit: 100, offset: 0 })
  const timelineQuery = useTimeline(caseId, parameters)
  const generateMutation = useGenerateTimeline(caseId)
  useEffect(() => { setSelected(null) }, [parameters])

  if (caseQuery.isPending) return <LoadingState label="Loading case timeline" />
  if (caseQuery.error instanceof ApiError && caseQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." />
  if (caseQuery.isError) return <ErrorState description={getErrorMessage(caseQuery.error)} onRetry={() => void caseQuery.refetch()} />
  const events = timelineQuery.data
  const start = events?.meta.total ? events.meta.offset + 1 : 0
  const end = events ? Math.min(events.meta.offset + events.data.length, events.meta.total) : 0
  function generate() { generateMutation.mutate(undefined, { onSuccess: (generated) => { setResult(generated); setOffset(0); setGenerateOpen(false) } }) }
  function clear() { setDraft(EMPTY_FILTERS); setFilters(EMPTY_FILTERS); setOffset(0) }
  return <div className="space-y-5"><PageHeader eyebrow="Analysis" title="Forensic Timeline" description="Persisted timeline observations with explicit source timestamp semantics and evidence provenance." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Timeline' }]} actions={<Button leadingIcon={<Activity aria-hidden="true" className="size-4" />} onClick={() => setGenerateOpen(true)}>Generate timeline</Button>} />
    {result && <SuccessNotice message={`Timeline generation considered ${result.records_considered} records, created ${result.events_created} events, and skipped ${result.events_skipped}.`} />}
    {result?.warnings.map((warning) => <div key={warning} className="rounded-md border border-warning/30 bg-warning/10 p-3 text-sm text-warning">Generation warning: {warning}</div>)}
    {generateMutation.isError && <ErrorState title="Timeline generation failed" description={getErrorMessage(generateMutation.error)} />}
    <TimelineFiltersPanel value={draft} onChange={setDraft} onApply={() => { setFilters(draft); setOffset(0) }} onClear={clear} evidence={evidenceQuery.data?.data ?? []} disabled={timelineQuery.isFetching} />
    {timelineQuery.isPending ? <LoadingState label="Loading timeline observations" /> : timelineQuery.error instanceof ApiError && timelineQuery.error.status === 404 ? <NotFoundState title="Case not found" description="The requested investigation case does not exist or is no longer available." /> : timelineQuery.isError ? <ErrorState title="Unable to load timeline" description={getErrorMessage(timelineQuery.error)} onRetry={() => void timelineQuery.refetch()} /> : events && events.data.length === 0 ? <EmptyState title="No timeline events" description={Object.keys(filters).length ? 'No persisted TimelineEvents match the active filters.' : 'Generate the timeline from parsed artifact records to begin reconstruction.'} action={!Object.keys(filters).length ? <Button leadingIcon={<Activity aria-hidden="true" className="size-4" />} onClick={() => setGenerateOpen(true)}>Generate timeline</Button> : <Button variant="secondary" onClick={clear}>Clear filters</Button>} /> : events ? <section aria-labelledby="timeline-events" className="grid min-w-0 gap-4 lg:grid-cols-[11rem_minmax(0,1fr)]"><aside className="hidden rounded-md border border-border-subtle bg-surface-base p-3 lg:block"><h2 className="text-xs font-semibold uppercase tracking-wide text-text-muted">Temporal navigation</h2><p className="mt-3 text-sm text-text-secondary">Events are ordered by normalized event time, with untimed observations last.</p><p className="mt-3 font-mono text-xs text-accent">{start}–{end} / {events.meta.total}</p></aside><div className="min-w-0 rounded-md border border-border-subtle bg-surface-inset p-3 sm:p-4"><h2 id="timeline-events" className="sr-only">Timeline events</h2><ol className="space-y-4">{events.data.map((event) => <TimelineEventRow key={event.id} event={event} selected={selected?.id === event.id} onSelect={() => setSelected(event)} />)}</ol><div className="mt-5 flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {start}–{end} of {events.meta.total} events</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || timelineQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}>Previous</Button><Button disabled={offset + PAGE_SIZE >= events.meta.total || timelineQuery.isFetching} onClick={() => setOffset((current) => current + PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div></div></section> : null}
    <GenerateTimelineDialog open={generateOpen} onOpenChange={setGenerateOpen} pending={generateMutation.isPending} onGenerate={generate} />
    <TimelineEventDrawer event={selected} caseId={caseId} open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null) }} />
  </div>
}
