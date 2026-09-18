import { Badge } from '..'

export function ArtifactTypeBadge({ type }: { type: string }) {
  return <Badge aria-label={`Artifact type ${type}`}>{type.replaceAll('_', ' ')}</Badge>
}
