import type { LucideIcon } from 'lucide-react'
import { Activity, Boxes, FileOutput, FileSearch, Fingerprint, LayoutDashboard, ScrollText, Settings, ShieldCheck } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { EmptyState, PageHeader, UnsupportedState } from '../components'

interface WorkspaceConfig { title: string; eyebrow: string; description: string; icon: LucideIcon; unsupported?: boolean }
const workspaces: Record<string, WorkspaceConfig> = {
  overview: { title: 'Case Overview', eyebrow: 'Case', description: 'Authoritative case metadata and lifecycle actions for the active investigation.', icon: LayoutDashboard },
  evidence: { title: 'Evidence', eyebrow: 'Case', description: 'Registered Evidence, integrity records, and Chain of Custody history.', icon: Fingerprint },
  'evidence-detail': { title: 'Evidence Detail', eyebrow: 'Evidence', description: 'Read-only Evidence metadata, Evidence Hash records, Chain of Custody, and derived-data navigation.', icon: Fingerprint },
  artifacts: { title: 'Artifacts', eyebrow: 'Case', description: 'Parser-derived Artifacts and their persisted Artifact Records.', icon: Boxes },
  'artifact-detail': { title: 'Artifact Detail', eyebrow: 'Artifact', description: 'Parser diagnostics, Artifact Records, and source Evidence provenance.', icon: Boxes },
  timeline: { title: 'Timeline', eyebrow: 'Analysis', description: 'Persisted Timeline Events with source timestamp semantics and provenance.', icon: Activity },
  correlations: { title: 'Correlations', eyebrow: 'Analysis', description: 'Deterministic Correlation Matches explained without implying causality or probability.', icon: FileSearch },
  findings: { title: 'Findings', eyebrow: 'Analysis', description: 'Evidence-backed Findings with stored language, confidence, review state, and provenance.', icon: ShieldCheck },
  'finding-detail': { title: 'Finding Detail', eyebrow: 'Finding', description: 'The stored analytical relationship, examiner review fields, and supporting provenance.', icon: ShieldCheck },
  reports: { title: 'Reports', eyebrow: 'Output', description: 'Immutable JSON, HTML, and PDF Report Artifacts generated from persisted report snapshots.', icon: FileOutput },
  'report-detail': { title: 'Report Detail', eyebrow: 'Report', description: 'Immutable Report metadata, Report Artifact hashes, and controlled download actions.', icon: FileOutput },
  audit: { title: 'Audit', eyebrow: 'Output', description: 'Backend operations create Audit Events, but the backend does not expose an Audit Event read endpoint for this workspace.', icon: ScrollText, unsupported: true },
  settings: { title: 'Settings', eyebrow: 'System', description: 'Application configuration is supplied outside this interface. The backend does not expose a settings API.', icon: Settings, unsupported: true },
}

export function WorkspacePage({ kind }: { kind: keyof typeof workspaces }) {
  const config = workspaces[kind]
  const { caseId, evidenceId, artifactId, findingId, reportId } = useParams()
  const resourceId = evidenceId ?? artifactId ?? findingId ?? reportId
  const Icon = config.icon
  return <div className="space-y-6"><PageHeader eyebrow={config.eyebrow} title={config.title} description={config.description} breadcrumbs={[{ label: 'Cases', to: '/cases' }, ...(caseId ? [{ label: caseId, to: `/cases/${caseId}/overview` }] : []), { label: config.title }]} />{config.unsupported ? <UnsupportedState title={`${config.title} unavailable`} description={config.description} /> : <EmptyState title={`No ${config.title.toLowerCase()} records`} description={resourceId ? `No backend record is available for ${resourceId}.` : `No ${config.title.toLowerCase()} records are currently available.`} action={<div className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted"><Icon aria-hidden="true" className="size-4" />No records available</div>} />}</div>
}
