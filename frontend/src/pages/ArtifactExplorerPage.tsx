import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ChevronLeft, ChevronRight, ExternalLink, ScanSearch } from 'lucide-react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api'
import { ArtifactTypeBadge, Button, DataTable, EmptyState, ErrorState, MonospaceValue, NotFoundState, PageHeader, ParseEvidenceDialog, StatusBadge, TimestampValue, type DataTableColumn } from '../components'
import { EvidenceListSkeleton } from '../components/evidence/EvidenceListSkeleton'
import { useCase, useCaseEvidence, useEvidenceArtifacts, useParseEvidence } from '../hooks'
import type { ArtifactRecord, EvidenceRecord, ProductionArtifactType } from '../types'
import { cn, getErrorMessage } from '../utils'

const EVIDENCE_LIMIT = 100
const ARTIFACT_PAGE_SIZE = 25

export function ArtifactExplorerPage() {
  const { caseId = '' } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [offset, setOffset] = useState(0)
  const [parseOpen, setParseOpen] = useState(false)
  const caseQuery = useCase(caseId)
  const evidenceQuery = useCaseEvidence(caseId, { limit: EVIDENCE_LIMIT, offset: 0 })
  const evidenceItems = evidenceQuery.data?.data ?? []
  const requestedEvidenceId = searchParams.get('evidence') ?? ''
  const selectedEvidence = evidenceItems.find((item) => item.id === requestedEvidenceId) ?? evidenceItems[0]
  const artifactsQuery = useEvidenceArtifacts(selectedEvidence?.id ?? '', { limit: ARTIFACT_PAGE_SIZE, offset })
  const parser = useParseEvidence(selectedEvidence?.id ?? '')

  useEffect(() => {
    if (!requestedEvidenceId && selectedEvidence) setSearchParams({ evidence: selectedEvidence.id }, { replace: true })
  }, [requestedEvidenceId, selectedEvidence, setSearchParams])

  const columns = useMemo<DataTableColumn<ArtifactRecord>[]>(() => [
    { id: 'type', header: 'Artifact type', cell: (artifact) => <Link className="inline-flex items-center gap-1.5 rounded-sm" to={`/cases/${caseId}/artifacts/${artifact.id}`}><ArtifactTypeBadge type={artifact.artifact_type} /><ExternalLink aria-hidden="true" className="size-3.5 text-accent" /></Link> },
    { id: 'parser', header: 'Parser', cell: (artifact) => <div><p className="font-medium text-text-primary">{artifact.parser_name}</p><MonospaceValue className="mt-1 block text-xs text-text-muted">v{artifact.parser_version}</MonospaceValue></div> },
    { id: 'status', header: 'Status', cell: (artifact) => <StatusBadge status={artifact.status} /> },
    { id: 'records', header: 'Records', align: 'right', cell: (artifact) => <span className="forensic-mono tabular-nums">{artifact.record_count}</span> },
    { id: 'warnings', header: 'Warnings', align: 'right', cell: (artifact) => <span className={cn('forensic-mono tabular-nums', artifact.warnings.length ? 'text-warning' : 'text-text-muted')}>{artifact.warnings.length}</span> },
    { id: 'created', header: 'Created', cell: (artifact) => <TimestampValue value={artifact.created_at} /> },
  ], [caseId])

  if (evidenceQuery.error instanceof ApiError && evidenceQuery.error.status === 404) return <NotFoundState title="Case not found" description="The requested case does not exist or is no longer available." />
  function selectEvidence(evidenceId: string) { setOffset(0); setSearchParams({ evidence: evidenceId }) }
  function parse(artifactType: ProductionArtifactType) { parser.mutate({ artifact_type: artifactType }, { onSuccess: (artifact) => { setParseOpen(false); navigate(`/cases/${caseId}/artifacts/${artifact.id}`, { state: { notice: `${artifact.parser_name} ${artifact.parser_version} completed with status ${artifact.status}.` } }) } }) }
  const data = artifactsQuery.data

  return <div className="space-y-6"><PageHeader eyebrow="Derived evidence" title="Artifact Explorer" description="Parser-derived forensic records with explicit evidence provenance." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Artifacts' }]} actions={selectedEvidence && <Button variant="primary" leadingIcon={<ScanSearch aria-hidden="true" className="size-4" />} onClick={() => setParseOpen(true)}>Parse evidence</Button>} />
    {evidenceQuery.isPending ? <EvidenceListSkeleton /> : evidenceQuery.isError ? <ErrorState description={getErrorMessage(evidenceQuery.error)} onRetry={() => void evidenceQuery.refetch()} /> : evidenceItems.length === 0 ? <EmptyState title="No evidence available for parsing" description="Register evidence before creating parser-derived artifacts." action={<Link to={`/cases/${caseId}/evidence`}><Button>Open evidence inventory</Button></Link>} /> : <>
      {evidenceQuery.data && evidenceQuery.data.meta.total > EVIDENCE_LIMIT && <div className="flex gap-2 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm text-warning"><AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />Showing the first {EVIDENCE_LIMIT} evidence items. Selectable case-wide aggregation is bounded because the backend has no case-level artifact endpoint.</div>}
      <div className="grid min-w-0 gap-4 lg:grid-cols-[17rem_minmax(0,1fr)]"><aside aria-label="Evidence sources" className="hidden self-start rounded-md border border-border-subtle bg-surface-base lg:block"><header className="border-b border-border-subtle px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-text-muted">Evidence sources</header><div className="max-h-[34rem] overflow-y-auto p-2 scrollbar-forensic">{evidenceItems.map((item) => <EvidenceSourceButton key={item.id} evidence={item} selected={item.id === selectedEvidence?.id} onSelect={() => selectEvidence(item.id)} />)}</div></aside><div className="min-w-0 space-y-4"><label className="block text-sm font-medium text-text-primary lg:hidden">Evidence source<select className="field-input mt-1.5" value={selectedEvidence?.id} onChange={(event) => selectEvidence(event.target.value)}>{evidenceItems.map((item) => <option key={item.id} value={item.id}>{item.evidence_number} · {item.name}</option>)}</select></label>
        {selectedEvidence && <section className="rounded-md border border-border-subtle bg-surface-base px-4 py-3"><span className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Selected evidence</span><div className="mt-1 flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3"><Link className="rounded-sm" to={`/cases/${caseId}/evidence/${selectedEvidence.id}`}><MonospaceValue className="text-accent">{selectedEvidence.evidence_number}</MonospaceValue></Link><span className="min-w-0 break-all text-sm text-text-secondary">{selectedEvidence.name}</span></div></section>}
        {artifactsQuery.isPending ? <EvidenceListSkeleton /> : artifactsQuery.isError ? <ErrorState title="Unable to load artifacts" description={getErrorMessage(artifactsQuery.error)} onRetry={() => void artifactsQuery.refetch()} /> : data && data.data.length === 0 && offset === 0 ? <EmptyState title="No parsed artifacts" description="Run a supported parser to create a derived artifact for this evidence item." action={<Button variant="primary" leadingIcon={<ScanSearch aria-hidden="true" className="size-4" />} onClick={() => setParseOpen(true)}>Parse evidence</Button>} /> : data ? <><div className="hidden md:block"><DataTable columns={columns} rows={data.data} getRowKey={(artifact) => artifact.id} caption="Parser-derived artifacts" /></div><div className="space-y-3 md:hidden">{data.data.map((artifact) => <Link key={artifact.id} to={`/cases/${caseId}/artifacts/${artifact.id}`} className="block rounded-md border border-border-subtle bg-surface-base p-4 hover:border-accent/45"><div className="flex flex-wrap items-center justify-between gap-2"><ArtifactTypeBadge type={artifact.artifact_type} /><StatusBadge status={artifact.status} /></div><p className="mt-3 text-sm font-medium text-text-primary">{artifact.parser_name} <MonospaceValue className="text-xs text-text-muted">v{artifact.parser_version}</MonospaceValue></p><dl className="mt-3 grid grid-cols-2 gap-3 border-t border-border-subtle pt-3 text-xs"><div><dt className="uppercase tracking-wide text-text-muted">Records</dt><dd className="forensic-mono mt-1 text-sm">{artifact.record_count}</dd></div><div><dt className="uppercase tracking-wide text-text-muted">Warnings</dt><dd className="forensic-mono mt-1 text-sm">{artifact.warnings.length}</dd></div></dl></Link>)}</div><Pagination offset={offset} total={data.meta.total} count={data.data.length} fetching={artifactsQuery.isFetching} onOffset={setOffset} /></> : null}
      </div></div>
    </>}
    {selectedEvidence && <ParseEvidenceDialog evidence={selectedEvidence} open={parseOpen} onOpenChange={(open) => { setParseOpen(open); if (!open) parser.reset() }} submitting={parser.isPending} error={parser.error} onSubmit={parse} />}
  </div>
}

