import type { PaginationMeta } from './case'

export type ReportFormat = 'json' | 'html' | 'pdf'
export type ReportType = 'FORENSIC_INVESTIGATION_REPORT'
export type ReportStatus = 'GENERATED' | 'FAILED'

export interface ReportArtifactRecord {
  id: string
  format: ReportFormat
  content_hash: string
  size_bytes: number
  created_at: string
}

export interface ReportRecord {
  id: string
  case_id: string
  report_type: ReportType
  report_version: string
  status: ReportStatus
  generated_at: string
  generated_by: string
  content_hash: string
  artifacts: ReportArtifactRecord[]
  created_at: string
}

export interface ReportCreateRequest { format: ReportFormat; report_type?: ReportType }
export interface ReportListResponse { data: ReportRecord[]; meta: PaginationMeta }
