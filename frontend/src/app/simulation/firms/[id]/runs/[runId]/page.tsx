import Link from 'next/link';
import RunProgress from '@/components/simulation/RunProgress';

export default async function RunPage({ params }: { params: Promise<{ id: string; runId: string }> }) {
  const { id, runId } = await params;
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '2rem 1rem' }}>
      <Link href={`/simulation/firms/${id}`} style={{ color: '#888', textDecoration: 'none' }}>← Back to firm</Link>
      <h1>Run {runId.slice(0, 8)}</h1>
      <RunProgress runId={runId} />
    </main>
  );
}
