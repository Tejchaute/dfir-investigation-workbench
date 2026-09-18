import type { PaginationMeta } from './case'
import type { TimelineArtifactType, TimelineEventType } from './timeline'

export type CorrelationRunStatus = 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED'
export interface CorrelationRuleReference { rule_id: string; rule_version: string }
export interface CorrelationRunRecord {
  id: string; case_id: string; started_at: string; completed_at: string | null; status: CorrelationRunStatus
  rule_set_version: string; temporal_window_seconds: number; event_count: number; matched_count: number
  finding_count: number; rules_evaluated: CorrelationRuleReference[]; warnings: string[]; errors: string[]; created_at: string
}
export interface CorrelationSupportingEvent {
  id: string; evidence_id: string; artifact_id: string; artifact_record_id: string
  artifact_type: TimelineArtifactType; event_type: TimelineEventType; event_time: string | null
  source_identifier: string | null; metadata: Record<string, unknown>; provenance: Record<string, unknown>
}
export interface CorrelationMatchRecord {
  id: string; correlation_run_id: string; case_id: string; rule_id: string; rule_version: string
  deterministic_key: string; temporal_delta_seconds: number; match_basis: string; explanation: string
  metadata: Record<string, unknown>; timeline_event_ids: string[]; supporting_events: CorrelationSupportingEvent[]; created_at: string
}
export interface CorrelationMatchListResponse { data: CorrelationMatchRecord[]; meta: PaginationMeta }
export interface CorrelationFilters { ruleId?: string; correlationRunId?: string }
