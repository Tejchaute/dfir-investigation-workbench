import type { CorrelationFilters, CorrelationMatchListResponse, CorrelationRunRecord } from '../types'
import { apiClient } from './client'

export interface CorrelationListParameters extends CorrelationFilters { limit: number; offset: number }
export const correlationApi = {
  run: (caseId: string) => apiClient.post<CorrelationRunRecord>(`/api/cases/${caseId}/correlation/run`),
  list: (caseId: string, p: CorrelationListParameters, signal?: AbortSignal) => apiClient.get<CorrelationMatchListResponse>(`/api/cases/${caseId}/correlations`, { query: { rule_id: p.ruleId, correlation_run_id: p.correlationRunId, limit: p.limit, offset: p.offset }, signal }),
}
