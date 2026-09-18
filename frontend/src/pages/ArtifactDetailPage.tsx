import { useState } from 'react'
import { AlertTriangle, ArrowLeft, ChevronLeft, ChevronRight, FileJson } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { ArtifactTypeBadge, Button, EmptyState, ErrorState, LoadingState, MonospaceValue, NotFoundState, PageHeader, ParserDiagnostics, ProvenanceChain, StatusBadge, StructuredDataViewer, SuccessNotice, TimestampValue } from '../components'
import { useArtifact, useArtifactRecords, useCase, useEvidence } from '../hooks'
import type { DerivedArtifactRecord, ParserStatus } from '../types'
import { getErrorMessage } from '../utils'

const RECORD_PAGE_SIZE = 25

export function ArtifactDetailPage() {
  const { caseId = '', artifactId = '' } = useParams()
  const location = useLocation()
  const [offset, setOffset] = useState(0)
  const artifactQuery = useArtifact(artifactId)
  const artifact = artifactQuery.data
  const evidenceQuery = useEvidence(artifact?.evidence_id ?? '')
  const recordsQuery = useArtifactRecords(artifactId, { limit: RECORD_PAGE_SIZE, offset })
  const caseQuery = useCase(caseId)
  const notice = (location.state as { notice?: string } | null)?.notice

  if (artifactQuery.isPending) return <LoadingState label="Loading artifact result" />
  if (artifactQuery.error instanceof ApiError && artifactQuery.error.status === 404) return <NotFoundState title="Artifact not found" description="The requested parser-derived artifact does not exist or is no longer available." action={<Link to={`/cases/${caseId}/artifacts`}><Button leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />}>Artifact Explorer</Button></Link>} />
  if (artifactQuery.isError) return <ErrorState description={getErrorMessage(artifactQuery.error)} onRetry={() => void artifactQuery.refetch()} />
  if (!artifact) return null
  if (evidenceQuery.isPending) return <LoadingState label="Resolving artifact provenance" />
  if (evidenceQuery.isError) return <ErrorState title="Unable to resolve source evidence" description={getErrorMessage(evidenceQuery.error)} onRetry={() => void evidenceQuery.refetch()} />
  const evidence = evidenceQuery.data
  if (!evidence || evidence.case_id !== caseId) return <NotFoundState title="Artifact not found in this case" description="The artifact's authoritative evidence source is not associated with the active case." />
  const records = recordsQuery.data
  const start = records?.meta.total ? records.meta.offset + 1 : 0
  const end = records ? Math.min(records.meta.offset + records.data.length, records.meta.total) : 0

  return <div className="space-y-6"><PageHeader eyebrow="Parser result" title={`${artifact.artifact_type.replaceAll('_', ' ')} artifact`} description="Derived artifact metadata, diagnostics, records, and evidence provenance." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Artifacts', to: `/cases/${caseId}/artifacts?evidence=${evidence.id}` }, { label: artifact.id }]} />
    {notice && <SuccessNotice message={notice} />}
    <section aria-labelledby="artifact-identification" className="rounded-md border border-border-subtle bg-surface-base"><header className="flex flex-col gap-3 border-b border-border-subtle px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">Artifact identification</p><h2 id="artifact-identification" className="mt-1"><MonospaceValue className="text-sm font-semibold text-accent">{artifact.id}</MonospaceValue></h2></div><div className="flex flex-wrap gap-2"><ArtifactTypeBadge type={artifact.artifact_type} /><StatusBadge status={artifact.status} /></div></header><dl className="grid gap-px bg-border-subtle sm:grid-cols-2 xl:grid-cols-4"><Info label="Parser">{artifact.parser_name}</Info><Info label="Parser version"><MonospaceValue className="text-xs">{artifact.parser_version}</MonospaceValue></Info><Info label="Record count"><span className="forensic-mono">{artifact.record_count}</span></Info><Info label="Created"><TimestampValue value={artifact.created_at} /></Info></dl></section>
    <section aria-labelledby="artifact-provenance" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 id="artifact-provenance" className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-primary">Provenance</h2><ProvenanceChain nodes={[{ label: 'Evidence', id: evidence.id, to: `/cases/${caseId}/evidence/${evidence.id}` }, { label: 'Artifact', id: artifact.id }]} /><p className="mt-3 text-sm text-text-secondary">Source: <MonospaceValue className="text-xs text-accent">{evidence.evidence_number}</MonospaceValue> · <span className="break-all">{evidence.name}</span></p></section>
    {(artifact.status === 'FAILED' || artifact.status === 'UNSUPPORTED') && <div className="flex gap-2 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger"><AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />The parser recorded status {artifact.status}. This describes parser execution and is not a conclusion about the evidence.</div>}
    <section aria-labelledby="parser-result" className="grid gap-4 lg:grid-cols-2"><div className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 id="parser-result" className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-primary">Parser diagnostics</h2><ParserDiagnostics warnings={artifact.warnings} errors={artifact.errors} /></div><div className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-primary">Parser metadata</h2><StructuredDataViewer value={{ metadata: artifact.metadata, statistics: artifact.statistics }} label="Parser metadata" /></div></section>
    <section aria-labelledby="artifact-records" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><div className="mb-4 flex items-center gap-2"><FileJson aria-hidden="true" className="size-4 text-accent" /><h2 id="artifact-records" className="text-sm font-semibold uppercase tracking-wide text-text-primary">Artifact Records</h2></div>{recordsQuery.isPending ? <LoadingState label="Loading Artifact Records" /> : recordsQuery.isError ? <ErrorState title="Unable to load Artifact Records" description={getErrorMessage(recordsQuery.error)} onRetry={() => void recordsQuery.refetch()} /> : records && records.data.length === 0 ? <EmptyState title="No Artifact Records" description={emptyRecordDescription(artifact.status)} /> : records ? <><div className="space-y-3">{records.data.map((record) => <ArtifactRecordPanel key={record.id} record={record} evidenceId={evidence.id} artifactId={artifact.id} caseId={caseId} />)}</div><div className="mt-4 flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {start}–{end} of {records.meta.total} records</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || recordsQuery.isFetching} onClick={() => setOffset((current) => Math.max(0, current - RECORD_PAGE_SIZE))}>Previous</Button><Button disabled={offset + RECORD_PAGE_SIZE >= records.meta.total || recordsQuery.isFetching} onClick={() => setOffset((current) => current + RECORD_PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div></> : null}</section>
  </div>
}

