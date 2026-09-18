import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { evidenceApi, type EvidenceListParameters } from '../api/evidence'
import type { EvidenceRegistrationRequest } from '../types'

export const evidenceQueryKeys = {
  all: ['evidence'] as const,
  lists: () => [...evidenceQueryKeys.all, 'list'] as const,
  caseLists: (caseId: string) => [...evidenceQueryKeys.lists(), caseId] as const,
  list: (caseId: string, parameters: EvidenceListParameters) => [...evidenceQueryKeys.caseLists(caseId), parameters] as const,
  details: () => [...evidenceQueryKeys.all, 'detail'] as const,
  detail: (evidenceId: string) => [...evidenceQueryKeys.details(), evidenceId] as const,
  hashes: (evidenceId: string) => [...evidenceQueryKeys.detail(evidenceId), 'hashes'] as const,
  custody: (evidenceId: string) => [...evidenceQueryKeys.detail(evidenceId), 'custody'] as const,
}

export function useCaseEvidence(caseId: string, parameters: EvidenceListParameters) {
  return useQuery({ queryKey: evidenceQueryKeys.list(caseId, parameters), queryFn: ({ signal }) => evidenceApi.list(caseId, parameters, signal), enabled: Boolean(caseId), placeholderData: (previous) => previous })
}
export function useEvidence(evidenceId: string) {
  return useQuery({ queryKey: evidenceQueryKeys.detail(evidenceId), queryFn: ({ signal }) => evidenceApi.get(evidenceId, signal), enabled: Boolean(evidenceId) })
}
export function useEvidenceHashes(evidenceId: string) {
  return useQuery({ queryKey: evidenceQueryKeys.hashes(evidenceId), queryFn: ({ signal }) => evidenceApi.hashes(evidenceId, signal), enabled: Boolean(evidenceId) })
}
export function useEvidenceCustody(evidenceId: string) {
  return useQuery({ queryKey: evidenceQueryKeys.custody(evidenceId), queryFn: ({ signal }) => evidenceApi.custody(evidenceId, signal), enabled: Boolean(evidenceId) })
}
export function useRegisterEvidence(caseId: string) {
  const queryClient = useQueryClient()
  return useMutation({ mutationFn: (payload: EvidenceRegistrationRequest) => evidenceApi.register(caseId, payload), onSuccess: async (created) => {
    queryClient.setQueryData(evidenceQueryKeys.detail(created.id), created)
    await queryClient.invalidateQueries({ queryKey: evidenceQueryKeys.caseLists(caseId) })
  } })
}
export function useVerifyEvidence(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({ mutationFn: () => evidenceApi.verify(evidenceId), onSuccess: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: evidenceQueryKeys.detail(evidenceId) }),
      queryClient.invalidateQueries({ queryKey: evidenceQueryKeys.hashes(evidenceId) }),
      queryClient.invalidateQueries({ queryKey: evidenceQueryKeys.custody(evidenceId) }),
    ])
  } })
}
