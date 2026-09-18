import type { ArtifactListResponse, ArtifactRecord, ArtifactRecordListResponse, ParseEvidenceRequest } from '../types'
import { apiClient } from './client'

export interface ArtifactListParameters { limit: number; offset: number }
export interface ArtifactRecordListParameters { limit: number; offset: number }

export const artifactApi = {
  parse: (evidenceId: string, payload: ParseEvidenceRequest) => apiClient.post<ArtifactRecord, ParseEvidenceRequest>(`/api/evidence/${evidenceId}/parse`, payload),
  listForEvidence: (evidenceId: string, parameters: ArtifactListParameters, signal?: AbortSignal) => apiClient.get<ArtifactListResponse>(`/api/evidence/${evidenceId}/artifacts`, { query: { limit: parameters.limit, offset: parameters.offset }, signal }),
  get: (artifactId: string, signal?: AbortSignal) => apiClient.get<ArtifactRecord>(`/api/artifacts/${artifactId}`, { signal }),
  records: (artifactId: string, parameters: ArtifactRecordListParameters, signal?: AbortSignal) => apiClient.get<ArtifactRecordListResponse>(`/api/artifacts/${artifactId}/records`, { query: { limit: parameters.limit, offset: parameters.offset }, signal }),
}
