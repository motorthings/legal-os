#!/usr/bin/env python3
"""
Add comprehensive examples with executive_summary to each system instruction file
"""

from pathlib import Path

# Example for VENDOR contract
VENDOR_EXAMPLE = '''
		<example id="vendor_complete_analysis_example">
			<title>Complete Analysis Example with Executive Summary</title>

			<contract_clause>
				Vendor Services Agreement between Acme Corp (Vendor) and Client for cloud infrastructure services. Initial term of 3 years with automatic renewal. Annual fee of $500,000. Service level of 99.9% uptime with service credits. Vendor liability capped at 3 months of fees. Termination only for material breach with 30-day cure.
			</contract_clause>

			<analysis_output><![CDATA[
{
  "executive_summary": {
    "contract_overview": "3-year vendor services agreement with Acme Corp for cloud infrastructure at $500K annually",
    "key_findings": [
      "HIGH RISK: No termination for convenience - locked into full 3-year term with only material breach as exit option",
      "HIGH RISK: Liability cap of only 3 months fees ($125K) inadequate for potential service failure damages",
      "POSITIVE: Strong 99.9% uptime SLA with service credits and termination rights for repeated failures"
    ],
    "recommendation": "NEGOTIATE before signing - add termination for convenience after Year 1, increase liability cap to minimum 12 months of fees"
  },
  "risk_assessment": {
    "overall_risk_level": "high",
    "risk_score": 75
  }
}
			]]></analysis_output>

			<reasoning>
				This example demonstrates the new executive summary format with:
				1. Contract overview providing context at a glance
				2. Key findings as bulleted items with risk level prefixes
				3. Clear, actionable recommendation
			</reasoning>
		</example>
'''

# Example for CUSTOMER contract
CUSTOMER_EXAMPLE = '''
		<example id="customer_complete_analysis_example">
			<title>Complete Analysis Example with Executive Summary</title>

			<contract_clause>
				Professional Services Agreement where we provide consulting services to BigCo for $2M over 12 months. Deliverables include system implementation and training. We warrant work will be performed in workmanlike manner. Liability limited to fees paid. Customer can terminate for convenience with 30 days notice.
			</contract_clause>

			<analysis_output><![CDATA[
{
  "executive_summary": {
    "contract_overview": "12-month professional services engagement with BigCo for system implementation and training ($2M revenue)",
    "key_findings": [
      "HIGH RISK: Open-ended workmanlike manner warranty could expose us to unlimited rework obligations",
      "MEDIUM RISK: Customer can terminate for convenience with only 30 days notice, putting $2M revenue at risk",
      "POSITIVE: Liability cap limits our exposure to fees paid ($2M maximum)"
    ],
    "recommendation": "NEGOTIATE warranty language - define specific acceptance criteria and limit warranty period to 90 days post-delivery"
  },
  "risk_assessment": {
    "overall_risk_level": "medium",
    "risk_score": 60
  }
}
			]]></analysis_output>

			<reasoning>
				This example demonstrates how to analyze customer contracts from our perspective as the service provider, highlighting revenue risk and liability exposure.
			</reasoning>
		</example>
'''

# Example for EMPLOYMENT contract
EMPLOYMENT_EXAMPLE = '''
		<example id="employment_complete_analysis_example">
			<title>Complete Analysis Example with Executive Summary</title>

			<contract_clause>
				Employment Agreement for Senior Engineering Manager role at $180K base salary plus 20% target bonus. Includes 100,000 stock options vesting over 4 years. Non-compete for 12 months post-termination covering entire software industry. IP assignment clause assigns all inventions to company.
			</contract_clause>

			<analysis_output><![CDATA[
{
  "executive_summary": {
    "contract_overview": "Senior Engineering Manager employment agreement with $180K salary, $36K target bonus, 100K options over 4 years",
    "key_findings": [
      "HIGH RISK: 12-month non-compete covering entire software industry likely unenforceable and exposes company to legal challenges",
      "MEDIUM RISK: Unlimited IP assignment including off-hours inventions may violate state law protections for employee IP rights",
      "POSITIVE: Competitive compensation package with standard vesting schedule aligns with market rates"
    ],
    "recommendation": "REVISE before offering - narrow non-compete to specific competitors/geography, add IP assignment carve-outs per state law"
  },
  "risk_assessment": {
    "overall_risk_level": "high",
    "risk_score": 70
  }
}
			]]></analysis_output>

			<reasoning>
				Employment contracts require careful attention to enforceability under employment law. Overly broad restrictions can expose the company to legal liability.
			</reasoning>
		</example>
'''

# Example for DPA contract
DPA_EXAMPLE = '''
		<example id="dpa_complete_analysis_example">
			<title>Complete Analysis Example with Executive Summary</title>

			<contract_clause>
				Data Processing Agreement where we act as Processor for EU customer personal data including names, emails, purchase history. Sub-processors allowed with notification. Security measures include encryption and access controls. Data retention until customer deletion request. Processor fee of €50K annually.
			</contract_clause>

			<analysis_output><![CDATA[
{
  "executive_summary": {
    "contract_overview": "GDPR Data Processing Agreement as Processor for EU customer handling names, emails, and purchase history",
    "key_findings": [
      "COMPLIANCE ISSUE: Missing Standard Contractual Clauses (SCCs) required for transfers to US - GDPR violation risk",
      "HIGH RISK: Unlimited liability for GDPR breaches could expose us to millions in regulatory fines",
      "POSITIVE: Security measures (encryption, access controls) meet GDPR Article 32 technical requirements"
    ],
    "recommendation": "DO NOT SIGN without adding EU SCCs and negotiating liability cap for non-willful violations"
  },
  "risk_assessment": {
    "overall_risk_level": "high",
    "risk_score": 85
  }
}
			]]></analysis_output>

			<reasoning>
				DPAs require strict GDPR compliance. Missing SCCs for EU-US transfers is a showstopper that must be resolved before signing.
			</reasoning>
		</example>
'''

