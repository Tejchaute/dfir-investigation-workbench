import type { ReactNode } from 'react'
import { AlertTriangle, CircleOff, Database, LoaderCircle, SearchX } from 'lucide-react'
import { Button } from './Button'

interface StateProps { title: string; description: string; action?: ReactNode }
function StateFrame({ icon, title, description, action }: StateProps & { icon: ReactNode }) {
  return <section className="flex min-h-60 flex-col items-center justify-center rounded-lg border border-dashed border-border-strong bg-surface-base px-6 py-10 text-center"><div className="mb-4 flex size-10 items-center justify-center rounded-md border border-border-subtle bg-surface-raised text-text-secondary">{icon}</div><h2 className="text-base font-semibold text-text-primary">{title}</h2><p className="mt-2 max-w-lg text-sm leading-6 text-text-secondary">{description}</p>{action && <div className="mt-5">{action}</div>}</section>
}
export function EmptyState({ title = 'No records available', description = 'No records match the current context.', action }: Partial<StateProps>) { return <StateFrame icon={<Database aria-hidden="true" className="size-5" />} title={title} description={description} action={action} /> }
export function UnsupportedState({ title = 'Capability unavailable', description = 'The backend does not currently expose this capability.' }: Partial<StateProps>) { return <StateFrame icon={<CircleOff aria-hidden="true" className="size-5" />} title={title} description={description} /> }
export function NotFoundState({ title = 'Record not found', description = 'The requested resource does not exist or is no longer available.', action }: Partial<StateProps>) { return <StateFrame icon={<SearchX aria-hidden="true" className="size-5" />} title={title} description={description} action={action} /> }
export function ErrorState({ title = 'Unable to load data', description = 'The request could not be completed.', onRetry }: Partial<StateProps> & { onRetry?: () => void }) { return <StateFrame icon={<AlertTriangle aria-hidden="true" className="size-5 text-danger" />} title={title} description={description} action={onRetry ? <Button onClick={onRetry}>Try again</Button> : undefined} /> }
export function LoadingState({ label = 'Loading investigation data' }: { label?: string }) { return <div role="status" className="flex min-h-60 items-center justify-center gap-3 text-sm text-text-secondary"><LoaderCircle aria-hidden="true" className="size-5 animate-spin text-accent motion-reduce:animate-none" />{label}</div> }
export function Skeleton({ className = '' }: { className?: string }) { return <span aria-hidden="true" className={`block animate-pulse rounded-sm bg-surface-overlay motion-reduce:animate-none ${className}`} /> }
