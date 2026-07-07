'use client';

export default function SecurityFooter() {
  return (
    <footer className="border-t border-default mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="text-xs text-muted space-y-2">
          <p className="font-semibold">Data Security & Confidentiality</p>
          <p>
            All contract data is encrypted in transit (TLS 1.3) and at rest (AES-256).
            AI processing is performed via secure API connections to Anthropic Claude
            with no data retention by the AI provider. Access is restricted via role-based
            authentication and row-level security policies.
          </p>
          <p>
            This application is designed for internal use only. Do not share access credentials
            or upload contracts containing highly sensitive information without proper authorization.
            All processing activity is logged for audit purposes.
          </p>
          <p className="text-[10px] opacity-70">
            © {new Date().getFullYear()} Contract Review System. For authorized users only.
          </p>
        </div>
      </div>
    </footer>
  );
}
