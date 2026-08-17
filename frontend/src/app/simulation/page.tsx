'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/lib/auth';

interface Firm {
  id: string;
  name: string;
  status: string;
  created_at: string;
}

export default function FirmsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [firms, setFirms] = useState<Firm[]>([]);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { data, error } = await supabase
      .from('firms')
      .select('id, name, status, created_at')
      .order('created_at', { ascending: false });
    if (error) setError(error.message);
    else setFirms(data ?? []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createFirm(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    const { data, error } = await supabase
      .from('firms')
      .insert({ name: newName.trim(), owner_id: user?.id })
      .select('id')
      .single();
    if (error) setError(error.message);
    else {
      setNewName('');
      router.push(`/simulation/firms/${data.id}`);
    }
  }

  async function deleteFirm(id: string) {
    const { error } = await supabase.from('firms').delete().eq('id', id);
    if (error) setError(error.message);
    else setFirms((f) => f.filter((x) => x.id !== id));
  }

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '2rem 1rem' }}>
      <header>
        <h1>Firms</h1>
      </header>

      <form onSubmit={createFirm} style={{ display: 'flex', gap: '0.5rem', margin: '1rem 0' }}>
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="New firm name…" style={{ flex: 1 }} />
        <button type="submit" disabled={!newName.trim()}>Create</button>
      </form>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {loading ? (
        <p>Loading…</p>
      ) : firms.length === 0 ? (
        <p style={{ color: '#888' }}>No firms yet. Create one to run an intake.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {firms.map((f) => (
            <li key={f.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', padding: '0.75rem 0' }}>
              <Link href={`/simulation/firms/${f.id}`} style={{ textDecoration: 'none' }}>
                <strong>{f.name}</strong> <span style={{ color: '#888' }}>· {f.status}</span>
              </Link>
              <button onClick={() => deleteFirm(f.id)} style={{ background: 'none', border: 'none', color: 'crimson', cursor: 'pointer' }}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
