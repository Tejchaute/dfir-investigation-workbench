import { useState } from 'react'
import { ArrowLeft, Database, ShieldCheck } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Badge, Button, ErrorState, LoadingState, MonospaceValue, NotFoundState, PageHeader, StatusBadge, SuccessNotice, TimestampValue } from '../components'
import { CustodyTimeline } from '../components/evidence/CustodyTimeline'
import { EvidenceHashes } from '../components/evidence/EvidenceHashes'
import { EvidenceVerificationDialog } from '../components/evidence/EvidenceVerificationDialog'
import { useCase, useEvidence, useEvidenceCustody, useEvidenceHashes, useVerifyEvidence } from '../hooks'
import { formatBytes, getErrorMessage } from '../utils'

export function EvidenceDetailPage() {
  const { caseId = '', evidenceId = '' } = useParams()
  const location = useLocation()
  const caseQuery = useCase(caseId)
  const evidenceQuery = useEvidence(evidenceId)
  const hashesQuery = useEvidenceHashes(evidenceId)
  const custodyQuery = useEvidenceCustody(evidenceId)
  const verification = useVerifyEvidence(evidenceId)
  const [verifyOpen, setVerifyOpen] = useState(false)
  const registrationNotice = (location.state as { notice?: string } | null)?.notice

  if (evidenceQuery.isPending) return <LoadingState label="Loading evidence record" />
  if (evidenceQuery.error instanceof ApiError && evidenceQuery.error.status === 404) return <NotFoundState title="Evidence not found" description="The requested evidence does not exist or is no longer available." action={<Link to={`/cases/${caseId}/evidence`}><Button leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />}>Evidence inventory</Button></Link>} />
  if (evidenceQuery.isError) return <ErrorState description={getErrorMessage(evidenceQuery.error)} onRetry={() => void evidenceQuery.refetch()} />
  const evidence = evidenceQuery.data
  if (!evidence) return null
  if (evidence.case_id !== caseId) return <NotFoundState title="Evidence not found in this case" description="The requested evidence is not associated with the active case." action={<Link to={`/cases/${caseId}/evidence`}><Button>Evidence inventory</Button></Link>} />

  function verify() { verification.mutate(undefined, { onSuccess: () => setVerifyOpen(false) }) }

  return <div className="space-y-6"><PageHeader eyebrow="Evidence record" title={evidence.name} description="Authoritative evidence metadata, integrity records, and custody history." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: caseQuery.data?.case_number ?? 'Case', to: `/cases/${caseId}/overview` }, { label: 'Evidence', to: `/cases/${caseId}/evidence` }, { label: evidence.evidence_number }]} actions={<Button variant="primary" leadingIcon={<ShieldCheck aria-hidden="true" className="size-4" />} onClick={() => setVerifyOpen(true)}>Verify integrity</Button>} />
    {registrationNotice && <SuccessNotice message={registrationNotice} />}
    {verification.data && <div role="status" aria-live="polite" className={`rounded-md border px-4 py-3 ${verification.data.match ? 'border-integrity-match/30 bg-integrity-match/10' : 'border-integrity-mismatch/30 bg-integrity-mismatch/10'}`}><div className="flex flex-wrap items-center gap-3"><StatusBadge status={verification.data.match ? 'MATCH' : 'MISMATCH'} /><p className="text-sm font-semibold text-text-primary">Verification completed</p></div><p className="mt-2 text-sm text-text-secondary">The backend-calculated SHA-256 {verification.data.match ? 'matches' : 'does not match'} the recorded acquisition SHA-256.</p><TimestampValue value={verification.data.verified_at} semantics="verification completed" /></div>}
    <section aria-labelledby="evidence-identification" className="rounded-md border border-border-subtle bg-surface-base"><header className="flex flex-col gap-3 border-b border-border-subtle px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">Evidence identification</p><h2 id="evidence-identification" className="mt-1"><MonospaceValue className="text-lg font-semibold text-accent">{evidence.evidence_number}</MonospaceValue></h2></div><Badge>{evidence.evidence_type.replaceAll('_', ' ')}</Badge></header><dl className="grid gap-px bg-border-subtle sm:grid-cols-2 xl:grid-cols-4"><Info label="Evidence ID"><MonospaceValue className="text-xs">{evidence.id}</MonospaceValue></Info><Info label="Size"><span className="forensic-mono">{formatBytes(evidence.size_bytes)}</span></Info><Info label="Registered"><TimestampValue value={evidence.created_at} /></Info><Info label="Updated"><TimestampValue value={evidence.updated_at} /></Info></dl></section>
    <section aria-labelledby="evidence-metadata" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 id="evidence-metadata" className="text-sm font-semibold uppercase tracking-wide text-text-primary">Evidence metadata</h2><dl className="mt-4 grid gap-5 md:grid-cols-2"><InfoBlock label="Original filename"><span className="break-all">{evidence.name}</span></InfoBlock><InfoBlock label="Collected by">{evidence.collected_by || 'Not supplied'}</InfoBlock><InfoBlock label="Collected at"><TimestampValue value={evidence.collected_at} /></InfoBlock><InfoBlock label="Description"><span className="whitespace-pre-wrap">{evidence.description || 'No description supplied.'}</span></InfoBlock></dl></section>
    <section aria-labelledby="integrity-records" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><div className="mb-4 flex items-center gap-2"><Database aria-hidden="true" className="size-4 text-accent" /><h2 id="integrity-records" className="text-sm font-semibold uppercase tracking-wide text-text-primary">Integrity records</h2></div>{hashesQuery.isPending ? <LoadingState label="Loading evidence hashes" /> : <EvidenceHashes records={hashesQuery.data} error={hashesQuery.error} onRetry={() => void hashesQuery.refetch()} />}</section>
    <section aria-labelledby="custody-history" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 id="custody-history" className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-primary">Chain of custody</h2>{custodyQuery.isPending ? <LoadingState label="Loading chain of custody" /> : <CustodyTimeline entries={custodyQuery.data} error={custodyQuery.error} onRetry={() => void custodyQuery.refetch()} />}</section>
    <section aria-labelledby="derived-data" className="rounded-md border border-border-subtle bg-surface-base p-4 sm:p-5"><h2 id="derived-data" className="text-sm font-semibold uppercase tracking-wide text-text-primary">Derived data</h2><p className="mt-2 text-sm leading-6 text-text-secondary">Parser-derived Artifacts and their persisted Artifact Records are available in the Artifact Explorer. This evidence page does not infer record counts that are not returned by the backend.</p><Link className="mt-3 inline-flex rounded-sm text-sm font-semibold text-accent hover:text-focus" to={`/cases/${caseId}/artifacts`}>Open Artifact Explorer</Link></section>
    <EvidenceVerificationDialog open={verifyOpen} onOpenChange={(open) => { setVerifyOpen(open); if (!open) verification.reset() }} submitting={verification.isPending} error={verification.error} onConfirm={verify} />
  </div>
}

function Info({ label, children }: { label: string; children: React.ReactNode }) { return <div className="min-w-0 bg-surface-base px-4 py-3"><dt className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">{label}</dt><dd className="mt-1.5 min-w-0 text-sm text-text-secondary">{children}</dd></div> }
function InfoBlock({ label, children }: { label: string; children: React.ReactNode }) { return <div><dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">{label}</dt><dd className="mt-1.5 text-sm leading-6 text-text-secondary">{children}</dd></div> }
