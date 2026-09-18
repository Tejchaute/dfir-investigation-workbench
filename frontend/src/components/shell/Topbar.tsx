import { Menu, Server } from 'lucide-react'
import { Link } from 'react-router-dom'
import { IconButton } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { MonospaceValue } from '../ui/ForensicValue'
import type { CaseRecord } from '../../types'

export function Topbar({ caseId, currentCase, onOpenNavigation }: { caseId?: string; currentCase?: CaseRecord; onOpenNavigation: () => void }) {
  return <header className="flex h-16 items-center justify-between gap-4 border-b border-border-subtle bg-surface-base/95 px-4 backdrop-blur sm:px-6"><div className="flex min-w-0 items-center gap-3"><div className="lg:hidden"><IconButton label="Open navigation" onClick={onOpenNavigation}><Menu aria-hidden="true" className="size-5" /></IconButton></div><div className="min-w-0"><Link to="/cases" className="text-xs font-bold tracking-[0.14em] text-text-primary lg:hidden">DFIR WORKBENCH</Link>{caseId ? <div className="flex min-w-0 items-baseline gap-2"><span className="hidden text-xs uppercase tracking-wide text-text-muted sm:inline">Case context</span><MonospaceValue className="truncate text-xs" title={currentCase ? `${currentCase.case_number} — ${currentCase.name}` : caseId}>{currentCase?.case_number ?? caseId}</MonospaceValue>{currentCase && <span className="hidden truncate text-xs text-text-secondary md:inline">{currentCase.name}</span>}</div> : <p className="text-sm text-text-secondary">Investigation workspace</p>}</div></div><Badge className="shrink-0 border-success/25 text-success"><Server aria-hidden="true" className="size-3" />API configured</Badge></header>
}
