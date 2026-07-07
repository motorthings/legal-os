-- Migration: Seed legal_standards table with default standards
-- Description: 60 default legal compliance standards for contract analysis

-- VENDOR CONTRACT STANDARDS (12 standards)

-- Payment Terms
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('payment_terms', 'net_days', 'Standard payment terms in days', 'vendor', 'yellow_flag', '{"type": "range", "min": 0, "max": 60, "preferred": 30}', 'Payment terms should not exceed Net 60. Industry standard is Net 30. Longer terms may indicate cash flow issues.', NULL),
('payment_terms', 'early_payment_discount', 'Early payment discount percentage', 'vendor', 'info', '{"type": "range", "min": 0, "max": 5, "preferred": 2}', 'Early payment discounts of 2-3% are common for Net 10 or Net 15 terms.', NULL),
('payment_terms', 'late_payment_penalty', 'Late payment penalty percentage', 'vendor', 'red_flag', '{"type": "range", "min": 0, "max": 18, "preferred": 1.5}', 'Late payment penalties exceeding 18% annually may be considered usurious in some jurisdictions.', NULL);

-- Liability and Indemnification
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('liability', 'liability_cap', 'Liability cap as multiple of contract value', 'vendor', 'red_flag', '{"type": "range", "min": 1, "max": 10, "preferred": 1}', 'Liability should be capped at 1-2x annual contract value. Unlimited liability is a red flag.', NULL),
('liability', 'liability_cap_exceptions', 'Exceptions to liability cap', 'vendor', 'red_flag', '{"type": "list", "allowed": ["gross_negligence", "willful_misconduct", "ip_infringement", "data_breach", "confidentiality"], "max_exceptions": 5}', 'Common exceptions include gross negligence, IP infringement, and data breaches. Avoid overly broad exceptions.', NULL),
('liability', 'consequential_damages', 'Consequential damages exclusion', 'vendor', 'red_flag', '{"type": "boolean", "required": true}', 'Both parties should exclude consequential, indirect, and punitive damages except for specified exceptions.', NULL),
('indemnification', 'mutual_indemnity', 'Mutual indemnification obligations', 'vendor', 'red_flag', '{"type": "boolean", "required": true}', 'Indemnification should be mutual and balanced. One-sided indemnity is a red flag.', NULL),
('indemnification', 'ip_infringement_indemnity', 'IP infringement indemnification', 'vendor', 'red_flag', '{"type": "required_clause", "must_include": ["vendor_defends", "vendor_pays", "vendor_replaces"]}', 'Vendor must indemnify against IP infringement claims and defend, pay judgments, or replace infringing materials.', NULL);

-- Warranties and Representations
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('warranties', 'warranty_period', 'Warranty period in months', 'vendor', 'yellow_flag', '{"type": "range", "min": 3, "max": 24, "preferred": 12}', 'Standard warranty period is 12 months. Software should have ongoing support and maintenance terms.', NULL),
('warranties', 'performance_warranty', 'Performance meets specifications', 'vendor', 'red_flag', '{"type": "required_clause", "must_include": ["meets_specs", "remedy", "termination_right"]}', 'Vendor must warrant services meet documented specifications with remedies and termination rights.', NULL),
('warranties', 'no_harmful_code', 'Warranty against harmful code', 'vendor', 'red_flag', '{"type": "required_clause", "must_include": ["no_viruses", "no_backdoors", "no_malware"]}', 'For software contracts, vendor must warrant deliverables are free of viruses, backdoors, and malicious code.', NULL);

-- Termination
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('termination', 'convenience_termination', 'Termination for convenience notice period', 'vendor', 'yellow_flag', '{"type": "range", "min": 30, "max": 90, "preferred": 60}', 'Both parties should have right to terminate for convenience with 60-90 days notice.', NULL);


-- CUSTOMER CONTRACT STANDARDS (12 standards)

-- Revenue and Payment
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('payment_terms', 'customer_net_days', 'Customer payment terms', 'customer', 'red_flag', '{"type": "range", "min": 0, "max": 45, "preferred": 30}', 'Customer payment terms should be Net 30 or less to ensure healthy cash flow.', NULL),
('payment_terms', 'auto_renewal', 'Automatic renewal terms', 'customer', 'yellow_flag', '{"type": "object", "requires_notice": true, "notice_days": {"min": 60, "max": 90}}', 'Auto-renewal is acceptable with 60-90 day advance notice requirement and opt-out rights.', NULL),
('revenue', 'price_increase_cap', 'Annual price increase cap percentage', 'customer', 'red_flag', '{"type": "range", "min": 0, "max": 10, "preferred": 5}', 'Price increases should be capped at 5% annually or tied to CPI.', NULL);

