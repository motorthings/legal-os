# Legal Standards Value Types Guide

This document explains all supported value types for legal standards and how to use them.

## Overview

Legal standards use JSON to define acceptable values, but the UI provides user-friendly templates that handle the JSON conversion automatically. You can define:

- **Numeric ranges** with min/max/preferred values
- **Lists of allowed values** (comma-separated)
- **Required clauses** that must be present
- **Boolean flags**
- **Complex nested objects** for multi-tier requirements

## Value Type Patterns

### 1. Range with Preferred Value

**Use when:** You need min/max limits with a preferred target value.

**Template:** "Range with Preferred Value"

**User Input:**
- Minimum Value: 0
- Maximum Value: 60
- Preferred Value: 30
- Unit: days

**Stored as JSON:**
```json
{
  "type": "range",
  "min": 0,
  "max": 60,
  "preferred": 30,
  "unit": "days"
}
```

**Displayed in Table:** "0-60 days (preferred: 30)"

**Examples:**
- Payment terms: Net 0-60 days, preferred 30
- Notice periods: 30-90 days notice
- Warranty periods: 3-24 months
- Late payment penalties: 0-18% annually

---

### 2. Allowed Values List

**Use when:** Only specific values from a predefined list are acceptable.

**Template:** "Allowed Values List"

**User Input:**
- Allowed Values: gross_negligence, willful_misconduct, ip_infringement, data_breach
- Maximum Number of Items: 5

**Stored as JSON:**
```json
{
  "type": "list",
  "allowed": ["gross_negligence", "willful_misconduct", "ip_infringement", "data_breach"],
  "max_items": 5
}
```

**Displayed in Table:** "Allowed: gross_negligence, willful_misconduct, ip_infringement, data_breach (max 5)"

**Examples:**
- Liability cap exceptions
- Acceptable payment methods
- Permitted disclosure exceptions
- Termination causes

---

### 3. Required Items from List

**Use when:** Contract must include specific items, may include additional ones.

**Template:** "Required Items from List" or "Security Certifications"

**User Input:**
- Required Items: SOC2, ISO27001
- Preferred Additional Items: GDPR, HIPAA, PCI-DSS

**Stored as JSON:**
```json
{
  "type": "list",
  "required": ["SOC2", "ISO27001"],
  "preferred": ["GDPR", "HIPAA", "PCI-DSS"]
}
```

**Displayed in Table:** "Required: SOC2, ISO27001 | Preferred: GDPR, HIPAA, PCI-DSS"

**Examples:**
- Security certifications
- Required insurance types
- Compliance frameworks
- Data processing lawful bases

---

### 4. Required Clauses

**Use when:** Contract must include specific clauses or language.

**Template:** "Required Clauses"

**User Input:**
- Required Clauses: customer_owns_data, export_rights, deletion_rights

**Stored as JSON:**
```json
{
  "type": "required_clause",
  "must_include": ["customer_owns_data", "export_rights", "deletion_rights"]
}
```

**Displayed in Table:** "Must include: customer_owns_data, export_rights, deletion_rights"

**Examples:**
- Data ownership clauses
- IP indemnification requirements
- Warranty provisions
- Termination rights

---

### 5. Boolean Requirements

**Use when:** Something is simply required or not required.

**User Input:**
- Required: Yes/No checkbox

**Stored as JSON:**
```json
{
  "type": "boolean",
  "required": true
}
```

**Displayed in Table:** "Required: Yes"

**Examples:**
- Mutual indemnification required
- Consequential damages exclusion required
- At-will employment status
- Work for hire assignment

---

### 6. Multi-Tier Insurance Requirements

**Use when:** Different insurance types each have their own min/preferred amounts.

**Template:** "Multi-Tier Insurance Requirements"

**User Input:**
- General Liability Minimum: 1,000,000
- General Liability Preferred: 2,000,000
- Cyber Liability Minimum: 1,000,000
- Cyber Liability Preferred: 5,000,000

**Stored as JSON:**
```json
{
  "type": "object",
  "general_liability": {
    "min": 1000000,
    "preferred": 2000000
  },
  "cyber_liability": {
    "min": 1000000,
    "preferred": 5000000
  }
}
```

**Displayed in Table:** "GL: $1,000,000 | Cyber: $1,000,000"

**Examples:**
- Insurance requirements (GL, E&O, Cyber, etc.)
- Multi-tier service credits
- Tiered support response times

---

## How Claude Interprets These Values

When analyzing contracts, Claude receives legal standards as XML:

