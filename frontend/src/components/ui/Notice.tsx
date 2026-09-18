import { CheckCircle2 } from 'lucide-react'
export function SuccessNotice({ message }: { message: string }) { return <div role="status" aria-live="polite" className="flex items-center gap-2 rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success"><CheckCircle2 aria-hidden="true" className="size-4" />{message}</div> }
