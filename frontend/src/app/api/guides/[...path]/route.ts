import { NextRequest } from 'next/server';

const DIAGRAMS_BASE = 'https://motorthings.github.io/diagrams';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const url = `${DIAGRAMS_BASE}/${path.join('/')}`;

  let html: string;
  try {
    const resp = await fetch(url, { cache: 'no-store' });
    if (!resp.ok) return new Response('Guide not found', { status: 404 });
    html = await resp.text();
  } catch {
    return new Response('Guide not found', { status: 404 });
  }

  // Nothing should lead back to the diagrams repo. Open every link in the app's top
  // frame and rewrite internal <a> links to the app's guides page (external links
  // like LinkedIn / Google Fonts are left alone).
  html = html.replace(/<head>/i, '<head><base target="_top">');
  html = html.replace(/<a ([^>]*)href="([^"]*)"([^>]*)>/g, (_m, pre, href, post) => {
    if (href.startsWith('https://') && !href.includes('motorthings.github.io')) {
      return `<a ${pre}href="${href}"${post}>`;
    }
    return `<a ${pre}href="/guides"${post}>`;
  });

  return new Response(html, {
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' },
  });
}
