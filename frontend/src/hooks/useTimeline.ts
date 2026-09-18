import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { timelineApi, type TimelineListParameters } from '../api/timeline'

export const timelineQueryKeys = { all: ['timeline'] as const, case: (caseId: string) => ['timeline', 'case', caseId] as const, list: (caseId: string, p: TimelineListParameters) => ['timeline', 'case', caseId, 'list', p] as const }
export function useTimeline(caseId: string, parameters: TimelineListParameters) { return useQuery({ queryKey: timelineQueryKeys.list(caseId, parameters), queryFn: ({ signal }) => timelineApi.list(caseId, parameters, signal), enabled: Boolean(caseId), placeholderData: (previous) => previous }) }
export function useGenerateTimeline(caseId: string) { const client = useQueryClient(); return useMutation({ mutationFn: () => timelineApi.generate(caseId), onSuccess: async () => { await client.invalidateQueries({ queryKey: timelineQueryKeys.case(caseId) }) } }) }