```xml
<legal_standards>
  <standard severity="red_flag">
    <category>payment_terms</category>
    <term>net_days</term>
    <description>Standard payment terms in days</description>
    <acceptable_values>{"type": "range", "min": 0, "max": 60, "preferred": 30}</acceptable_values>
    <recommendation>Payment terms should not exceed Net 60. Industry standard is Net 30.</recommendation>
  </standard>

  <standard severity="red_flag">
    <category>security</category>
    <term>security_standards</term>
    <description>Required security certifications</description>
    <acceptable_values>{"type": "list", "required": ["SOC2", "ISO27001"], "preferred": ["GDPR", "HIPAA"]}</acceptable_values>
    <recommendation>Vendor must maintain SOC 2 Type II and ISO 27001 certifications at minimum.</recommendation>
  </standard>
</legal_standards>
```

Claude:
1. Extracts the relevant terms from the contract
2. Compares them against the acceptable_values criteria
3. Generates red/yellow flags when values fall outside acceptable ranges or missing required items
4. Includes the recommendation in the flag description

---

## Examples from Production Standards

### Payment Terms (Range)
```json
{
  "type": "range",
  "min": 0,
  "max": 60,
  "preferred": 30
}
```
**Triggers flag if:** Payment terms > 60 days

### Liability Cap Exceptions (Allowed List)
```json
{
  "type": "list",
  "allowed": ["gross_negligence", "willful_misconduct", "ip_infringement", "data_breach", "confidentiality"],
  "max_exceptions": 5
}
```
**Triggers flag if:** More than 5 exceptions OR exceptions not in allowed list

### Security Standards (Required List)
```json
{
  "type": "list",
  "required": ["SOC2", "ISO27001"],
  "preferred": ["SOC2", "ISO27001", "GDPR", "HIPAA"]
}
```
**Triggers flag if:** Missing SOC2 or ISO27001

### Customer Data Ownership (Required Clause)
```json
{
  "type": "required_clause",
  "must_include": ["customer_owns", "export_rights", "deletion_rights"]
}
```
**Triggers flag if:** Any required clause is missing

### Mutual Indemnification (Boolean)
```json
{
  "type": "boolean",
  "required": true
}
```
**Triggers flag if:** Mutual indemnification is not present

### Vendor Insurance (Multi-Tier Object)
```json
{
  "type": "object",
  "general_liability": {"min": 1000000, "preferred": 2000000},
  "cyber_liability": {"min": 1000000, "preferred": 5000000}
}
```
**Triggers flag if:** GL < $1M or Cyber < $1M

---

## Comma-Separated Lists

**Yes, you can use comma-separated lists!**

The `array` field type automatically handles comma-separated input:

**User enters:** `SOC2, ISO27001, GDPR, HIPAA`

**System stores:** `["SOC2", "ISO27001", "GDPR", "HIPAA"]`

**Claude receives:** `{"type": "list", "required": ["SOC2", "ISO27001", "GDPR", "HIPAA"]}`

This works for:
- Allowed values lists
- Required items lists
- Required clauses
- Acceptable jurisdictions
- Payment methods
- Any array field in templates

---

## Creating Custom Value Types

For advanced users who need custom structures not covered by templates:

1. Select "Custom Standard" template
2. Click "JSON View (Advanced)" toggle
3. Enter any valid JSON structure:

```json
{
  "type": "custom",
  "my_custom_field": "value",
  "nested": {
    "field": "value"
  },
  "array_field": ["item1", "item2"]
}
```

Claude is smart enough to interpret custom JSON structures as long as they're logically structured.

---

## Best Practices

1. **Use Templates First** - Start with a pre-built template when possible
2. **Be Specific** - More specific criteria = better flag accuracy
3. **Add Context** - Use the description field to explain why this matters
4. **Test Display** - Check how values appear in the table
5. **Use Preferred Values** - Help Claude distinguish "acceptable" from "ideal"
6. **Comma-Separated Lists** - Easier than typing JSON arrays
7. **Nested Objects** - Use for multi-tier requirements (insurance, SLAs, etc.)

---

## Troubleshooting

**Q: My comma-separated list isn't working**
A: Make sure you're using an `array` field type in the template. Regular text fields don't auto-convert.

**Q: How do I create a range of currencies?**
A: Use the "Liability Cap" or similar currency template, or create a custom object with nested min/max.

**Q: Can I combine multiple patterns?**
A: Yes! Use the Custom Standard template and JSON view to create complex nested structures.

**Q: My changes aren't reflected in contract analysis**
A: Standards are loaded when contracts are processed. Re-process existing contracts to apply new standards.
