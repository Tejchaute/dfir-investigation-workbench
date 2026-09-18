import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { MonospaceValue } from './ForensicValue'

export interface ProvenanceNode { label: string; id: string; to?: string }
export function ProvenanceChain({ nodes }: { nodes: ProvenanceNode[] }) {
  return <nav aria-label="Forensic provenance"><ol className="flex flex-col gap-2 lg:flex-row lg:flex-wrap lg:items-center">{nodes.map((node, index) => <li key={`${node.label}-${node.id}`} className="flex min-w-0 items-center gap-2">{node.to ? <Link to={node.to} className="min-w-0 rounded-md border border-border-subtle bg-surface-inset px-3 py-2 hover:border-accent/50"><Node node={node} /></Link> : <div className="min-w-0 rounded-md border border-border-subtle bg-surface-inset px-3 py-2"><Node node={node} /></div>}{index < nodes.length - 1 && <ChevronRight aria-hidden="true" className="hidden size-4 shrink-0 text-text-muted lg:block" />}</li>)}</ol></nav>
}
function Node({ node }: { node: ProvenanceNode }) { return <><span className="block text-[11px] font-semibold uppercase tracking-wide text-text-muted">{node.label}</span><MonospaceValue className="block truncate text-xs" title={node.id}>{node.id}</MonospaceValue></> }