-- Service Level Agreements
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('sla', 'uptime_guarantee', 'Service uptime percentage', 'customer', 'red_flag', '{"type": "range", "min": 99.0, "max": 100, "preferred": 99.9}', 'SaaS services should guarantee 99.9% uptime with service credits for violations.', NULL),
('sla', 'response_time', 'Support response time in hours', 'customer', 'yellow_flag', '{"type": "range", "min": 1, "max": 48, "preferred": 4}', 'Critical issues should have 4-hour response time. Non-critical can be 24-48 hours.', NULL),
('sla', 'service_credits', 'Service credit percentage for SLA breach', 'customer', 'red_flag', '{"type": "range", "min": 5, "max": 100, "preferred": 10}', 'SLA breaches should result in service credits of 10% per incident, capped at 100% monthly.', NULL);

-- Data and IP
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('data_rights', 'customer_data_ownership', 'Customer owns their data', 'customer', 'red_flag', '{"type": "required_clause", "must_include": ["customer_owns", "export_rights", "deletion_rights"]}', 'Customer must retain ownership of all customer data with rights to export and deletion.', NULL),
('ip_rights', 'work_product_ownership', 'Ownership of custom work product', 'customer', 'red_flag', '{"type": "required_clause", "must_include": ["customer_owns_custom", "vendor_retains_general"]}', 'Customer should own custom work product. Vendor retains ownership of pre-existing IP and general platform.', NULL),
('confidentiality', 'nda_term', 'Confidentiality obligation period in years', 'customer', 'yellow_flag', '{"type": "range", "min": 2, "max": 10, "preferred": 5}', 'Confidentiality obligations should survive termination for 3-5 years. Trade secrets should be indefinite.', NULL);

-- Customer Protections
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('audit', 'audit_rights', 'Customer audit rights', 'customer', 'red_flag', '{"type": "required_clause", "must_include": ["annual_audit", "security_audit", "compliance_audit"]}', 'Customer should have right to audit vendor security, compliance, and financials annually.', NULL),
('insurance', 'vendor_insurance', 'Vendor insurance requirements', 'customer', 'red_flag', '{"type": "object", "general_liability": {"min": 1000000, "preferred": 2000000}, "cyber_liability": {"min": 1000000, "preferred": 5000000}}', 'Vendor should maintain $2M general liability and $5M cyber liability insurance.', NULL),
('security', 'security_standards', 'Required security certifications', 'customer', 'red_flag', '{"type": "list", "required": ["SOC2", "ISO27001"], "preferred": ["SOC2", "ISO27001", "GDPR", "HIPAA"]}', 'Vendor should maintain SOC 2 Type II and ISO 27001 certifications at minimum.', NULL);


-- EMPLOYMENT CONTRACT STANDARDS (12 standards)

-- Compensation
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('compensation', 'salary_payment_frequency', 'Salary payment frequency', 'employment', 'red_flag', '{"type": "list", "allowed": ["weekly", "biweekly", "semimonthly", "monthly"], "preferred": "biweekly"}', 'Salary should be paid biweekly or semimonthly per state law requirements.', NULL),
('compensation', 'overtime_eligible', 'Overtime eligibility clarification', 'employment', 'red_flag', '{"type": "required_clause", "must_include": ["exempt_status", "flsa_classification"]}', 'Contract must clearly state FLSA exempt/non-exempt status and overtime eligibility.', NULL),
('benefits', 'benefits_waiting_period', 'Waiting period for benefits in days', 'employment', 'yellow_flag', '{"type": "range", "min": 0, "max": 90, "preferred": 30}', 'Benefits should begin within 30-60 days of employment start date.', NULL),
('benefits', 'pto_accrual', 'PTO days per year', 'employment', 'yellow_flag', '{"type": "range", "min": 10, "max": 30, "preferred": 15}', 'Standard PTO is 15-20 days annually for professional positions.', NULL);

