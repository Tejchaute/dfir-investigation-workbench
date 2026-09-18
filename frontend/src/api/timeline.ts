import type { TimelineEventListResponse, TimelineFilters, TimelineGenerationResult } from '../types'
import { apiClient } from './client'

export interface TimelineListParameters extends TimelineFilters { limit: number; offset: number }
export const timelineApi = {
  generate: (caseId: string) => apiClient.post<TimelineGenerationResult>(`/api/cases/${caseId}/timeline/generate`),
  list: (caseId: string, p: TimelineListParameters, signal?: AbortSignal) => apiClient.get<TimelineEventListResponse>(`/api/cases/${caseId}/timeline`, { query: { start_time: p.startTime, end_time: p.endTime, event_type: p.eventType, artifact_type: p.artifactType, evidence_id: p.evidenceId, source_identifier: p.sourceIdentifier, limit: p.limit, offset: p.offset }, signal }),
}
