import type { Config } from 'tailwindcss'

const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: { canvas: token('surface-canvas'), base: token('surface-base'), raised: token('surface-raised'), overlay: token('surface-overlay'), inset: token('surface-inset') },
        border: { subtle: token('border-subtle'), strong: token('border-strong') },
        text: { primary: token('text-primary'), secondary: token('text-secondary'), muted: token('text-muted') },
        accent: { DEFAULT: token('accent'), strong: token('accent-strong') },
        focus: token('focus'), success: token('success'), warning: token('warning'), danger: token('danger'), info: token('info'),
        severity: { info: token('severity-info'), low: token('severity-low'), medium: token('severity-medium'), high: token('severity-high'), critical: token('severity-critical') },
        confidence: { low: token('confidence-low'), medium: token('confidence-medium'), high: token('confidence-high') },
        status: { open: token('status-open'), closed: token('status-closed'), archived: token('status-archived') },
        integrity: { match: token('integrity-match'), mismatch: token('integrity-mismatch'), unknown: token('integrity-unknown') },
        parser: { running: token('parser-running'), warning: token('parser-warning'), failed: token('parser-failed'), complete: token('parser-complete') },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"Cascadia Code"', 'Consolas', 'ui-monospace', 'monospace'],
      },
      borderRadius: { sm: '3px', md: '5px', lg: '8px' },
      boxShadow: { panel: '0 12px 32px rgb(0 0 0 / 0.24)' },
      transitionDuration: { fast: '140ms', standard: '220ms', deliberate: '300ms' },
      zIndex: { sidebar: '30', overlay: '40', dialog: '50' },
    },
  },
  plugins: [],
} satisfies Config
