import type { DownloadedFile } from './client'
import type { ReportCreateRequest, ReportListResponse, ReportRecord } from '../types'
import { apiClient } from './client'

export interface ReportListParameters { limit: number; offset: number }

export const reportApi = {
  list: (caseId: string, parameters: ReportListParameters, signal?: AbortSignal) => apiClient.get<ReportListResponse>(`/api/cases/${caseId}/reports`, { query: { limit: parameters.limit, offset: parameters.offset }, signal }),
  get: (reportId: string, signal?: AbortSignal) => apiClient.get<ReportRecord>(`/api/reports/${reportId}`, { signal }),
  create: (caseId: string, payload: ReportCreateRequest) => apiClient.post<ReportRecord, ReportCreateRequest>(`/api/cases/${caseId}/reports`, payload),
  download: (reportId: string, signal?: AbortSignal): Promise<DownloadedFile> => apiClient.download(`/api/reports/${reportId}/download`, { signal }),
}
