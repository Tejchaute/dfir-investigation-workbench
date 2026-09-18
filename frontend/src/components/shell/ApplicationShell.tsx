import { useState } from 'react'
import { Outlet, useParams } from 'react-router-dom'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { useCase } from '../../hooks'

export function ApplicationShell() {
  const { caseId } = useParams()
  const caseQuery = useCase(caseId)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const reduceMotion = useReducedMotion()
  return <div className="flex min-h-dvh bg-surface-canvas"><a href="#main-content" className="fixed left-3 top-3 z-[100] -translate-y-20 rounded-md bg-accent-strong px-3 py-2 font-semibold text-surface-canvas focus:translate-y-0">Skip to main content</a><div className="sticky top-0 hidden h-dvh shrink-0 lg:block"><Sidebar caseId={caseId} collapsed={collapsed} onCollapsedChange={setCollapsed} /></div><DialogPrimitive.Root open={mobileOpen} onOpenChange={setMobileOpen}><AnimatePresence>{mobileOpen && <DialogPrimitive.Portal forceMount><DialogPrimitive.Overlay asChild><motion.div className="fixed inset-0 z-overlay bg-surface-canvas/80 lg:hidden" initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} /></DialogPrimitive.Overlay><DialogPrimitive.Content asChild><motion.div aria-label="Mobile navigation" className="fixed inset-y-0 left-0 z-dialog w-60 lg:hidden" initial={reduceMotion ? false : { x: -240 }} animate={{ x: 0 }} exit={{ x: -240 }} transition={{ duration: reduceMotion ? 0 : 0.22 }}><DialogPrimitive.Title className="sr-only">Investigation navigation</DialogPrimitive.Title><DialogPrimitive.Description className="sr-only">Navigate case and analysis workspaces.</DialogPrimitive.Description><Sidebar caseId={caseId} collapsed={false} onCollapsedChange={() => undefined} onNavigate={() => setMobileOpen(false)} /></motion.div></DialogPrimitive.Content></DialogPrimitive.Portal>}</AnimatePresence></DialogPrimitive.Root><div className="min-w-0 flex-1"><Topbar caseId={caseId} currentCase={caseQuery.data} onOpenNavigation={() => setMobileOpen(true)} /><main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[1600px] px-4 py-5 sm:px-6 sm:py-6 lg:px-8"><Outlet /></main></div></div>
}
