import type { FindingFilters, FindingListResponse, FindingRecord, FindingUpdateRequest } from '../types'
import { apiClient } from './client'

export interface FindingListParameters extends FindingFilters { limit: number; offset: number }

export const findingApi = {
  list: (caseId: string, parameters: FindingListParameters, signal?: AbortSignal) => apiClient.get<FindingListResponse>(`/api/cases/${caseId}/findings`, { query: { status: parameters.status, severity: parameters.severity, confidence: parameters.confidence, rule_id: parameters.ruleId, limit: parameters.limit, offset: parameters.offset }, signal }),
  get: (findingId: string, signal?: AbortSignal) => apiClient.get<FindingRecord>(`/api/findings/${findingId}`, { signal }),
  update: (findingId: string, payload: FindingUpdateRequest) => apiClient.patch<FindingRecord, FindingUpdateRequest>(`/api/findings/${findingId}`, payload),
}
