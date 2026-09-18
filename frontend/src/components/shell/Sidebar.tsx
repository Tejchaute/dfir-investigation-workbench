import { NavLink } from 'react-router-dom'
import { ChevronsLeft, ChevronsRight, FlaskConical } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { cn } from '../../utils'
import { IconButton } from '../ui/Button'
import { caseNavigation, rootNavigation } from './navigation'

export function Sidebar({ caseId, collapsed, onCollapsedChange, onNavigate, className }: { caseId?: string; collapsed: boolean; onCollapsedChange: (value: boolean) => void; onNavigate?: () => void; className?: string }) {
  const reduceMotion = useReducedMotion()
  return <motion.aside aria-label="Investigation navigation" className={cn('flex h-full flex-col border-r border-border-subtle bg-surface-base', className)} animate={{ width: collapsed ? 72 : 240 }} transition={{ duration: reduceMotion ? 0 : 0.22, ease: [0.22, 1, 0.36, 1] }}>
    <div className="flex h-16 items-center gap-3 border-b border-border-subtle px-4"><span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-accent/30 bg-accent/10 text-accent"><FlaskConical aria-hidden="true" className="size-5" /></span>{!collapsed && <div className="min-w-0"><p className="truncate text-xs font-bold tracking-[0.14em] text-text-primary">DFIR WORKBENCH</p><p className="truncate text-[11px] text-text-muted">Forensic Operations</p></div>}</div>
    <nav className="scrollbar-forensic flex-1 overflow-y-auto px-2 py-4"><ul className="space-y-1">{rootNavigation.slice(0, 1).map((item) => <NavItem key={item.path} {...item} collapsed={collapsed} onNavigate={onNavigate} />)}</ul>{caseNavigation.map((group) => <div key={group.label} className="mt-5"><p className={cn('mb-2 px-2 text-[10px] font-bold uppercase tracking-[0.18em] text-text-muted', collapsed && 'sr-only')}>{group.label}</p><ul className="space-y-1">{group.items.map((item) => <NavItem key={item.segment} label={item.label} path={caseId ? `/cases/${caseId}/${item.segment}` : '/cases'} icon={item.icon} collapsed={collapsed} disabled={!caseId} onNavigate={onNavigate} />)}</ul></div>)}</nav>
    <div className="border-t border-border-subtle p-2"><NavItem {...rootNavigation[1]} collapsed={collapsed} onNavigate={onNavigate} /><div className="mt-2 hidden justify-end lg:flex"><IconButton label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => onCollapsedChange(!collapsed)}>{collapsed ? <ChevronsRight aria-hidden="true" className="size-4" /> : <ChevronsLeft aria-hidden="true" className="size-4" />}</IconButton></div></div>
  </motion.aside>
}

function NavItem({ label, path, icon: Icon, collapsed, disabled, onNavigate }: { label: string; path: string; icon: typeof FlaskConical; collapsed: boolean; disabled?: boolean; onNavigate?: () => void }) {
  return <li><NavLink to={path} onClick={onNavigate} title={collapsed ? label : undefined} aria-disabled={disabled || undefined} className={({ isActive }) => cn('flex min-h-10 items-center gap-3 rounded-md border border-transparent px-3 text-sm font-medium text-text-secondary transition-colors duration-fast hover:bg-surface-raised hover:text-text-primary', isActive && 'border-accent/25 bg-accent/10 text-accent', disabled && 'pointer-events-none opacity-40', collapsed && 'justify-center px-0')}><Icon aria-hidden="true" className="size-[18px] shrink-0" />{!collapsed && <span>{label}</span>}</NavLink></li>
}
