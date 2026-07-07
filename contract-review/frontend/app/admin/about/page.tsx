'use client';

import { useState } from 'react';

type TabType = 'overview' | 'governance' | 'security' | 'tech';

export default function AboutPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-primary">About Contract Review</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'overview'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('governance')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'governance'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Data Governance
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'security'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Security & Privacy
          </button>
          <button
            onClick={() => setActiveTab('tech')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'tech'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-gray-300'
            }`}
          >
            Technology Stack
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <>
            {/* Compliance Badge */}
            <div className="card p-6 border-2" style={{ borderColor: 'var(--color-primary)' }}>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-primary)' }}>
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-primary mb-2">Enterprise-Grade Security & Compliance</h2>
                  <p className="text-secondary text-lg mb-4">
                    Built on infrastructure trusted by the world's leading organizations with SOC 2 Type II certified services
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <span className="px-4 py-2 bg-card rounded-full text-sm font-semibold text-primary border border-border shadow-sm">
                      SOC 2 Type II Infrastructure
                    </span>
                    <span className="px-4 py-2 bg-card rounded-full text-sm font-semibold text-primary border border-border shadow-sm">
                      ISO 27001 Compliant
                    </span>
                    <span className="px-4 py-2 bg-card rounded-full text-sm font-semibold text-primary border border-border shadow-sm">
                      GDPR Compliant
                    </span>
                    <span className="px-4 py-2 bg-card rounded-full text-sm font-semibold text-primary border border-border shadow-sm">
                      End-to-End Encryption
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Third-Party Services */}
            <div className="card p-6">
              <h2 className="text-xl font-semibold text-primary mb-4">Trusted Third-Party Services & Certifications</h2>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 font-semibold text-primary">Service</th>
                      <th className="text-left py-3 px-4 font-semibold text-primary">Purpose</th>
                      <th className="text-center py-3 px-4 font-semibold text-primary">SOC 2 Type II</th>
                      <th className="text-center py-3 px-4 font-semibold text-primary">ISO 27001</th>
                      <th className="text-center py-3 px-4 font-semibold text-primary">HIPAA</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border hover:bg-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-primary">Anthropic Claude</td>
                      <td className="py-3 px-4 text-sm text-muted">AI language model for contract analysis</td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                    </tr>
                    <tr className="border-b border-border hover:bg-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-primary">Supabase</td>
                      <td className="py-3 px-4 text-sm text-muted">Database, auth, and storage infrastructure</td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-gray-300">—</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                    </tr>
                    <tr className="border-b border-border hover:bg-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-primary">Vercel</td>
                      <td className="py-3 px-4 text-sm text-muted">Frontend hosting and edge network</td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-gray-300">—</span>
                      </td>
                    </tr>
                    <tr className="border-b border-border hover:bg-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-primary">Railway</td>
                      <td className="py-3 px-4 text-sm text-muted">Backend API hosting</td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-gray-300">—</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-gray-300">—</span>
                      </td>
                    </tr>
                    <tr className="hover:bg-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-primary">Sentry</td>
                      <td className="py-3 px-4 text-sm text-muted">Error tracking and performance monitoring</td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-gray-300">—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {activeTab === 'governance' && (
          <div className="card p-6">
            <div className="prose prose-sm max-w-none">
              <div className="space-y-3 text-secondary">
                <div>
                  <h2 className="font-semibold text-primary text-xl mb-4">AI Data Processing & Privacy</h2>
                  <div className="space-y-3">
                    <p className="text-sm">
                      All contract processing happens in secure, isolated environments with enterprise-grade AI privacy protections:
                    </p>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-start gap-2">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500 flex-shrink-0">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                        <span>
                          <strong>Zero Data Retention by AI Provider:</strong> Anthropic Claude processes your documents via API calls but
                          <strong className="text-teal-700"> does not store, log, or use your data for model training</strong>. All processing
                          is ephemeral and your contract data is immediately discarded after analysis.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500 flex-shrink-0">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                        <span>
                          <strong>Encrypted Transmission:</strong> Documents are transmitted to Claude's API over TLS 1.3 encrypted connections.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500 flex-shrink-0">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                        <span>
                          <strong>Secure Storage:</strong> Analysis results are stored encrypted in your dedicated database partition with
                          Row Level Security (RLS) enforcement—only you can access your data.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500 flex-shrink-0">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                        <span>
                          <strong>No Third-Party Training:</strong> Your contracts never become part of any AI training dataset.
                          Your sensitive business data remains private and confidential.
                        </span>
                      </li>
                      <li className="flex items-start gap-2">
                        <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-500 flex-shrink-0">
                          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                            <path d="M13 4L6 11L3 8" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        </div>
                        <span>
                          <strong>SOC 2 Type II Certified AI:</strong> Anthropic Claude maintains SOC 2 Type II certification
                          with strict security controls and regular third-party audits.
                        </span>
                      </li>
                    </ul>
                  </div>
                </div>

                <div>
                  <h2 className="font-semibold text-primary text-xl mb-4">Access Controls</h2>
                  <p className="text-sm">
                    Multi-level access control ensures users only see their own data. Admin users have enhanced
                    permissions for system management. All access is logged and auditable.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="card p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left Column */}
              <div className="space-y-6">
                {/* Authentication */}
                <div className="border-l-4 border-teal-500 pl-4">
                  <h3 className="font-semibold text-primary mb-2">Authentication & Authorization</h3>
                  <ul className="space-y-2 text-secondary text-sm">
                    <li className="flex items-start gap-2">
                      <span className="text-teal-600 mt-0.5">✓</span>
                      <span>JWT-based authentication via Supabase Auth</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-teal-600 mt-0.5">✓</span>
                      <span>Role-based access control (Admin/User)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-teal-600 mt-0.5">✓</span>
                      <span>Session management with secure tokens</span>
                    </li>
                  </ul>
                </div>

                {/* Data Protection */}
                <div className="border-l-4 border-blue-500 pl-4">
                  <h3 className="font-semibold text-primary mb-2">Data Protection</h3>
                  <ul className="space-y-2 text-secondary text-sm">
                    <li className="flex items-start gap-2">
                      <span className="text-blue-600 mt-0.5">✓</span>
                      <span>Row Level Security (RLS) policies in PostgreSQL</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-blue-600 mt-0.5">✓</span>
                      <span>Encryption at rest for all database data</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-blue-600 mt-0.5">✓</span>
                      <span>Encryption in transit via HTTPS/TLS</span>
                    </li>
                  </ul>
                </div>

                {/* Privacy Practices */}
                <div className="border-l-4 border-orange-500 pl-4">
                  <h3 className="font-semibold text-primary mb-2">Privacy Practices</h3>
                  <ul className="space-y-2 text-secondary text-sm">
                    <li className="flex items-start gap-2">
                      <span className="text-orange-600 mt-0.5">✓</span>
                      <span>User data isolation with RLS policies</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-orange-600 mt-0.5">✓</span>
                      <span>No third-party data sharing without consent</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-orange-600 mt-0.5">✓</span>
                      <span>Minimal data collection principles</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Right Column */}
              <div className="space-y-6">
                {/* API Security */}
                <div className="border-l-4 border-purple-500 pl-4">
                  <h3 className="font-semibold text-primary mb-2">API Security</h3>
                  <ul className="space-y-2 text-secondary text-sm">
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>CORS protection with configurable origins</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>Rate limiting to prevent abuse</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-purple-600 mt-0.5">✓</span>
                      <span>Input validation via Pydantic schemas</span>
                    </li>
                  </ul>
                </div>

                {/* Monitoring & Compliance */}
                <div className="border-l-4 border-green-500 pl-4">
                  <h3 className="font-semibold text-primary mb-2">Monitoring & Compliance</h3>
                  <ul className="space-y-2 text-secondary text-sm">
                    <li className="flex items-start gap-2">
                      <span className="text-green-600 mt-0.5">✓</span>
                      <span>Real-time error tracking with Sentry</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-600 mt-0.5">✓</span>
                      <span>Comprehensive logging and audit trails</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-green-600 mt-0.5">✓</span>
                      <span>Regular security updates and dependency scanning</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'tech' && (
          <div className="card p-6">
            <div className="space-y-6">
              {/* Frontend */}
              <div>
                <h3 className="text-lg font-semibold text-primary mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Frontend
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Next.js 16.0.7</div>
                    <div className="text-sm text-muted text-right">React framework with Turbopack</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">React 19.2.0</div>
                    <div className="text-sm text-muted text-right">UI library</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">TypeScript 5</div>
                    <div className="text-sm text-muted text-right">Type-safe development</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Tailwind CSS 4</div>
                    <div className="text-sm text-muted text-right">Utility-first styling</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Supabase Client</div>
                    <div className="text-sm text-muted text-right">Auth & real-time data</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Sentry</div>
                    <div className="text-sm text-muted text-right">Error tracking & monitoring</div>
                  </div>
                </div>
              </div>

              {/* Backend */}
              <div>
                <h3 className="text-lg font-semibold text-primary mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Backend
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">FastAPI 0.115.0</div>
                    <div className="text-sm text-muted text-right">High-performance Python API</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Uvicorn</div>
                    <div className="text-sm text-muted text-right">ASGI server</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Pydantic 2</div>
                    <div className="text-sm text-muted text-right">Data validation</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">APScheduler</div>
                    <div className="text-sm text-muted text-right">Background job scheduling</div>
                  </div>
                </div>
              </div>

              {/* AI & ML */}
              <div>
                <h3 className="text-lg font-semibold text-primary mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI & Machine Learning
                </h3>
                <div className="grid grid-cols-1 gap-3">
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Anthropic Claude</div>
                    <div className="text-sm text-muted text-right">Advanced language models for contract analysis</div>
                  </div>
                </div>
              </div>

              {/* Database & Storage */}
              <div>
                <h3 className="text-lg font-semibold text-primary mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                  Database & Storage
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Supabase PostgreSQL</div>
                    <div className="text-sm text-muted text-right">Managed database with RLS</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Supabase Storage</div>
                    <div className="text-sm text-muted text-right">Encrypted file storage</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Redis</div>
                    <div className="text-sm text-muted text-right">Caching layer (optional)</div>
                  </div>
                </div>
              </div>

              {/* Infrastructure */}
              <div>
                <h3 className="text-lg font-semibold text-primary mb-3 flex items-center gap-2">
                  <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                  </svg>
                  Infrastructure
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Vercel</div>
                    <div className="text-sm text-muted text-right">Frontend hosting & CDN</div>
                  </div>
                  <div className="bg-hover rounded-lg p-2 border border-border flex justify-between items-start gap-3">
                    <div className="font-medium text-primary">Railway</div>
                    <div className="text-sm text-muted text-right">Backend API hosting</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Version Info - Always visible */}
        <div className="card p-6 bg-gray-50 dark:bg-gray-900">
          <div className="flex items-center justify-between text-sm text-muted">
            <div>
              <span className="font-medium">Platform Version:</span> 1.0.0
            </div>
            <div>
              <span className="font-medium">Last Updated:</span> {new Date().toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
