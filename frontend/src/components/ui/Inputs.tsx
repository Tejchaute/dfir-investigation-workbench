import type { InputHTMLAttributes, ReactNode } from 'react'
import { Search } from 'lucide-react'
import { cn } from '../../utils'

export function SearchInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <label className={cn('relative block min-w-0', className)}><span className="sr-only">Search</span><Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-muted" /><input type="search" className="h-9 w-full rounded-md border border-border-subtle bg-surface-inset py-1.5 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted hover:border-border-strong focus:border-accent" placeholder="Search records" {...props} /></label>
}

export function FilterBar({ children }: { children: ReactNode }) { return <div role="search" aria-label="Filters" className="flex flex-col gap-2 rounded-md border border-border-subtle bg-surface-base p-3 sm:flex-row sm:flex-wrap sm:items-center">{children}</div> }
