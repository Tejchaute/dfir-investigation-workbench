const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type QueryValue = string | number | boolean | Date | null | undefined
export type QueryParameters = Record<string, QueryValue | QueryValue[]>
export interface ApiValidationIssue { loc?: Array<string | number>; msg?: string; type?: string }
export interface ApiErrorDetail { code?: string; message?: string }
export interface ApiErrorPayload { detail?: string | ApiErrorDetail | ApiValidationIssue[]; message?: string; [key: string]: unknown }

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly payload?: ApiErrorPayload) { super(message); this.name = 'ApiError' }
}

export interface RequestOptions { query?: QueryParameters; signal?: AbortSignal; headers?: HeadersInit }
export interface DownloadedFile { blob: Blob; filename: string | null; contentType: string }

function serializeQuery(url: URL, query?: QueryParameters): void {
  if (!query) return
  for (const [key, rawValue] of Object.entries(query)) {
    for (const value of Array.isArray(rawValue) ? rawValue : [rawValue]) {
      if (value === null || value === undefined) continue
      url.searchParams.append(key, value instanceof Date ? value.toISOString() : String(value))
    }
  }
}

async function normalizeError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload | undefined
  try { payload = (await response.json()) as ApiErrorPayload } catch { payload = undefined }
  const detail = typeof payload?.detail === 'string'
    ? payload.detail
    : Array.isArray(payload?.detail)
      ? payload.detail.map((issue) => issue.msg).filter(Boolean).join('; ')
      : payload?.detail?.message ?? payload?.message
  return new ApiError(detail ?? `API request failed with status ${response.status}`, response.status, payload)
}

async function request<T>(method: 'GET' | 'POST' | 'PATCH', path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
  const url = new URL(path, apiBaseUrl)
  serializeQuery(url, options.query)
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  const isFormData = body instanceof FormData
  if (body !== undefined && !isFormData) headers.set('Content-Type', 'application/json')
  const response = await fetch(url, { method, headers, signal: options.signal, body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body) })
  if (!response.ok) throw await normalizeError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

async function download(path: string, options: RequestOptions = {}): Promise<DownloadedFile> {
  const url = new URL(path, apiBaseUrl)
  serializeQuery(url, options.query)
  const response = await fetch(url, { method: 'GET', headers: options.headers, signal: options.signal })
  if (!response.ok) throw await normalizeError(response)
  const disposition = response.headers.get('content-disposition')
  const encoded = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  const quoted = disposition?.match(/filename="([^"]+)"/i)?.[1]
  return { blob: await response.blob(), filename: encoded ? decodeURIComponent(encoded) : quoted ?? null, contentType: response.headers.get('content-type') ?? 'application/octet-stream' }
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>('GET', path, undefined, options),
  post: <TResponse, TBody = unknown>(path: string, body?: TBody, options?: RequestOptions) => request<TResponse>('POST', path, body, options),
  patch: <TResponse, TBody = unknown>(path: string, body: TBody, options?: RequestOptions) => request<TResponse>('PATCH', path, body, options),
  download,
}

export { apiBaseUrl }
