import { useMemo, useState } from 'react'
import { Braces, Check, Copy, ListTree } from 'lucide-react'
import { Button, MonospaceValue } from '..'

export function StructuredDataViewer({ value, label = 'Structured record data' }: { value: unknown; label?: string }) {
  const [mode, setMode] = useState<'structured' | 'raw'>('structured')
  const [copied, setCopied] = useState(false)
  const raw = useMemo(() => JSON.stringify(value, null, 2), [value])
  async function copy() { await navigator.clipboard.writeText(raw ?? 'null'); setCopied(true); window.setTimeout(() => setCopied(false), 1500) }
  return <div className="min-w-0 rounded-md border border-border-subtle bg-surface-inset"><div className="flex flex-col gap-2 border-b border-border-subtle p-2 sm:flex-row sm:items-center sm:justify-between"><div role="tablist" aria-label={`${label} view`} className="flex gap-1"><Button role="tab" aria-selected={mode === 'structured'} variant={mode === 'structured' ? 'secondary' : 'ghost'} leadingIcon={<ListTree aria-hidden="true" className="size-4" />} onClick={() => setMode('structured')}>Structured</Button><Button role="tab" aria-selected={mode === 'raw'} variant={mode === 'raw' ? 'secondary' : 'ghost'} leadingIcon={<Braces aria-hidden="true" className="size-4" />} onClick={() => setMode('raw')}>Raw JSON</Button></div>{mode === 'raw' && <Button variant="ghost" leadingIcon={copied ? <Check aria-hidden="true" className="size-4 text-success" /> : <Copy aria-hidden="true" className="size-4" />} onClick={() => void copy()}>{copied ? 'Copied' : 'Copy JSON'}</Button>}</div><div role="tabpanel" className="min-w-0 p-3 sm:p-4">{mode === 'structured' ? <StructuredValue value={value} depth={0} /> : <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-text-secondary scrollbar-forensic">{raw ?? 'null'}</pre>}</div>{copied && <span className="sr-only" role="status">Raw JSON copied</span>}</div>
}

function StructuredValue({ value, depth }: { value: unknown; depth: number }): React.ReactNode {
  if (value === null) return <span className="italic text-text-muted">null</span>
  if (Array.isArray(value)) {
    if (!value.length) return <span className="text-text-muted">Empty array</span>
    return <div className="space-y-2">{value.map((item, index) => <details key={index} open={depth < 1} className="group rounded-sm border border-border-subtle bg-surface-base"><summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-text-secondary focus-visible:ring-inset">Item {index + 1}</summary><div className="border-t border-border-subtle p-3"><StructuredValue value={item} depth={depth + 1} /></div></details>)}</div>
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (!entries.length) return <span className="text-text-muted">Empty object</span>
    return <dl className="divide-y divide-border-subtle">{entries.map(([key, item]) => <div key={key} className="grid min-w-0 gap-1 py-2 first:pt-0 last:pb-0 sm:grid-cols-[minmax(8rem,0.35fr)_minmax(0,1fr)] sm:gap-4"><dt className="font-mono text-xs font-semibold text-text-muted">{key}</dt><dd className="min-w-0 text-sm text-text-secondary">{typeof item === 'object' && item !== null ? <details open={depth < 1}><summary className="cursor-pointer text-xs font-semibold text-accent">{Array.isArray(item) ? `Array · ${item.length}` : `Object · ${Object.keys(item as object).length} fields`}</summary><div className="mt-2 border-l border-border-strong pl-3"><StructuredValue value={item} depth={depth + 1} /></div></details> : <Primitive value={item} />}</dd></div>)}</dl>
  }
  return <Primitive value={value} />
}

function Primitive({ value }: { value: unknown }) {
  if (typeof value === 'string') return <MonospaceValue className="block whitespace-pre-wrap break-words text-xs leading-5">{value}</MonospaceValue>
  if (typeof value === 'boolean') return <span className="font-mono text-xs text-text-primary">{String(value)}</span>
  if (typeof value === 'number') return <span className="font-mono text-xs tabular-nums text-text-primary">{value}</span>
  return <span className="font-mono text-xs text-text-muted">{String(value)}</span>
}
