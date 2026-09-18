import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { findingApi, type FindingListParameters } from '../api/findings'
import type { FindingUpdateRequest } from '../types'

export const findingQueryKeys = {
  all: ['findings'] as const,
  case: (caseId: string) => ['findings', 'case', caseId] as const,
  list: (caseId: string, parameters: FindingListParameters) => ['findings', 'case', caseId, 'list', parameters] as const,
  detail: (findingId: string) => ['findings', 'detail', findingId] as const,
}

export function useFindings(caseId: string, parameters: FindingListParameters) { return useQuery({ queryKey: findingQueryKeys.list(caseId, parameters), queryFn: ({ signal }) => findingApi.list(caseId, parameters, signal), enabled: Boolean(caseId), placeholderData: (previous) => previous }) }
export function useFinding(findingId: string) { return useQuery({ queryKey: findingQueryKeys.detail(findingId), queryFn: ({ signal }) => findingApi.get(findingId, signal), enabled: Boolean(findingId) }) }
export function useUpdateFinding(findingId: string, caseId: string) { const client = useQueryClient(); return useMutation({ mutationFn: (payload: FindingUpdateRequest) => findingApi.update(findingId, payload), onSuccess: async (finding) => { client.setQueryData(findingQueryKeys.detail(findingId), finding); await client.invalidateQueries({ queryKey: findingQueryKeys.case(caseId) }) } }) }
