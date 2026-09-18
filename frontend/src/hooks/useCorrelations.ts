import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { correlationApi, type CorrelationListParameters } from '../api/correlation'

export const correlationQueryKeys = { all: ['correlations'] as const, case: (caseId: string) => ['correlations', 'case', caseId] as const, list: (caseId: string, p: CorrelationListParameters) => ['correlations', 'case', caseId, 'list', p] as const }
export function useCorrelations(caseId: string, parameters: CorrelationListParameters) { return useQuery({ queryKey: correlationQueryKeys.list(caseId, parameters), queryFn: ({ signal }) => correlationApi.list(caseId, parameters, signal), enabled: Boolean(caseId), placeholderData: (previous) => previous }) }
export function useRunCorrelation(caseId: string) { const client = useQueryClient(); return useMutation({ mutationFn: () => correlationApi.run(caseId), onSuccess: async () => { await client.invalidateQueries({ queryKey: correlationQueryKeys.case(caseId) }) } }) }
