import { Navigate, Route, Routes } from 'react-router-dom'
import { ApplicationShell } from './components/shell/ApplicationShell'
import { CaseOverviewPage } from './pages/CaseOverviewPage'
import { CasesPage } from './pages/CasesPage'
import { EvidenceDetailPage } from './pages/EvidenceDetailPage'
import { EvidencePage } from './pages/EvidencePage'
import { FindingDetailPage } from './pages/FindingDetailPage'
import { FindingsPage } from './pages/FindingsPage'
import { ReportDetailPage } from './pages/ReportDetailPage'
import { ReportsPage } from './pages/ReportsPage'
import { ArtifactDetailPage } from './pages/ArtifactDetailPage'
import { ArtifactExplorerPage } from './pages/ArtifactExplorerPage'
import { TimelinePage } from './pages/TimelinePage'
import { CorrelationPage } from './pages/CorrelationPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { WorkspacePage } from './pages/WorkspacePage'

export default function App() {
  return <Routes><Route element={<ApplicationShell />}><Route index element={<Navigate to="/cases" replace />} /><Route path="cases" element={<CasesPage />} /><Route path="cases/:caseId"><Route index element={<Navigate to="overview" replace />} /><Route path="overview" element={<CaseOverviewPage />} /><Route path="evidence" element={<EvidencePage />} /><Route path="evidence/:evidenceId" element={<EvidenceDetailPage />} /><Route path="artifacts" element={<ArtifactExplorerPage />} /><Route path="artifacts/:artifactId" element={<ArtifactDetailPage />} /><Route path="timeline" element={<TimelinePage />} /><Route path="correlations" element={<CorrelationPage />} /><Route path="findings" element={<FindingsPage />} /><Route path="reports" element={<ReportsPage />} /><Route path="reports/:reportId" element={<ReportDetailPage />} /><Route path="audit" element={<WorkspacePage kind="audit" />} /></Route><Route path="findings/:findingId" element={<FindingDetailPage />} /><Route path="reports/:reportId" element={<ReportDetailPage />} /><Route path="settings" element={<WorkspacePage kind="settings" />} /><Route path="*" element={<NotFoundPage />} /></Route></Routes>
}
