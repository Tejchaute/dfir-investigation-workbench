import type { LucideIcon } from 'lucide-react'
import { Activity, Boxes, FileOutput, FileSearch, Fingerprint, FolderKanban, LayoutDashboard, ScrollText, Settings, ShieldCheck } from 'lucide-react'

export interface NavigationItem { label: string; segment: string; icon: LucideIcon }
export interface NavigationGroup { label: string; items: NavigationItem[] }

export const caseNavigation: NavigationGroup[] = [
  { label: 'Case', items: [
    { label: 'Overview', segment: 'overview', icon: LayoutDashboard },
    { label: 'Evidence', segment: 'evidence', icon: Fingerprint },
    { label: 'Artifacts', segment: 'artifacts', icon: Boxes },
  ] },
  { label: 'Analysis', items: [
    { label: 'Timeline', segment: 'timeline', icon: Activity },
    { label: 'Correlations', segment: 'correlations', icon: FileSearch },
    { label: 'Findings', segment: 'findings', icon: ShieldCheck },
  ] },
  { label: 'Output', items: [
    { label: 'Reports', segment: 'reports', icon: FileOutput },
    { label: 'Audit', segment: 'audit', icon: ScrollText },
  ] },
]

export const rootNavigation = [
  { label: 'Cases', path: '/cases', icon: FolderKanban },
  { label: 'Settings', path: '/settings', icon: Settings },
]
