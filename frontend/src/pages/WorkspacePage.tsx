import type { LucideIcon } from 'lucide-react'
import { Activity, Boxes, FileOutput, FileSearch, Fingerprint, LayoutDashboard, ScrollText, Settings, ShieldCheck } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { EmptyState, PageHeader, UnsupportedState } from '../components'

interface WorkspaceConfig { title: string; eyebrow: string; description: string; icon: LucideIcon; unsupported?: boolean }
const workspaces: Record<string, WorkspaceConfig> = {
  overview: { title: 'Case Overview', eyebrow: 'Case', description: 'Case context and investigation workflow will appear here when the overview feature is implemented.', icon: LayoutDashboard },
  evidence: { title: 'Evidence', eyebrow: 'Case', description: 'Registered evidence, integrity observations, and custody history will be managed in a later frontend increment.', icon: Fingerprint },
  'evidence-detail': { title: 'Evidence Detail', eyebrow: 'Evidence', description: 'Evidence metadata, hashes, custody, and derived records will appear here without permitting evidence mutation.', icon: Fingerprint },
  artifacts: { title: 'Artifacts', eyebrow: 'Case', description: 'Parsed artifact executions and normalized records will be available in the artifact explorer.', icon: Boxes },
  'artifact-detail': { title: 'Artifact Detail', eyebrow: 'Artifact', description: 'Parser diagnostics, records, and evidence provenance will appear here.', icon: Boxes },
  timeline: { title: 'Timeline', eyebrow: 'Analysis', description: 'Normalized forensic observations will be presented with their source timestamp semantics and provenance.', icon: Activity },
  correlations: { title: 'Correlations', eyebrow: 'Analysis', description: 'Deterministic rule matches will be explained without implying causality or probability.', icon: FileSearch },
  findings: { title: 'Findings', eyebrow: 'Analysis', description: 'Evidence-backed analytical findings will preserve their stored language, confidence, and provenance.', icon: ShieldCheck },
  'finding-detail': { title: 'Finding Detail', eyebrow: 'Finding', description: 'The analytical relationship and complete provenance chain will appear here.', icon: ShieldCheck },
  reports: { title: 'Reports', eyebrow: 'Output', description: 'Generated JSON, HTML, and PDF report artifacts will be available in a later frontend increment.', icon: FileOutput },
  'report-detail': { title: 'Report Detail', eyebrow: 'Report', description: 'Immutable report metadata, hashes, and download actions will appear here.', icon: FileOutput },
  audit: { title: 'Audit', eyebrow: 'Output', description: 'Audit records are not available because the backend does not currently expose a read endpoint.', icon: ScrollText, unsupported: true },
  settings: { title: 'Settings', eyebrow: 'System', description: 'Frontend preferences and supported connection information will appear here. No backend settings API is currently available.', icon: Settings, unsupported: true },
}

export function WorkspacePage({ kind }: { kind: keyof typeof workspaces }) {
  const config = workspaces[kind]
  const { caseId, evidenceId, artifactId, findingId, reportId } = useParams()
  const resourceId = evidenceId ?? artifactId ?? findingId ?? reportId
  const Icon = config.icon
  return <div className="space-y-6"><PageHeader eyebrow={config.eyebrow} title={config.title} description={config.description} breadcrumbs={[{ label: 'Cases', to: '/cases' }, ...(caseId ? [{ label: caseId, to: `/cases/${caseId}/overview` }] : []), { label: config.title }]} />{config.unsupported ? <UnsupportedState title={`${config.title} unavailable`} description={config.description} /> : <EmptyState title={`${config.title} foundation ready`} description={resourceId ? `Route context is established for ${resourceId}. No forensic values are fabricated while this feature is pending.` : 'The route, layout, and state foundation are ready. Feature data is intentionally not implemented in Phase 10.1–10.2.'} action={<div className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted"><Icon aria-hidden="true" className="size-4" />Feature implementation pending</div>} />}</div>
}
