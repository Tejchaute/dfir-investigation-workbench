import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import { Button, ConfidenceBadge, ErrorState, LoadingState, MonospaceValue, NotFoundState, PageHeader, SeverityBadge, StatusBadge, TimestampValue } from '../components'
import { FindingProvenance } from '../components/findings/FindingProvenance'
import { FindingReviewForm } from '../components/findings/FindingReviewForm'
import { useFinding, useUpdateFinding } from '../hooks'
import type { FindingUpdateRequest } from '../types'
import { getErrorMessage } from '../utils'

export function FindingDetailPage() {
  const { findingId = '' } = useParams()
  const findingQuery = useFinding(findingId)
  const finding = findingQuery.data
  const updateMutation = useUpdateFinding(findingId, finding?.case_id ?? '')
  if (findingQuery.isPending) return <LoadingState label="Loading finding" />
  if (findingQuery.error instanceof ApiError && findingQuery.error.status === 404) return <NotFoundState title="Finding not found" description="The requested finding does not exist or is no longer available." />
  if (findingQuery.isError || !finding) return <ErrorState title="Unable to load finding" description={getErrorMessage(findingQuery.error)} onRetry={() => void findingQuery.refetch()} />
  function save(payload: FindingUpdateRequest, onSuccess: () => void) { updateMutation.mutate(payload, { onSuccess }) }
  return <div className="space-y-5"><PageHeader eyebrow="Analytical finding" title={finding.title} description="Backend-generated relationship requiring examiner interpretation; confidence is analytical metadata, not probability." breadcrumbs={[{ label: 'Cases', to: '/cases' }, { label: finding.case_id, to: `/cases/${finding.case_id}/overview` }, { label: 'Findings', to: `/cases/${finding.case_id}/findings` }, { label: finding.id }]} actions={<Link to={`/cases/${finding.case_id}/findings`}><Button variant="ghost" leadingIcon={<ArrowLeft aria-hidden="true" className="size-4" />}>Back to findings</Button></Link>} />
    <section className="rounded-md border border-border-subtle bg-surface-base p-4"><div className="flex flex-wrap items-center gap-2"><StatusBadge status={finding.status} /><SeverityBadge severity={finding.severity} /><ConfidenceBadge confidence={finding.confidence} /></div><dl className="mt-4 grid gap-3 sm:grid-cols-2"><Field label="Finding ID"><MonospaceValue>{finding.id}</MonospaceValue></Field><Field label="Finding type"><MonospaceValue>{finding.finding_type}</MonospaceValue></Field><Field label="Created"><TimestampValue value={finding.created_at} /></Field><Field label="Updated"><TimestampValue value={finding.updated_at} /></Field></dl></section>
    <section className="rounded-md border border-border-subtle bg-surface-base p-4"><h2 className="text-sm font-semibold text-text-primary">Observation and Analysis</h2><p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-text-secondary">{finding.description}</p><p className="mt-3 text-xs text-text-muted">Displayed exactly as stored by the backend. The frontend does not strengthen or summarize this statement.</p></section>
    <section className="rounded-md border border-border-subtle bg-surface-base p-4"><FindingReviewForm finding={finding} pending={updateMutation.isPending} error={updateMutation.error} onSave={save} /></section>
    <section className="rounded-md border border-border-subtle bg-surface-base p-4"><FindingProvenance finding={finding} /></section>
  </div>
}
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="min-w-0"><dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">{label}</dt><dd className="mt-1 min-w-0 break-words text-sm text-text-secondary">{children}</dd></div> }
