import type { PaginationMeta } from './case'

export type ProductionArtifactType = 'EVTX' | 'REGISTRY' | 'PREFETCH' | 'LNK' | 'NTFS_MFT'
export type ParserStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED' | 'UNSUPPORTED'

export interface ArtifactRecord {
  id: string
  evidence_id: string
  artifact_type: ProductionArtifactType | string
  parser_name: string
  parser_version: string
  status: ParserStatus
  metadata: Record<string, unknown>
  warnings: string[]
  errors: string[]
  statistics: Record<string, number>
  record_count: number
  created_at: string
}

export interface ArtifactListResponse { data: ArtifactRecord[]; meta: PaginationMeta }

export interface DerivedArtifactRecord {
  id: string
  artifact_id: string
  record_type: string
  source_record_identifier: string | null
  event_time: string | null
  data: Record<string, unknown>
  provenance: Record<string, unknown>
  created_at: string
}

export interface ArtifactRecordListResponse { data: DerivedArtifactRecord[]; meta: PaginationMeta }
export interface ParseEvidenceRequest { artifact_type: ProductionArtifactType }
