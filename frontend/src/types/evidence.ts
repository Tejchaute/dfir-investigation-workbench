import type { PaginationMeta } from './case'

export type EvidenceType = 'DISK_IMAGE' | 'LOG_FILE' | 'MEMORY_DUMP' | 'REGISTRY_HIVE' | 'FILE' | 'DIRECTORY' | 'OTHER'

export interface EvidenceRecord {
  id: string
  case_id: string
  evidence_number: string
  name: string
  description: string | null
  evidence_type: EvidenceType
  size_bytes: number | null
  collected_by: string | null
  collected_at: string | null
  created_at: string
  updated_at: string
}

export interface EvidenceListResponse { data: EvidenceRecord[]; meta: PaginationMeta }
export interface EvidenceHashRecord { id: string; evidence_id: string; algorithm: string; digest: string; computed_at: string; purpose: string }
export interface CustodyEntry { id: string; evidence_id: string; timestamp: string; person: string; action: string; location: string | null; notes: string | null; created_at: string }
export interface EvidenceVerification { evidence_id: string; algorithm: string; recorded_digest: string; calculated_digest: string; match: boolean; verified_at: string }
export interface EvidenceRegistrationRequest {
  file: File
  evidence_type: EvidenceType
  custody_person: string
  description?: string
  collected_by?: string
  collected_at?: string
  custody_location?: string
  custody_notes?: string
}
