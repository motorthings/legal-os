#!/usr/bin/env python3
"""
Seed Legal Standards Database
Populates the legal_standards table with 30 common default standards
Usage: python seed_legal_standards.py
"""

import os
import json
from dotenv import load_dotenv
from supabase import create_client
from logger_config import get_logger

load_dotenv()
logger = get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ==================== DEFAULT LEGAL STANDARDS ====================
# These are sensible defaults that apply to all clients unless overridden

DEFAULT_STANDARDS = [
    # ========== VENDOR CONTRACTS ==========
    {
        "contract_type": "vendor",
        "category": "payment_terms",
        "term_name": "net_days",
        "acceptable_values": {
            "type": "range",
            "max": 60,
            "preferred": 30,
            "acceptable": [30, 45, 60]
        },
        "violation_severity": "yellow_flag",
        "description": "Payment terms should not exceed Net 60",
        "rationale": "Longer payment terms negatively impact cash flow and working capital",
        "recommendation": "Negotiate for Net 30 or Net 45 payment terms"
    },
    {
        "contract_type": "vendor",
        "category": "liability",
        "term_name": "liability_cap_multiple",
        "acceptable_values": {
            "type": "range",
            "min": 12,
            "preferred": 24,
            "description": "Minimum 12 months of fees, prefer 24+ months"
        },
        "violation_severity": "red_flag",
        "description": "Vendor liability cap must be at least 12x monthly fees",
        "rationale": "Caps below 12 months provide inadequate protection against vendor failures",
        "recommendation": "Require minimum 12 months, negotiate for 24+ months or uncapped"
    },
    {
        "contract_type": "vendor",
        "category": "termination",
        "term_name": "convenience_notice_period",
        "acceptable_values": {
            "type": "range",
            "max": 90,
            "preferred": 30,
            "acceptable": [30, 60, 90]
        },
        "violation_severity": "yellow_flag",
        "description": "Termination for convenience notice period should not exceed 90 days",
        "rationale": "Long notice periods create vendor lock-in and reduce flexibility",
        "recommendation": "Negotiate for 30-60 days notice"
    },
    {
        "contract_type": "vendor",
        "category": "sla",
        "term_name": "uptime_guarantee",
        "acceptable_values": {
            "type": "range",
            "min": 99.0,
            "preferred": 99.9,
            "unit": "percentage"
        },
        "violation_severity": "yellow_flag",
        "description": "SLA uptime guarantee should be at least 99%",
        "rationale": "Lower uptime guarantees indicate poor service reliability",
        "recommendation": "Require minimum 99% uptime, prefer 99.9% for critical services"
    },
    {
        "contract_type": "vendor",
        "category": "data_security",
        "term_name": "security_certifications",
        "acceptable_values": {
            "type": "required_any",
            "must_have_one_of": ["SOC 2", "ISO 27001", "FedRAMP"]
        },
        "violation_severity": "red_flag",
        "description": "Vendor must have at least one major security certification",
        "rationale": "Security certifications provide third-party validation of security practices",
        "recommendation": "Require SOC 2 Type II or ISO 27001 certification"
    },
    {
        "contract_type": "vendor",
        "category": "data_security",
        "term_name": "breach_notification_hours",
        "acceptable_values": {
            "type": "range",
            "max": 72,
            "preferred": 24
        },
        "violation_severity": "red_flag",
        "description": "Breach notification must be within 72 hours (prefer 24)",
        "rationale": "Rapid notification is critical for incident response and regulatory compliance",
        "recommendation": "Require notification within 24-48 hours"
    },
    {
        "contract_type": "vendor",
        "category": "audit_rights",
        "term_name": "audit_frequency",
        "acceptable_values": {
            "type": "enum",
            "allowed": ["Annual", "Quarterly", "Upon request with notice"]
        },
        "violation_severity": "yellow_flag",
        "description": "Must have right to audit vendor at least annually",
        "rationale": "Regular audits ensure vendor compliance with security and service obligations",
        "recommendation": "Include right to audit at least annually or upon request"
    },
    {
        "contract_type": "vendor",
        "category": "ip_rights",
        "term_name": "data_ownership",
        "acceptable_values": {
            "type": "enum",
            "required": "Company retains full ownership"
        },
        "violation_severity": "red_flag",
        "description": "Company must retain full ownership of all data",
        "rationale": "Sharing or vendor ownership of company data creates unacceptable IP risk",
        "recommendation": "Require explicit clause confirming company owns all data"
    },

    # ========== CUSTOMER CONTRACTS ==========
    {
        "contract_type": "customer",
        "category": "liability",
        "term_name": "unlimited_liability_categories",
        "acceptable_values": {
            "type": "required_list",
            "must_include": ["IP infringement", "Data breach", "Gross negligence", "Fraud"]
        },
        "violation_severity": "red_flag",
        "description": "Certain liability categories must remain unlimited",
        "rationale": "Capping liability for IP/data/fraud creates unacceptable risk exposure",
        "recommendation": "Ensure IP, data breach, gross negligence, and fraud have unlimited liability"
    },
    {
        "contract_type": "customer",
        "category": "warranties",
        "term_name": "warranty_disclaimer_prohibition",
        "acceptable_values": {
            "type": "boolean",
            "allowed": False,
            "description": "Must NOT disclaim all warranties"
        },
        "violation_severity": "red_flag",
        "description": "Cannot accept blanket warranty disclaimers",
        "rationale": "Customers need warranty protection for service quality and functionality",
        "recommendation": "Remove AS-IS disclaimer, include fitness and merchantability warranties"
    },
    {
        "contract_type": "customer",
        "category": "indemnification",
        "term_name": "customer_indemnification_scope",
        "acceptable_values": {
            "type": "enum",
            "allowed": ["Customer misuse only", "Customer breach only", "Limited scope"]
        },
        "violation_severity": "yellow_flag",
        "description": "Customer indemnification obligations must be limited in scope",
        "rationale": "Broad customer indemnification creates excessive liability exposure",
        "recommendation": "Limit to customer misuse or breach, exclude vendor's failure scenarios"
    },
    {
        "contract_type": "customer",
        "category": "payment_terms",
        "term_name": "advance_payment_prohibition",
        "acceptable_values": {
            "type": "boolean",
            "allowed": False,
            "description": "Avoid requiring full payment in advance"
        },
        "violation_severity": "yellow_flag",
        "description": "Should avoid paying in full advance without delivery",
        "rationale": "Advance payment creates financial risk if vendor fails to deliver",
        "recommendation": "Structure payments based on milestones or subscription periods"
    },

    # ========== EMPLOYMENT CONTRACTS ==========
    {
        "contract_type": "employment",
        "category": "ip_assignment",
        "term_name": "work_product_ownership",
        "acceptable_values": {
            "type": "enum",
            "required": "Company owns all work product"
        },
        "violation_severity": "red_flag",
        "description": "Company must own all work product created during employment",
        "rationale": "Essential to protect company IP rights and prevent ownership disputes",
        "recommendation": "Require full IP assignment clause with no carveouts except legally required"
    },
    {
        "contract_type": "employment",
        "category": "non_compete",
        "term_name": "non_compete_duration",
        "acceptable_values": {
            "type": "range",
            "max": 12,
            "preferred": 6,
            "unit": "months",
            "description": "Maximum 12 months, prefer 6 months"
        },
        "violation_severity": "yellow_flag",
        "description": "Non-compete duration should not exceed 12 months",
        "rationale": "Excessive non-compete periods may be unenforceable and harm employee relations",
        "recommendation": "Limit to 6-12 months for senior roles, consider eliminating for junior roles"
    },
    {
        "contract_type": "employment",
        "category": "non_compete",
        "term_name": "non_compete_geography",
        "acceptable_values": {
            "type": "enum",
            "allowed": ["Reasonable geographic limit", "Where company operates", "State-specific"]
        },
        "violation_severity": "yellow_flag",
        "description": "Non-compete must have reasonable geographic scope",
        "rationale": "Overly broad geography makes non-competes unenforceable",
        "recommendation": "Limit to regions where company actively operates or has customers"
    },
    {
        "contract_type": "employment",
        "category": "confidentiality",
        "term_name": "confidentiality_term",
        "acceptable_values": {
            "type": "enum",
            "allowed": ["Indefinite for trade secrets", "5+ years for confidential info"]
        },
        "violation_severity": "yellow_flag",
        "description": "Confidentiality should be indefinite for trade secrets",
        "rationale": "Perpetual protection needed for true trade secrets",
        "recommendation": "Indefinite for trade secrets, 5+ years for other confidential information"
    },
    {
        "contract_type": "employment",
        "category": "termination",
        "term_name": "at_will_employment",
        "acceptable_values": {
            "type": "boolean",
            "preferred": True,
            "description": "Prefer at-will employment for flexibility"
        },
        "violation_severity": "info",
        "description": "At-will employment provides maximum flexibility (where legal)",
        "rationale": "At-will status allows termination without cause, reducing legal risk",
        "recommendation": "Use at-will where legally permitted; for-cause only where required"
    },

    # ========== DPA CONTRACTS ==========
    {
        "contract_type": "dpa",
        "category": "data_processing",
        "term_name": "purpose_limitation",
        "acceptable_values": {
            "type": "boolean",
            "required": True,
            "description": "Must limit processing to specified purposes only"
        },
        "violation_severity": "red_flag",
        "description": "Processing must be limited to specified purposes only",
        "rationale": "GDPR/CCPA require strict purpose limitation for data processing",
        "recommendation": "Explicitly limit processing to defined business purposes in Annex A"
    },
    {
        "contract_type": "dpa",
        "category": "sub_processors",
        "term_name": "sub_processor_consent",
        "acceptable_values": {
            "type": "enum",
            "required": "Prior written consent required"
        },
        "violation_severity": "red_flag",
        "description": "Must require consent before engaging new sub-processors",
        "rationale": "Controller must approve all processors handling their data",
        "recommendation": "Require prior written consent with right to object to new sub-processors"
    },
    {
        "contract_type": "dpa",
        "category": "data_breach",
        "term_name": "breach_notification_hours",
        "acceptable_values": {
            "type": "range",
            "max": 72,
            "preferred": 24
        },
        "violation_severity": "red_flag",
        "description": "Breach notification required within 72 hours (prefer 24)",
        "rationale": "GDPR requires controller notification within 72 hours; need buffer time",
        "recommendation": "Require processor notification within 24-48 hours of discovery"
    },
    {
        "contract_type": "dpa",
        "category": "data_deletion",
        "term_name": "deletion_timeline",
        "acceptable_values": {
            "type": "range",
            "max": 90,
            "preferred": 30,
            "unit": "days"
        },
        "violation_severity": "yellow_flag",
        "description": "Data deletion must occur within 90 days of termination",
        "rationale": "Prolonged retention after termination violates data minimization principles",
        "recommendation": "Require deletion within 30 days, maximum 90 days"
    },

    # ========== ALL CONTRACT TYPES ==========
    {
        "contract_type": "all",
        "category": "auto_renewal",
        "term_name": "auto_renewal_allowed",
        "acceptable_values": {
            "type": "boolean",
            "allowed": False,
            "exception_conditions": ["90+ day notice required", "Annual renewal only"]
        },
        "violation_severity": "yellow_flag",
        "description": "Auto-renewal clauses require careful review",
        "rationale": "Auto-renewal can lead to unintended contract extensions and missed opportunities to renegotiate",
        "recommendation": "Remove auto-renewal or ensure 90+ day notice window for non-renewal"
    },
    {
        "contract_type": "all",
        "category": "governing_law",
        "term_name": "favorable_jurisdiction",
        "acceptable_values": {
            "type": "enum",
            "preferred": ["Delaware", "New York", "California", "Company's home state"]
        },
        "violation_severity": "info",
        "description": "Prefer governing law in Delaware, NY, CA, or company's home state",
        "rationale": "Familiar jurisdictions with predictable commercial law reduce legal uncertainty",
        "recommendation": "Negotiate for company's home state or established commercial law jurisdiction"
    },
    {
        "contract_type": "all",
        "category": "dispute_resolution",
        "term_name": "arbitration_prohibition",
        "acceptable_values": {
            "type": "boolean",
            "allowed": False,
            "description": "Avoid mandatory arbitration where possible"
        },
        "violation_severity": "yellow_flag",
        "description": "Mandatory arbitration limits legal options",
        "rationale": "Arbitration can be expensive, lacks appeal rights, and limits discovery",
        "recommendation": "Prefer litigation or optional mediation, avoid mandatory arbitration"
    },
    {
        "contract_type": "all",
        "category": "assignment",
        "term_name": "counterparty_assignment_restriction",
        "acceptable_values": {
            "type": "enum",
            "required": "Requires consent" or "Prohibited to competitors"
        },
        "violation_severity": "yellow_flag",
        "description": "Counterparty should not freely assign contract without consent",
        "rationale": "Assignment could transfer obligations to unfavorable or unqualified party",
        "recommendation": "Require written consent for assignment, especially to competitors"
    },
    {
        "contract_type": "all",
        "category": "force_majeure",
        "term_name": "pandemic_coverage",
        "acceptable_values": {
            "type": "boolean",
            "required": True,
            "description": "Force majeure should explicitly cover pandemics/epidemics"
        },
        "violation_severity": "info",
        "description": "Force majeure should explicitly include pandemics",
        "rationale": "COVID-19 demonstrated need for explicit pandemic coverage",
        "recommendation": "Include pandemics, epidemics, and public health emergencies in force majeure"
    },
    {
        "contract_type": "all",
        "category": "entire_agreement",
        "term_name": "integration_clause",
        "acceptable_values": {
            "type": "boolean",
            "required": True
        },
        "violation_severity": "info",
        "description": "Should include entire agreement/integration clause",
        "rationale": "Integration clause prevents reliance on prior negotiations or side agreements",
        "recommendation": "Include standard entire agreement clause for clarity"
    },
    {
        "contract_type": "all",
        "category": "amendments",
        "term_name": "written_amendments_only",
        "acceptable_values": {
            "type": "boolean",
            "required": True
        },
        "violation_severity": "info",
        "description": "Amendments should require written agreement by both parties",
        "rationale": "Prevents unintended contract modifications via email or oral agreements",
        "recommendation": "Require written amendments signed by authorized representatives"
    },
    {
        "contract_type": "all",
        "category": "confidentiality",
        "term_name": "mutual_confidentiality",
        "acceptable_values": {
            "type": "boolean",
            "preferred": True
        },
        "violation_severity": "info",
        "description": "Confidentiality obligations should be mutual",
        "rationale": "Both parties typically share confidential information",
        "recommendation": "Include mutual confidentiality provisions unless clearly one-way"
    },
    {
        "contract_type": "all",
        "category": "notice",
        "term_name": "email_notice_permitted",
        "acceptable_values": {
            "type": "boolean",
            "preferred": True,
            "description": "Email should be acceptable for routine notices"
        },
        "violation_severity": "info",
        "description": "Email should be permitted for routine contract notices",
        "rationale": "Email notice is faster and more efficient than mail for routine matters",
        "recommendation": "Allow email for routine notices, require certified mail for termination"
    }
]


