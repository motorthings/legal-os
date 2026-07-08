"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createProject } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function NewProjectPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (loading) return null;
  if (!user) {
    router.push("/login");
    return null;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError("");

    const form = new FormData(e.currentTarget);
    try {
      const project = await createProject({
        client_id: user!.id, // Will be resolved server-side from JWT
        practice_group_id: "00000000-0000-0000-0000-000000000001", // TODO: pick from user's groups
        name: form.get("name") as string,
        description: (form.get("description") as string) || undefined,
        deal_type: (form.get("deal_type") as string) || undefined,
        counterparty: (form.get("counterparty") as string) || undefined,
        created_by: user!.id,
      });
      router.push(`/due-diligence/${project.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-xl">
      <Link
        href="/due-diligence"
        className="font-mono text-xs text-[var(--text-dim)] hover:text-[var(--secondary)] no-underline mb-4 inline-block"
      >
        &larr; Back
      </Link>

      <h1 className="text-3xl font-bold mb-8">New Due Diligence Project</h1>

      {error && (
        <div className="card p-4 mb-6 border-[var(--rose)] text-[var(--rose)] text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid gap-4">
        <div>
          <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
            Project Name *
          </label>
          <input name="name" required placeholder="e.g. Acme Corp Merger DD" />
        </div>

        <div>
          <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
            Description
          </label>
          <textarea
            name="description"
            rows={2}
            placeholder="Brief description of the deal and scope..."
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
              Deal Type
            </label>
            <select name="deal_type">
              <option value="">Select...</option>
              <option value="merger">Merger</option>
              <option value="acquisition">Acquisition</option>
              <option value="financing">Financing</option>
              <option value="ipo">IPO</option>
              <option value="restructuring">Restructuring</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
              Counterparty
            </label>
            <input name="counterparty" placeholder="Entity name" />
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Creating..." : "Create Project"}
          </button>
          <Link href="/due-diligence" className="btn-secondary no-underline">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