-- Restrictive Covenants
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('non_compete', 'non_compete_duration', 'Non-compete duration in months', 'employment', 'red_flag', '{"type": "range", "min": 0, "max": 24, "preferred": 12}', 'Non-compete should not exceed 12 months and be limited to reasonable geographic scope. Some states ban non-competes.', NULL),
('non_compete', 'non_compete_geography', 'Geographic scope of non-compete', 'employment', 'red_flag', '{"type": "required_clause", "must_include": ["specific_geography", "reasonable_scope"]}', 'Non-compete geography must be reasonable and limited to markets where company operates.', NULL),
('non_solicitation', 'non_solicitation_duration', 'Non-solicitation duration in months', 'employment', 'yellow_flag', '{"type": "range", "min": 0, "max": 24, "preferred": 12}', 'Non-solicitation of employees and customers should not exceed 12-24 months.', NULL),
('confidentiality', 'employment_nda_term', 'Confidentiality term for employees', 'employment', 'red_flag', '{"type": "indefinite", "survives_termination": true}', 'Employee confidentiality obligations should be indefinite and survive termination.', NULL);

-- IP Assignment
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('ip_assignment', 'work_for_hire', 'Work made for hire assignment', 'employment', 'red_flag', '{"type": "required_clause", "must_include": ["assigns_ip", "work_for_hire", "future_inventions"]}', 'All work product and inventions created during employment must be assigned to employer.', NULL),
('ip_assignment', 'prior_inventions', 'Exclusion of prior inventions', 'employment', 'yellow_flag', '{"type": "required_clause", "must_include": ["employee_lists_prior", "excluded_from_assignment"]}', 'Employee should have opportunity to list prior inventions excluded from assignment.', NULL);

-- Termination
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('termination', 'at_will_employment', 'At-will employment status', 'employment', 'red_flag', '{"type": "required_clause", "must_include": ["at_will", "either_party_may_terminate"]}', 'Employment should be at-will unless executive contract with cause-based termination.', NULL),
('termination', 'severance_terms', 'Severance package terms', 'employment', 'info', '{"type": "object", "weeks_per_year": {"min": 1, "max": 4, "preferred": 2}, "cap_weeks": {"max": 52}}', 'Severance typically provides 1-2 weeks per year of service, capped at 26-52 weeks.', NULL);


-- DATA PROCESSING AGREEMENT (DPA) STANDARDS (12 standards)

-- Data Protection
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('data_protection', 'data_retention_period', 'Maximum data retention period in months', 'dpa', 'red_flag', '{"type": "range", "min": 0, "max": 84, "preferred": 36}', 'Personal data should be retained only as long as necessary, typically 3 years or less unless required by law.', NULL),
('data_protection', 'data_minimization', 'Data minimization requirements', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["collect_minimum", "purpose_limitation", "storage_limitation"]}', 'Processor should only collect and process minimum data necessary for specified purposes.', NULL),
('data_protection', 'lawful_basis', 'Lawful basis for processing', 'dpa', 'red_flag', '{"type": "list", "required": ["consent", "contract", "legal_obligation", "legitimate_interest"]}', 'DPA must specify lawful basis for processing under GDPR Article 6.', NULL);

-- Security Measures
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('security', 'encryption_requirements', 'Encryption requirements for data', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["encryption_at_rest", "encryption_in_transit", "key_management"]}', 'Personal data must be encrypted at rest and in transit using industry-standard encryption (AES-256).', NULL),
('security', 'access_controls', 'Access control requirements', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["role_based_access", "mfa", "least_privilege", "audit_logs"]}', 'Processor must implement role-based access controls, MFA, and maintain audit logs.', NULL),
('security', 'security_assessments', 'Security assessment frequency', 'dpa', 'red_flag', '{"type": "object", "penetration_test": "annual", "vulnerability_scan": "quarterly", "security_audit": "annual"}', 'Processor should conduct annual penetration tests and quarterly vulnerability scans.', NULL);

-- Breach Notification
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('breach_notification', 'breach_notification_time', 'Breach notification time in hours', 'dpa', 'red_flag', '{"type": "range", "min": 24, "max": 72, "preferred": 48}', 'Data breaches must be reported to controller within 72 hours per GDPR Article 33.', NULL),
('breach_notification', 'breach_notification_content', 'Required breach notification content', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["nature_of_breach", "affected_data", "affected_individuals", "mitigation_steps", "contact_info"]}', 'Breach notifications must include nature, scope, affected individuals, and mitigation steps.', NULL);