def seed_legal_standards():
    """Seed the database with default legal standards"""
    logger.info(f"\n🌱 Seeding legal standards...")
    logger.info(f"   Total standards to insert: {len(DEFAULT_STANDARDS)}\n")

    inserted = 0
    updated = 0
    skipped = 0

    for standard in DEFAULT_STANDARDS:
        try:
            # Try to insert
            result = supabase.table('legal_standards').insert({
                **standard,
                'client_id': None  # NULL = default for all clients
            }).execute()

            inserted += 1
            logger.info(f"   ✅ Inserted: {standard['contract_type']:12} | {standard['category']:20} | {standard['term_name']}")

        except Exception as e:
            error_msg = str(e)
            if 'duplicate key' in error_msg.lower() or 'unique constraint' in error_msg.lower():
                # Standard already exists, update it
                try:
                    result = supabase.table('legal_standards')\
                        .update(standard)\
                        .eq('contract_type', standard['contract_type'])\
                        .eq('category', standard['category'])\
                        .eq('term_name', standard['term_name'])\
                        .is_('client_id', 'null')\
                        .execute()

                    updated += 1
                    logger.info(f"   🔄 Updated: {standard['contract_type']:12} | {standard['category']:20} | {standard['term_name']}")
                except Exception as update_error:
                    skipped += 1
                    logger.error(f"   ❌ Failed to update: {standard['term_name']} - {update_error}")
            else:
                skipped += 1
                logger.error(f"   ❌ Failed: {standard['term_name']} - {error_msg}")

    logger.info(f"\n📊 Seeding complete:")
    logger.info(f"   ✅ Inserted: {inserted}")
    logger.info(f"   🔄 Updated:  {updated}")
    logger.info(f"   ❌ Skipped:  {skipped}")
    logger.info(f"   📈 Total:    {inserted + updated} standards active\n")


if __name__ == "__main__":
    seed_legal_standards()
