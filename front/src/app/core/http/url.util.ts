export function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

export function resolveWsUrl(base: string): string {
  if (base.startsWith('/')) {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}${base}`;
  }
  if (base.startsWith('http')) {
    return base.replace(/^http/, 'ws');
  }
  return base;
}
