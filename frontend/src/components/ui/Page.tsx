import type { ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export interface BreadcrumbItem { label: string; to?: string }
export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return <nav aria-label="Breadcrumb"><ol className="flex flex-wrap items-center gap-1 text-xs text-text-muted">{items.map((item, index) => <li key={`${item.label}-${index}`} className="flex items-center gap-1">{index > 0 && <ChevronRight aria-hidden="true" className="size-3" />}{item.to ? <Link className="rounded-sm hover:text-text-primary" to={item.to}>{item.label}</Link> : <span aria-current="page" className="text-text-secondary">{item.label}</span>}</li>)}</ol></nav>
}

export function PageHeader({ eyebrow, title, description, breadcrumbs, actions }: { eyebrow?: string; title: string; description?: string; breadcrumbs?: BreadcrumbItem[]; actions?: ReactNode }) {
  return <header className="border-b border-border-subtle pb-5">{breadcrumbs && <Breadcrumbs items={breadcrumbs} />}<div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div className="min-w-0">{eyebrow && <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-accent">{eyebrow}</p>}<h1 className="text-2xl font-semibold tracking-tight text-text-primary sm:text-3xl">{title}</h1>{description && <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">{description}</p>}</div>{actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}</div></header>
}
