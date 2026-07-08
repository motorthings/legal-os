const DIMENSIONS = [
  { name: "Practice Area Classification", weight: "25%" },
  { name: "Urgency & Risk Assessment", weight: "25%" },
  { name: "Conflict Check Completeness", weight: "20%" },
  { name: "Staffing Recommendation", weight: "15%" },
  { name: "Data Integrity", weight: "15%" },
];

export default function EmptyState() {
  return (
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-6 text-center py-16">
      <div className="w-12 h-12 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center mx-auto mb-4 border border-[var(--primary)]/20">
        <svg className="w-6 h-6 text-[var(--primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-[var(--text)] mb-2">
        Ready to evaluate
      </h3>
      <p className="text-sm text-[var(--text-dim)] mb-8 max-w-md mx-auto">
        Paste a matter summary above and the system will evaluate it across five
        dimensions used in law firm intake assessment.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3 max-w-3xl mx-auto">
        {DIMENSIONS.map((d) => (
          <div
            key={d.name}
            className="p-3 rounded-lg bg-[var(--surface2)] border border-[var(--border)]"
          >
            <div className="text-xs font-medium text-[var(--text)] leading-tight">
              {d.name}
            </div>
            <div className="text-xs text-[var(--text-muted)] mt-0.5 font-mono">
              {d.weight}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
