import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { caseApi, type CaseListParameters } from '../api/cases'
import type { CaseCreateRequest, CaseUpdateRequest } from '../types'

export const caseQueryKeys = {
  all: ['cases'] as const,
  lists: () => [...caseQueryKeys.all, 'list'] as const,
  list: (parameters: CaseListParameters) => [...caseQueryKeys.lists(), parameters] as const,
  details: () => [...caseQueryKeys.all, 'detail'] as const,
  detail: (caseId: string) => [...caseQueryKeys.details(), caseId] as const,
}

export function useCases(parameters: CaseListParameters) {
  return useQuery({ queryKey: caseQueryKeys.list(parameters), queryFn: ({ signal }) => caseApi.list(parameters, signal), placeholderData: (previous) => previous })
}

export function useCase(caseId?: string) {
  return useQuery({ queryKey: caseQueryKeys.detail(caseId ?? ''), queryFn: ({ signal }) => caseApi.get(caseId!, signal), enabled: Boolean(caseId) })
}

function useCaseInvalidation() {
  const queryClient = useQueryClient()
  return async (caseId: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: caseQueryKeys.lists() }),
      queryClient.invalidateQueries({ queryKey: caseQueryKeys.detail(caseId) }),
    ])
  }
}

export function useCreateCase() {
  const queryClient = useQueryClient()
  return useMutation({ mutationFn: (payload: CaseCreateRequest) => caseApi.create(payload), onSuccess: async (created) => {
    queryClient.setQueryData(caseQueryKeys.detail(created.id), created)
    await queryClient.invalidateQueries({ queryKey: caseQueryKeys.lists() })
  } })
}

export function useUpdateCase(caseId: string) {
  const invalidate = useCaseInvalidation()
  return useMutation({ mutationFn: (payload: CaseUpdateRequest) => caseApi.update(caseId, payload), onSuccess: () => invalidate(caseId) })
}

export function useCloseCase(caseId: string) {
  const invalidate = useCaseInvalidation()
  return useMutation({ mutationFn: () => caseApi.close(caseId), onSuccess: () => invalidate(caseId) })
}

export function useArchiveCase(caseId: string) {
  const invalidate = useCaseInvalidation()
  return useMutation({ mutationFn: () => caseApi.archive(caseId), onSuccess: () => invalidate(caseId) })
}
