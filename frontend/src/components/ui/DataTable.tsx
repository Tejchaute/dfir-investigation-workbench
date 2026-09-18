import type { ReactNode } from 'react'
import { cn } from '../../utils'

export interface DataTableColumn<Row> { id: string; header: ReactNode; cell: (row: Row) => ReactNode; align?: 'left' | 'right'; className?: string }
export function DataTable<Row>({ columns, rows, getRowKey, caption, empty }: { columns: DataTableColumn<Row>[]; rows: Row[]; getRowKey: (row: Row) => string; caption: string; empty?: ReactNode }) {
  if (rows.length === 0 && empty) return <>{empty}</>
  return <div className="overflow-x-auto rounded-md border border-border-subtle bg-surface-base scrollbar-forensic"><table className="w-full min-w-[640px] border-collapse text-left text-sm"><caption className="sr-only">{caption}</caption><thead className="bg-surface-inset text-xs uppercase tracking-wide text-text-muted"><tr>{columns.map((column) => <th key={column.id} scope="col" className={cn('border-b border-border-subtle px-3 py-2.5 font-semibold', column.align === 'right' && 'text-right', column.className)}>{column.header}</th>)}</tr></thead><tbody className="divide-y divide-border-subtle">{rows.map((row) => <tr key={getRowKey(row)} className="transition-colors duration-fast hover:bg-surface-raised/55">{columns.map((column) => <td key={column.id} className={cn('px-3 py-3 align-top text-text-secondary', column.align === 'right' && 'text-right', column.className)}>{column.cell(row)}</td>)}</tr>)}</tbody></table></div>
}
