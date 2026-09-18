export function formatBytes(value: number | null): string {
  if (value === null) return 'Unavailable'
  if (value === 0) return '0 B'
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
  const exponent = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** exponent).toLocaleString(undefined, { maximumFractionDigits: exponent === 0 ? 0 : 2 })} ${units[exponent]}`
}