# Example for GENERAL contract
GENERAL_EXAMPLE = '''
		<example id="general_complete_analysis_example">
			<title>Complete Analysis Example with Executive Summary</title>

			<contract_clause>
				Partnership Agreement between our company and Tech Innovations Inc for joint development of AI software. Cost sharing 50/50 up to $1M each. IP jointly owned. 5-year term with no early termination except for material breach. Dispute resolution through binding arbitration.
			</contract_clause>

			<analysis_output><![CDATA[
{
  "executive_summary": {
    "contract_overview": "5-year partnership with Tech Innovations Inc for joint AI development with 50/50 cost sharing ($1M each)",
    "key_findings": [
      "HIGH RISK: Joint IP ownership with no clear commercialization rights could create gridlock and prevent product launch",
      "HIGH RISK: 5-year commitment with no termination for convenience locks us in even if partnership fails",
      "MEDIUM RISK: Binding arbitration waives our right to court litigation, potentially limiting legal remedies"
    ],
    "recommendation": "NEGOTIATE IP ownership split or license-back rights, add termination for convenience after Year 2"
  },
  "risk_assessment": {
    "overall_risk_level": "high",
    "risk_score": 78
  }
}
			]]></analysis_output>

			<reasoning>
				Partnership agreements require clear IP ownership and exit rights. Joint ownership without usage rights creates significant business risk.
			</reasoning>
		</example>
'''

# Example for OTHER contract
OTHER_EXAMPLE = '''
		<example id="other_complete_analysis_example">
			<title>Complete Analysis Example with Executive Summary</title>

			<contract_clause>
				Memorandum of Understanding between parties to explore potential business collaboration. Non-binding except for confidentiality obligations. Either party may terminate at will. Confidential information protected for 3 years. No financial commitments.
			</contract_clause>

			<analysis_output><![CDATA[
{
  "executive_summary": {
    "contract_overview": "Non-binding MOU for exploring business collaboration with confidentiality obligations",
    "key_findings": [
      "LOW RISK: Non-binding nature means no enforceable commitments beyond confidentiality",
      "POSITIVE: Either party can terminate at will, providing maximum flexibility",
      "POSITIVE: Standard 3-year confidentiality protection with no unusual restrictions"
    ],
    "recommendation": "APPROVE - low risk exploratory agreement with standard confidentiality terms"
  },
  "risk_assessment": {
    "overall_risk_level": "low",
    "risk_score": 20
  }
}
			]]></analysis_output>

			<reasoning>
				MOUs are typically low-risk as they create minimal binding obligations. This example shows how to communicate low-risk findings clearly.
			</reasoning>
		</example>
'''

EXAMPLES = {
    "VENDOR": VENDOR_EXAMPLE,
    "CUSTOMER": CUSTOMER_EXAMPLE,
    "EMPLOYMENT": EMPLOYMENT_EXAMPLE,
    "DPA": DPA_EXAMPLE,
    "GENERAL": GENERAL_EXAMPLE,
    "OTHER": OTHER_EXAMPLE,
}

def add_example_to_file(file_path: Path, contract_type: str):
    """Add executive summary example to a system instruction file"""
    print(f"Adding example to {file_path.name}...")

    content = file_path.read_text()

    # Find the end of examples section (before </examples>)
    if '</examples>' not in content:
        print(f"  WARNING: No </examples> tag found in {file_path.name}")
        return False

    # Check if example already exists
    if 'complete_analysis_example' in content:
        print(f"  Skipping - example already exists in {file_path.name}")
        return False

    # Insert the new example before </examples>
    example = EXAMPLES[contract_type]
    updated_content = content.replace('</examples>', example + '\n\t</examples>')

    # Write back
    file_path.write_text(updated_content)
    print(f"  ✓ Added example to {file_path.name}")
    return True

def main():
    """Add examples to all system instruction XML files"""
    instructions_dir = Path("system_instructions")

    if not instructions_dir.exists():
        print(f"ERROR: {instructions_dir} not found!")
        return

    # Map file names to contract types
    files_to_update = {
        "VENDOR_CONTRACT_SYSTEM_INSTRUCTIONS.xml": "VENDOR",
        "CUSTOMER_CONTRACT_SYSTEM_INSTRUCTIONS.xml": "CUSTOMER",
        "EMPLOYMENT_CONTRACT_SYSTEM_INSTRUCTIONS.xml": "EMPLOYMENT",
        "DPA_CONTRACT_SYSTEM_INSTRUCTIONS.xml": "DPA",
        "GENERAL_CONTRACT_SYSTEM_INSTRUCTIONS.xml": "GENERAL",
        "OTHER_CONTRACT_SYSTEM_INSTRUCTIONS.xml": "OTHER",
    }

    updated_count = 0
    for filename, contract_type in files_to_update.items():
        file_path = instructions_dir / filename
        if file_path.exists():
            if add_example_to_file(file_path, contract_type):
                updated_count += 1
        else:
            print(f"WARNING: {filename} not found")

    print(f"\n✓ Added examples to {updated_count} files")

if __name__ == "__main__":
    main()
