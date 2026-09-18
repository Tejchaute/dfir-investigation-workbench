import type { CustodyEntry, EvidenceHashRecord, EvidenceListResponse, EvidenceRecord, EvidenceRegistrationRequest, EvidenceVerification } from '../types'
import { apiClient } from './client'

export interface EvidenceListParameters { limit: number; offset: number }

function registrationForm(payload: EvidenceRegistrationRequest): FormData {
  const form = new FormData()
  form.append('file', payload.file, payload.file.name)
  form.append('evidence_type', payload.evidence_type)
  form.append('custody_person', payload.custody_person)
  if (payload.description) form.append('description', payload.description)
  if (payload.collected_by) form.append('collected_by', payload.collected_by)
  if (payload.collected_at) form.append('collected_at', payload.collected_at)
  if (payload.custody_location) form.append('custody_location', payload.custody_location)
  if (payload.custody_notes) form.append('custody_notes', payload.custody_notes)
  return form
}

export const evidenceApi = {
  list: (caseId: string, parameters: EvidenceListParameters, signal?: AbortSignal) => apiClient.get<EvidenceListResponse>(`/api/cases/${caseId}/evidence`, { query: { limit: parameters.limit, offset: parameters.offset }, signal }),
  get: (evidenceId: string, signal?: AbortSignal) => apiClient.get<EvidenceRecord>(`/api/evidence/${evidenceId}`, { signal }),
  hashes: (evidenceId: string, signal?: AbortSignal) => apiClient.get<EvidenceHashRecord[]>(`/api/evidence/${evidenceId}/hashes`, { signal }),
  custody: (evidenceId: string, signal?: AbortSignal) => apiClient.get<CustodyEntry[]>(`/api/evidence/${evidenceId}/coc`, { signal }),
  register: (caseId: string, payload: EvidenceRegistrationRequest) => apiClient.post<EvidenceRecord, FormData>(`/api/cases/${caseId}/evidence`, registrationForm(payload)),
  verify: (evidenceId: string) => apiClient.post<EvidenceVerification>(`/api/evidence/${evidenceId}/verify`),
}
