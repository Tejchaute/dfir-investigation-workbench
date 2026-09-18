import { useEffect, useRef, type ReactNode } from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { X } from 'lucide-react'
import { IconButton } from './Button'
import { cn } from '../../utils'

interface OverlayProps { open: boolean; onOpenChange: (open: boolean) => void; title: string; description?: string; children: ReactNode }
function OverlayContent({ open, onOpenChange, title, description, children, drawer }: OverlayProps & { drawer?: boolean }) {
  const reduceMotion = useReducedMotion()
  const returnFocusRef = useRef<HTMLElement | null>(null)
  useEffect(() => {
    if (open && document.activeElement instanceof HTMLElement) returnFocusRef.current = document.activeElement
  }, [open])
  return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}><AnimatePresence>{open && <DialogPrimitive.Portal forceMount><DialogPrimitive.Overlay asChild><motion.div className="fixed inset-0 z-overlay bg-surface-canvas/80 backdrop-blur-[2px]" initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.16 }} /></DialogPrimitive.Overlay><DialogPrimitive.Content asChild onCloseAutoFocus={(event) => { event.preventDefault(); returnFocusRef.current?.focus() }}><motion.section className={cn('fixed z-dialog border border-border-strong bg-surface-overlay shadow-panel', drawer ? 'inset-y-0 right-0 w-full max-w-xl overflow-y-auto scrollbar-forensic sm:w-[min(88vw,36rem)]' : 'left-1/2 top-1/2 w-[min(92vw,34rem)] rounded-lg')} initial={reduceMotion ? false : drawer ? { opacity: 0, x: 24 } : { opacity: 0, x: '-50%', y: '-48%' }} animate={drawer ? { opacity: 1, x: 0 } : { opacity: 1, x: '-50%', y: '-50%' }} exit={drawer ? { opacity: 0, x: 16 } : { opacity: 0, x: '-50%', y: '-48%' }} transition={{ duration: reduceMotion ? 0 : 0.22, ease: [0.22, 1, 0.36, 1] }}><header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-border-subtle bg-surface-overlay px-5 py-4"><div><DialogPrimitive.Title className="text-base font-semibold text-text-primary">{title}</DialogPrimitive.Title>{description && <DialogPrimitive.Description className="mt-1 text-sm text-text-secondary">{description}</DialogPrimitive.Description>}</div><DialogPrimitive.Close asChild><IconButton label="Close"><X aria-hidden="true" className="size-4" /></IconButton></DialogPrimitive.Close></header><div className="p-5">{children}</div></motion.section></DialogPrimitive.Content></DialogPrimitive.Portal>}</AnimatePresence></DialogPrimitive.Root>
}
export function Dialog(props: OverlayProps) { return <OverlayContent {...props} /> }
export function DetailDrawer(props: OverlayProps) { return <OverlayContent {...props} drawer /> }
