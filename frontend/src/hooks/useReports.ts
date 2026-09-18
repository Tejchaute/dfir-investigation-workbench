import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { reportApi, type ReportListParameters } from '../api/reports'
import type { ReportCreateRequest } from '../types'

export const reportQueryKeys = {
  all: ['reports'] as const,
  case: (caseId: string) => ['reports', 'case', caseId] as const,
  list: (caseId: string, parameters: ReportListParameters) => ['reports', 'case', caseId, 'list', parameters] as const,
  detail: (reportId: string) => ['reports', 'detail', reportId] as const,
}

export function useReports(caseId: string, parameters: ReportListParameters) { return useQuery({ queryKey: reportQueryKeys.list(caseId, parameters), queryFn: ({ signal }) => reportApi.list(caseId, parameters, signal), enabled: Boolean(caseId), placeholderData: (previous) => previous }) }
export function useReport(reportId: string) { return useQuery({ queryKey: reportQueryKeys.detail(reportId), queryFn: ({ signal }) => reportApi.get(reportId, signal), enabled: Boolean(reportId) }) }
export function useCreateReport(caseId: string) { const client = useQueryClient(); return useMutation({ mutationFn: (payload: ReportCreateRequest) => reportApi.create(caseId, payload), onSuccess: async (report) => { client.setQueryData(reportQueryKeys.detail(report.id), report); await client.invalidateQueries({ queryKey: reportQueryKeys.case(caseId) }) } }) }
export function useDownloadReport(reportId: string) { return useMutation({ mutationFn: () => reportApi.download(reportId) }) }
