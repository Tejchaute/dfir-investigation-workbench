import { ApiError } from '../api'

export function getErrorMessage(error: unknown, fallback = 'The request could not be completed.'): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof TypeError) return 'Unable to reach the API. Check the backend connection and try again.'
  return fallback
}
