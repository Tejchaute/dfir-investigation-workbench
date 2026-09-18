import { Skeleton } from '../ui/States'

export function CaseListSkeleton() {
  return <div aria-label="Loading cases" role="status" className="overflow-hidden rounded-md border border-border-subtle bg-surface-base"><div className="grid grid-cols-[1.1fr_2fr_0.8fr_1fr_1fr] gap-3 border-b border-border-subtle bg-surface-inset px-3 py-3">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="h-3 w-20" />)}</div>{Array.from({ length: 6 }, (_, index) => <div key={index} className="grid grid-cols-[1.1fr_2fr_0.8fr_1fr_1fr] gap-3 border-b border-border-subtle px-3 py-4 last:border-0"><Skeleton className="h-4 w-32" /><Skeleton className="h-4 w-44" /><Skeleton className="h-5 w-16" /><Skeleton className="h-4 w-28" /><Skeleton className="h-4 w-28" /></div>)}</div>
}