function EvidenceSourceButton({ evidence, selected, onSelect }: { evidence: EvidenceRecord; selected: boolean; onSelect: () => void }) { return <button type="button" aria-pressed={selected} className={cn('mb-1 w-full rounded-md border px-3 py-2 text-left transition-colors duration-fast last:mb-0', selected ? 'border-accent/45 bg-accent/10' : 'border-transparent hover:border-border-subtle hover:bg-surface-raised')} onClick={onSelect}><MonospaceValue className={cn('block text-xs', selected && 'text-accent')}>{evidence.evidence_number}</MonospaceValue><span className="mt-1 block truncate text-sm text-text-secondary" title={evidence.name}>{evidence.name}</span></button> }
function Pagination({ offset, total, count, fetching, onOffset }: { offset: number; total: number; count: number; fetching: boolean; onOffset: (value: number) => void }) { const start = total ? offset + 1 : 0; const end = Math.min(offset + count, total); return <div className="flex flex-col gap-3 border-t border-border-subtle pt-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-text-secondary" aria-live="polite">Showing {start}–{end} of {total} artifacts</p><div className="flex gap-2"><Button leadingIcon={<ChevronLeft aria-hidden="true" className="size-4" />} disabled={offset === 0 || fetching} onClick={() => onOffset(Math.max(0, offset - ARTIFACT_PAGE_SIZE))}>Previous</Button><Button disabled={offset + ARTIFACT_PAGE_SIZE >= total || fetching} onClick={() => onOffset(offset + ARTIFACT_PAGE_SIZE)}>Next <ChevronRight aria-hidden="true" className="size-4" /></Button></div></div> }
