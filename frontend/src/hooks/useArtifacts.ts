import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { artifactApi, type ArtifactListParameters, type ArtifactRecordListParameters } from '../api/artifacts'
import type { ParseEvidenceRequest } from '../types'

export const artifactQueryKeys = {
  all: ['artifacts'] as const,
  evidenceLists: () => [...artifactQueryKeys.all, 'evidence-list'] as const,
  evidenceList: (evidenceId: string, parameters: ArtifactListParameters) => [...artifactQueryKeys.evidenceLists(), evidenceId, parameters] as const,
  details: () => [...artifactQueryKeys.all, 'detail'] as const,
  detail: (artifactId: string) => [...artifactQueryKeys.details(), artifactId] as const,
  recordLists: (artifactId: string) => [...artifactQueryKeys.detail(artifactId), 'records'] as const,
  records: (artifactId: string, parameters: ArtifactRecordListParameters) => [...artifactQueryKeys.recordLists(artifactId), parameters] as const,
}

export function useEvidenceArtifacts(evidenceId: string, parameters: ArtifactListParameters) {
  return useQuery({ queryKey: artifactQueryKeys.evidenceList(evidenceId, parameters), queryFn: ({ signal }) => artifactApi.listForEvidence(evidenceId, parameters, signal), enabled: Boolean(evidenceId), placeholderData: (previous) => previous })
}
export function useArtifact(artifactId: string) {
  return useQuery({ queryKey: artifactQueryKeys.detail(artifactId), queryFn: ({ signal }) => artifactApi.get(artifactId, signal), enabled: Boolean(artifactId) })
}
export function useArtifactRecords(artifactId: string, parameters: ArtifactRecordListParameters) {
  return useQuery({ queryKey: artifactQueryKeys.records(artifactId, parameters), queryFn: ({ signal }) => artifactApi.records(artifactId, parameters, signal), enabled: Boolean(artifactId), placeholderData: (previous) => previous })
}
export function useParseEvidence(evidenceId: string) {
  const queryClient = useQueryClient()
  return useMutation({ mutationFn: (payload: ParseEvidenceRequest) => artifactApi.parse(evidenceId, payload), onSuccess: async (artifact) => {
    queryClient.setQueryData(artifactQueryKeys.detail(artifact.id), artifact)
    await queryClient.invalidateQueries({ queryKey: artifactQueryKeys.evidenceLists() })
  } })
}
