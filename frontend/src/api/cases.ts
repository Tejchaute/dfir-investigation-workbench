import { apiClient } from './client'
import type { CaseCreateRequest, CaseListResponse, CaseRecord, CaseUpdateRequest } from '../types'

export interface CaseListParameters { limit: number; offset: number }

export const caseApi = {
  list: (parameters: CaseListParameters, signal?: AbortSignal) => apiClient.get<CaseListResponse>('/api/cases', { query: { limit: parameters.limit, offset: parameters.offset }, signal }),
  get: (caseId: string, signal?: AbortSignal) => apiClient.get<CaseRecord>(`/api/cases/${caseId}`, { signal }),
  create: (payload: CaseCreateRequest) => apiClient.post<CaseRecord, CaseCreateRequest>('/api/cases', payload),
  update: (caseId: string, payload: CaseUpdateRequest) => apiClient.patch<CaseRecord, CaseUpdateRequest>(`/api/cases/${caseId}`, payload),
  close: (caseId: string) => apiClient.post<CaseRecord>(`/api/cases/${caseId}/close`),
  archive: (caseId: string) => apiClient.post<CaseRecord>(`/api/cases/${caseId}/archive`),
}