function emptyRecordDescription(status: ParserStatus): string {
  switch (status) {
    case 'PENDING':
      return 'Parser execution is pending; no Artifact Records have been persisted yet.'
    case 'RUNNING':
      return 'Parser execution is still running; no Artifact Records are currently available.'
    case 'COMPLETED':
      return 'The parser completed and persisted zero Artifact Records. This does not establish absence of activity.'
    case 'COMPLETED_WITH_WARNINGS':
      return 'The parser completed with warnings and persisted zero Artifact Records. Review the parser warnings for structures that could not be decoded.'
    case 'FAILED':
      return 'The parser failed before it could safely persist Artifact Records. This status does not characterize the evidence as malicious or corrupted.'
    case 'UNSUPPORTED':
      return 'The evidence input or format variant is unsupported by this parser, so no Artifact Records were persisted. Unsupported status does not characterize the evidence.'
  }
}

function ArtifactRecordPanel({ record, evidenceId, artifactId, caseId }: { record: DerivedArtifactRecord; evidenceId: string; artifactId: string; caseId: string }) { return <details className="group min-w-0 rounded-md border border-border-subtle bg-surface-inset"><summary className="cursor-pointer list-none p-4 focus-visible:ring-inset"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0"><span className="text-xs font-semibold uppercase tracking-wide text-accent">{record.record_type}</span><MonospaceValue className="mt-1 block text-xs text-text-secondary">{record.source_record_identifier ?? record.id}</MonospaceValue></div><TimestampValue value={record.event_time} semantics="artifact record event time" /></div></summary><div className="space-y-4 border-t border-border-subtle p-4"><ProvenanceChain nodes={[{ label: 'Evidence', id: evidenceId, to: `/cases/${caseId}/evidence/${evidenceId}` }, { label: 'Artifact', id: artifactId }, { label: 'Artifact record', id: record.id }]} /><div><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Normalized data</h3><StructuredDataViewer value={record.data} label="Normalized record data" /></div><div><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Record provenance</h3><StructuredDataViewer value={record.provenance} label="Record provenance" /></div><p className="text-xs text-text-muted">Persisted <TimestampValue value={record.created_at} /></p></div></details> }
function Info({ label, children }: { label: string; children: React.ReactNode }) { return <div className="min-w-0 bg-surface-base px-4 py-3"><dt className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">{label}</dt><dd className="mt-1.5 min-w-0 break-words text-sm text-text-secondary">{children}</dd></div> }
