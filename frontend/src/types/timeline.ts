import type { PaginationMeta } from './case'

export type TimelineEventType = 'EVTX_EVENT' | 'REGISTRY_KEY_LAST_WRITE' | 'PREFETCH_EXECUTION' | 'LNK_METADATA_CREATION' | 'LNK_METADATA_ACCESS' | 'LNK_METADATA_MODIFICATION' | 'NTFS_SI_CREATION' | 'NTFS_SI_MODIFICATION' | 'NTFS_SI_MFT_CHANGE' | 'NTFS_SI_ACCESS' | 'NTFS_FN_CREATION' | 'NTFS_FN_MODIFICATION' | 'NTFS_FN_MFT_CHANGE' | 'NTFS_FN_ACCESS'
export type TimelineArtifactType = 'REFERENCE' | 'EVTX' | 'REGISTRY' | 'PREFETCH' | 'LNK' | 'NTFS' | 'NTFS_MFT'
export type TimestampPrecision = 'SECOND' | 'MILLISECOND' | 'MICROSECOND' | '100NS' | 'UNKNOWN'

export interface TimelineEventRecord {
  id: string; case_id: string; evidence_id: string; artifact_id: string; artifact_record_id: string
  parser_name: string; parser_version: string; artifact_type: TimelineArtifactType; event_type: TimelineEventType
  event_time: string | null; raw_time: string | null; time_source: string; time_semantics: string
  timestamp_precision: TimestampPrecision; event_ordinal: number; description: string; source_identifier: string | null
  metadata: Record<string, unknown>; provenance: Record<string, unknown>; created_at: string
}
export interface TimelineEventListResponse { data: TimelineEventRecord[]; meta: PaginationMeta }
export interface TimelineGenerationResult { case_id: string; artifacts_considered: number; records_considered: number; events_created: number; events_skipped: number; warnings: string[]; unsupported_artifact_types: TimelineArtifactType[] }
export interface TimelineFilters { startTime?: string; endTime?: string; eventType?: TimelineEventType; artifactType?: TimelineArtifactType; evidenceId?: string; sourceIdentifier?: string }
