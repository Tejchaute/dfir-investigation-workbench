import type { PaginationMeta } from './case'
import type { CorrelationSupportingEvent } from './correlation'

export type FindingStatus = 'OPEN' | 'REVIEWED' | 'RESOLVED' | 'DISMISSED'
export type FindingSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type FindingConfidence = 'LOW' | 'MEDIUM' | 'HIGH'
export type FindingType = 'PROCESS_EXECUTION_CORROBORATED' | 'LNK_PROCESS_ASSOCIATION' | 'FILE_ACTIVITY_ASSOCIATION' | 'REGISTRY_PROCESS_ASSOCIATION'

export interface FindingRecord {
  id: string
  case_id: string
  correlation_run_id: string
  correlation_match_id: string
  finding_type: FindingType
  title: string
  description: string
  status: FindingStatus
  severity: FindingSeverity
  confidence: FindingConfidence
  rule_id: string
  rule_version: string
  deterministic_key: string
  analyst_notes: string | null
  metadata: Record<string, unknown>
  timeline_event_ids: string[]
  supporting_events: CorrelationSupportingEvent[]
  created_at: string
  updated_at: string
}

export interface FindingListResponse { data: FindingRecord[]; meta: PaginationMeta }
export interface FindingFilters { status?: FindingStatus; severity?: FindingSeverity; confidence?: FindingConfidence; ruleId?: string }
export interface FindingUpdateRequest { status?: FindingStatus; severity?: FindingSeverity; confidence?: FindingConfidence; analyst_notes?: string | null }