-- Data Subject Rights
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('data_subject_rights', 'right_to_access', 'Response time for access requests in days', 'dpa', 'red_flag', '{"type": "range", "min": 1, "max": 30, "preferred": 30}', 'Data subject access requests must be fulfilled within 30 days per GDPR Article 15.', NULL),
('data_subject_rights', 'right_to_deletion', 'Right to deletion implementation', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["deletion_process", "verification", "confirmation", "exceptions"]}', 'Processor must implement right to deletion (erasure) per GDPR Article 17 with proper verification.', NULL),
('data_subject_rights', 'data_portability', 'Data portability format', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["structured_format", "machine_readable", "commonly_used"]}', 'Data must be exportable in structured, machine-readable format (JSON, CSV) per GDPR Article 20.', NULL);

-- Sub-processors
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('sub_processors', 'sub_processor_approval', 'Sub-processor approval requirements', 'dpa', 'red_flag', '{"type": "required_clause", "must_include": ["prior_written_consent", "notification_period", "objection_rights"]}', 'Processor must obtain prior written consent for sub-processors with 30-day objection period.', NULL);


-- GENERAL CONTRACT STANDARDS (12 standards)

-- Governing Law and Jurisdiction
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('jurisdiction', 'governing_law', 'Governing law jurisdiction', 'general', 'red_flag', '{"type": "required_clause", "must_include": ["specific_state", "specific_country"]}', 'Contract should specify governing law. Prefer jurisdiction where company is headquartered.', NULL),
('jurisdiction', 'dispute_resolution', 'Dispute resolution mechanism', 'general', 'yellow_flag', '{"type": "list", "allowed": ["litigation", "arbitration", "mediation"], "preferred": "mediation_then_arbitration"}', 'Specify dispute resolution mechanism. Consider mediation followed by binding arbitration.', NULL),
('jurisdiction', 'venue', 'Exclusive venue for disputes', 'general', 'yellow_flag', '{"type": "required_clause", "must_include": ["specific_court", "specific_location"]}', 'Specify exclusive venue for disputes. Should align with governing law jurisdiction.', NULL);

-- Force Majeure
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('force_majeure', 'force_majeure_events', 'Covered force majeure events', 'general', 'yellow_flag', '{"type": "list", "should_include": ["natural_disaster", "war", "pandemic", "government_action"], "should_exclude": ["economic_hardship", "supplier_failure"]}', 'Force majeure should cover unforeseeable events beyond control but exclude economic hardship.', NULL),
('force_majeure', 'force_majeure_notice', 'Notice period for force majeure in days', 'general', 'info', '{"type": "range", "min": 1, "max": 30, "preferred": 10}', 'Party claiming force majeure should notify within 10 days of event.', NULL);

-- Assignment and Transfer
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('assignment', 'assignment_restrictions', 'Assignment and transfer restrictions', 'general', 'red_flag', '{"type": "required_clause", "must_include": ["consent_required", "change_of_control", "affiliate_exception"]}', 'Assignment should require consent except for affiliates and change of control transactions.', NULL);

-- Amendments and Waivers
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('amendments', 'amendment_process', 'Contract amendment requirements', 'general', 'red_flag', '{"type": "required_clause", "must_include": ["written_only", "signed_by_both", "no_oral_modifications"]}', 'Amendments must be in writing and signed by both parties. No oral modifications.', NULL),
('amendments', 'waiver_provision', 'Waiver requirements', 'general', 'yellow_flag', '{"type": "required_clause", "must_include": ["no_implied_waiver", "written_waiver"]}', 'Waiver must be in writing. No waiver of one breach waives other breaches.', NULL);

-- Notices
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('notices', 'notice_method', 'Required notice methods', 'general', 'yellow_flag', '{"type": "list", "allowed": ["email", "certified_mail", "courier"], "preferred": ["email", "certified_mail"]}', 'Notices should be by email with confirmation or certified mail. Include notice addresses.', NULL);

-- Entire Agreement and Severability
INSERT INTO legal_standards (category, term_name, description, contract_type, violation_severity, acceptable_values, recommendation, client_id) VALUES
('general_provisions', 'entire_agreement', 'Entire agreement clause', 'general', 'red_flag', '{"type": "required_clause", "must_include": ["supersedes_prior", "complete_agreement"]}', 'Contract should contain entire agreement clause superseding all prior agreements.', NULL),
('general_provisions', 'severability', 'Severability clause', 'general', 'yellow_flag', '{"type": "required_clause", "must_include": ["invalid_provisions_severed", "remaining_provisions_enforced"]}', 'Contract should include severability clause to preserve enforceability if one provision is invalid.', NULL);

-- COMMENT
COMMENT ON TABLE legal_standards IS 'Default legal compliance standards seeded for automated contract analysis across all contract types';
