-- ============================================================================
-- Legal AI OS — Demo Data Seed
-- ============================================================================
-- Creates a demo client, practice groups, users, matters, and sample documents
-- for development and demonstration purposes.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DEMO CLIENT
-- ----------------------------------------------------------------------------

insert into clients (id, name, slug, industry, jurisdiction, is_active) values
    ('d3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'Meridian Law Group', 'meridian-law', 'legal_services', 'US', true)
on conflict (id) do nothing;

-- ----------------------------------------------------------------------------
-- PRACTICE GROUPS
-- ----------------------------------------------------------------------------

insert into practice_groups (id, client_id, name, slug, description) values
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'Corporate M&A', 'corporate-ma', 'Mergers, acquisitions, due diligence, and corporate governance'),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'Litigation', 'litigation', 'Commercial litigation, arbitration, and regulatory defense'),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567803', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'Employment', 'employment', 'Employment law, worker classification, compliance'),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567804', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'Intellectual Property', 'ip', 'Patents, trademarks, copyright, trade secrets')
on conflict (client_id, slug) do nothing;

-- ----------------------------------------------------------------------------
-- MATTERS
-- ----------------------------------------------------------------------------

insert into matters (id, client_id, practice_group_id, name, description, matter_number, jurisdiction, practice_area, status, billing_type, estimated_hours, estimated_budget, adverse_parties, key_dates, risk_level, risk_score, confidence, created_by) values
    ('f1e2d3c4-b5a6-9780-1234-567890abcdef', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Acme Corp Acquisition', 'Due diligence and acquisition of Acme Corp by Stellar Industries. $450M all-cash deal. Key areas: IP portfolio, employment agreements, regulatory approvals.', 'MLG-2026-001', 'US', 'corporate', 'active', 'fixed_fee', 450, 750000.00, array['Stellar Industries', 'Acme Corp Shareholders'], '{"filing_deadline": "2026-09-15", "closing_date": "2026-12-01", "regulatory_approval": "2026-10-30"}', 'medium', 45, 88, '00000000-0000-0000-0000-000000000000'),

    ('f1e2d3c4-b5a6-9780-1234-567890abcdf1', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'DataTech Privacy Class Action', 'Defense of DataTech Inc. in consumer privacy class action. Alleged violations of state biometric privacy laws affecting ~2.3M users.', 'MLG-2026-002', 'US-IL', 'litigation', 'active', 'hourly', 1200, null, array['Jane Doe et al.', 'State of Illinois AG'], '{"class_cert_hearing": "2026-08-01", "discovery_cutoff": "2026-11-15", "trial_date": "2027-03-01"}', 'high', 72, 79, '00000000-0000-0000-0000-000000000000'),

    ('f1e2d3c4-b5a6-9780-1234-567890abcdf2', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567803', 'GlobalTech Workforce Restructuring', 'Employment compliance review for GlobalTech workforce reduction of ~1,500 employees across 12 states. WARN Act, severance, and non-compete analysis.', 'MLG-2026-003', 'US', 'employment', 'active', 'fixed_fee', 250, 425000.00, array['GlobalTech Inc.'], '{"reduction_date": "2026-10-01", "notice_deadline": "2026-08-01"}', 'medium', 55, 91, '00000000-0000-0000-0000-000000000000'),

    ('f1e2d3c4-b5a6-9780-1234-567890abcdf3', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'NovaTech IPO Preparation', 'IPO readiness assessment and preparation for NovaTech Inc. Estimated $2.1B valuation. SEC filing preparation, governance review, and risk factor analysis.', 'MLG-2026-004', 'US', 'corporate', 'active', 'fixed_fee', 600, 1200000.00, array['NovaTech Inc.', 'Underwriters Consortium'], '{"filing_date": "2027-01-15", "roadshow_start": "2027-02-15", "pricing_date": "2027-03-01"}', 'medium', 38, 85, '00000000-0000-0000-0000-000000000000'),

    ('f1e2d3c4-b5a6-9780-1234-567890abcdf4', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567804', 'BioGen Patent Portfolio Review', 'Strategic review of BioGen''s patent portfolio — 287 patents across 18 families. Freedom-to-operate analysis, licensing opportunities, and maintenance recommendations.', 'MLG-2026-005', 'US', 'ip', 'intake', 'fixed_fee', 180, 350000.00, array['BioGen Corp.', 'Competitor Analysis Only'], '{"initial_report": "2026-09-01", "final_recommendations": "2026-10-15"}', 'low', 28, 92, '00000000-0000-0000-0000-000000000000')
on conflict (id) do nothing;

-- ----------------------------------------------------------------------------
-- KNOWLEDGE DOCUMENTS (sample)
-- ----------------------------------------------------------------------------

insert into knowledge_documents (id, client_id, practice_group_id, title, document_type, raw_text, chunk_count, metadata, is_active) values
    ('e1d2c3b4-a5f6-7890-1234-567890abcdef', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801',
     'Wilson Corp Merger DD Report (2024)', 'memo',
     'Comprehensive due diligence report for the Wilson Corporation merger. Key findings: Indemnification clauses in 14 of 23 material contracts exceed standard market terms with unlimited liability caps. Employment agreements for 7 key executives contain change-of-control provisions triggering $23M in accelerated vesting. Environmental liability exposure at 2 manufacturing sites estimated at $5-8M. IP portfolio has 3 pending patent applications with office actions requiring responses within 90 days. Revenue recognition practices require alignment with ASC 606 before close. Recommendation: Proceed with adjustments to purchase price by $12-15M to account for identified risks.',
     4,
     '{"summary": "Due diligence report for Wilson Corp merger — identified risks in indemnification, employment, environmental, and IP", "author": "Partner Review", "date": "2024-11-15", "matter": "Wilson Corp Merger"}',
     true),

    ('e1d2c3b4-a5f6-7890-1234-567890abcde0', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801',
     'Standard Indemnification Clause — Market Terms', 'contract',
     'Market standard indemnification clause language for M&A transactions. Standard terms: survival period 12-18 months post-close, basket/deductible of 0.5-1.0% of purchase price, cap at 10-15% of purchase price. Carve-outs for fraud, willful misconduct, and fundamental representations survive indefinitely. Knowledge qualifiers should be limited to actual knowledge of designated individuals. Sandbagging provisions: pro-sandbagging recommended in majority of deals. Exclusive remedy provision standard for post-close claims except for fraud and specific performance.',
     2,
     '{"summary": "Standard market terms for M&A indemnification clauses — used as baseline for due diligence review", "author": "Knowledge Management", "date": "2025-03-01"}',
     true),

    ('e1d2c3b4-a5f6-7890-1234-567890abcde1', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802',
     'State Biometric Privacy Laws — 2026 Survey', 'research',
     'Comprehensive survey of state biometric privacy laws as of January 2026. Twelve states have enacted biometric privacy legislation: Illinois (BIPA — private right of action, statutory damages $1,000 negligent/$5,000 intentional per violation), Texas (CUBI — AG enforcement only), Washington (HB 1493 — AG enforcement, private right for actual damages), California (CPRA amendments — limited private right), New York (proposed SHIELD Act amendments), plus 7 others. Key trend: courts interpreting "aggrieved person" broadly under BIPA (Rosenbach v. Six Flags, 2019 IL 123186). Compliance requirements: written policy, informed consent, data retention schedule, prohibition on sale of biometric data. Damages exposure: $1,000-$5,000 per violation × number of affected individuals = potentially billions in class actions.',
     6,
     '{"summary": "50-state survey of biometric privacy laws — key compliance requirements, enforcement trends, and damages exposure analysis", "author": "Regulatory Research Group", "date": "2026-01-15"}',
     true),

    ('e1d2c3b4-a5f6-7890-1234-567890abcde2', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567803',
     'WARN Act Compliance — Multi-State Workforce Reduction Guide', 'memo',
     'Guide to Worker Adjustment and Retraining Notification (WARN) Act compliance for multi-state workforce reductions. Federal WARN: 60 days notice for plant closings (50+ employees) or mass layoffs (500+ or 50+ if 33% of workforce). State mini-WARN acts: California (75 employees, any facility), New York (25 employees, 33% threshold), Illinois (25 employees, 33% threshold), New Jersey (no minimum if plant closing), Wisconsin (25 employees, any reduction), plus 8 other states. Penalties: back pay + benefits for each day of violation, civil penalties up to $500/day. Best practices: staggered notice approach, coordination with state rapid response teams, severance package documentation, release agreement templates.',
     5,
     '{"summary": "Multi-state WARN Act compliance guide for workforce reductions — federal and state requirements, penalties, and best practices", "author": "Employment Practice Group", "date": "2025-09-01"}',
     true),

    ('e1d2c3b4-a5f6-7890-1234-567890abcde3', 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', 'a1b2c3d4-e5f6-7890-abcd-ef1234567804',
     'Patent Portfolio Strategic Review Framework', 'research',
     'Framework for conducting strategic patent portfolio reviews. Five-phase methodology: (1) Inventory & Classification — categorize by technology area, remaining term, geographic coverage, (2) Strength Assessment — claim scope analysis, prosecution history review, prior art landscape, (3) Freedom-to-Operate — competitor patent mapping, design-around analysis, clearance opinions, (4) Commercial Value — market coverage, licensing revenue potential, enforcement history, (5) Recommendations — maintain/abandon/license/sell decisions with cost-benefit analysis. Key metrics: patents per $M revenue (industry standard: 0.8-2.4), maintenance cost per patent ($2K-$15K/year depending on jurisdiction count), litigation ROI (median $5.2M recovery per successful assertion).',
     4,
     '{"summary": "Five-phase methodology for strategic patent portfolio review — classification, strength, FTO, valuation, recommendations", "author": "IP Practice Group", "date": "2026-02-01"}',
     true)
on conflict (id) do nothing;

-- ----------------------------------------------------------------------------
-- FUNCTION CONFIGS (enable all for demo client)
-- ----------------------------------------------------------------------------

insert into function_configs (function_id, client_id, is_enabled, config)
    select id, 'd3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01', true, '{}'
    from functions
on conflict (function_id, client_id) do nothing;

-- ----------------------------------------------------------------------------
-- NOTE: user_profiles are auto-created by the handle_new_user trigger
-- when a user signs up via Supabase Auth with client_id in metadata.
-- To create a demo user, sign up with email and include:
--   { "client_id": "d3b07384-d9a7-4e8b-9a3f-1c2b3a4e5f01", "display_name": "Demo User", "role": "partner" }
-- in the user_metadata.
-- ----------------------------------------------------------------------------
