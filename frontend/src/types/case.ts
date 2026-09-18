export type CaseStatus = 'OPEN' | 'CLOSED' | 'ARCHIVED'

export interface CaseRecord {
  id: string
  case_number: string
  name: string
  description: string | null
  investigator: string | null
  status: CaseStatus
  created_at: string
  updated_at: string
}

export interface CaseCreateRequest { name: string; description?: string | null; investigator?: string | null }
export interface CaseUpdateRequest { name?: string; description?: string | null; investigator?: string | null }
export interface PaginationMeta { limit: number; offset: number; total: number }
export interface CaseListResponse { data: CaseRecord[]; meta: PaginationMeta }
