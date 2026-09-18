import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'
import { cn } from '../../utils'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  loading?: boolean
  leadingIcon?: ReactNode
}

const variants: Record<ButtonVariant, string> = {
  primary: 'border-accent-strong bg-accent-strong text-surface-canvas hover:bg-accent',
  secondary: 'border-border-strong bg-surface-raised text-text-primary hover:border-accent/60 hover:bg-surface-overlay',
  ghost: 'border-transparent bg-transparent text-text-secondary hover:bg-surface-raised hover:text-text-primary',
  danger: 'border-danger/40 bg-danger/10 text-danger hover:bg-danger/20',
}

export function Button({ className, variant = 'secondary', loading = false, leadingIcon, disabled, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn('inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-md border px-3 py-1.5 text-sm font-semibold transition-colors duration-fast disabled:cursor-not-allowed disabled:opacity-45', variants[variant], className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <LoaderCircle aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" /> : leadingIcon}
      {children}
    </button>
  )
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> { label: string; children: ReactNode }

export function IconButton({ label, className, children, ...props }: IconButtonProps) {
  return <button aria-label={label} title={label} className={cn('inline-flex size-10 cursor-pointer items-center justify-center rounded-md border border-transparent text-text-secondary transition-colors duration-fast hover:border-border-subtle hover:bg-surface-raised hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-45', className)} {...props}>{children}</button>
}
