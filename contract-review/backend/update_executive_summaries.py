#!/usr/bin/env python3
"""
Update all system instruction XML files to use new executive summary format
"""

import re
from pathlib import Path

# Define the new executive summary format for each contract type
NEW_FORMATS = {
    "VENDOR": '''  "executive_summary": {
    "contract_overview": "One sentence describing the vendor relationship, services, and financial terms",
    "key_findings": [
      "First critical finding (use prefix: HIGH RISK/MEDIUM RISK/LOW RISK/POSITIVE as appropriate)",
      "Second critical finding with specific impact",
      "Third critical finding if applicable (limit to 3-4 most important items)"
    ],
    "recommendation": "Clear action: APPROVE / NEGOTIATE [specific items] / REJECT / SEEK LEGAL REVIEW"
  },''',

    "CUSTOMER": '''  "executive_summary": {
    "contract_overview": "One sentence describing the customer relationship, our deliverables, and revenue",
    "key_findings": [
      "First critical finding (use prefix: HIGH RISK/MEDIUM RISK/LOW RISK/POSITIVE as appropriate)",
      "Second critical finding with specific impact on our liability or obligations",
      "Third critical finding if applicable (limit to 3-4 most important items)"
    ],
    "recommendation": "Clear action: APPROVE / NEGOTIATE [specific items] / REJECT / SEEK LEGAL REVIEW"
  },''',

    "EMPLOYMENT": '''  "executive_summary": {
    "contract_overview": "One sentence describing the employment role, level, and key compensation",
    "key_findings": [
      "First critical finding (use prefix: HIGH RISK/MEDIUM RISK/LOW RISK/POSITIVE as appropriate)",
      "Second critical finding with specific employment law or company risk",
      "Third critical finding if applicable (limit to 3-4 most important items)"
    ],
    "recommendation": "Clear action: APPROVE / NEGOTIATE [specific items] / REJECT / SEEK LEGAL/HR REVIEW"
  },''',

    "DPA": '''  "executive_summary": {
    "contract_overview": "One sentence describing the data processing relationship and data types",
    "key_findings": [
      "First critical finding (use prefix: HIGH RISK/MEDIUM RISK/LOW RISK/COMPLIANCE ISSUE/POSITIVE as appropriate)",
      "Second critical finding with specific GDPR/privacy risk",
      "Third critical finding if applicable (limit to 3-4 most important compliance items)"
    ],
    "recommendation": "Clear action: APPROVE / NEGOTIATE [specific items] / REJECT / SEEK LEGAL/DPO REVIEW"
  },''',

    "GENERAL": '''  "executive_summary": {
    "contract_overview": "One sentence describing the contract type, parties, and purpose",
    "key_findings": [
      "First critical finding (use prefix: HIGH RISK/MEDIUM RISK/LOW RISK/POSITIVE as appropriate)",
      "Second critical finding with specific legal or business risk",
      "Third critical finding if applicable (limit to 3-4 most important items)"
    ],
    "recommendation": "Clear action: APPROVE / NEGOTIATE [specific items] / REJECT / SEEK LEGAL REVIEW"
  },''',

    "OTHER": '''  "executive_summary": {
    "contract_overview": "One sentence describing the contract type, parties, and purpose",
    "key_findings": [
      "First critical finding (use prefix: HIGH RISK/MEDIUM RISK/LOW RISK/POSITIVE as appropriate)",
      "Second critical finding with specific legal or business risk",
      "Third critical finding if applicable (limit to 3-4 most important items)"
    ],
    "recommendation": "Clear action: APPROVE / NEGOTIATE [specific items] / REJECT / SEEK LEGAL REVIEW"
  },'''
}

# Old pattern to match (paragraph format)
OLD_PATTERN = re.compile(
    r'  "executive_summary": "[^"]+",\n',
    re.MULTILINE
)

def update_xml_file(file_path: Path, contract_type: str):
    """Update a single XML file with new executive summary format"""
    print(f"Updating {file_path.name}...")

    # Read the file
    content = file_path.read_text()

    # Get the new format for this contract type
    new_format = NEW_FORMATS[contract_type]

    # Replace the old format with new format
    updated_content = OLD_PATTERN.sub(new_format + '\n', content)

    # Check if we actually made a change
    if content == updated_content:
        print(f"  WARNING: No changes made to {file_path.name}")
        return False

    # Write back
    file_path.write_text(updated_content)
    print(f"  ✓ Updated {file_path.name}")
    return True

def main():
    """Update all system instruction XML files"""
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
            if update_xml_file(file_path, contract_type):
                updated_count += 1
        else:
            print(f"WARNING: {filename} not found")

    print(f"\n✓ Updated {updated_count} files")

if __name__ == "__main__":
    main()
