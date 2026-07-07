# Legal Standards - User-Friendly Interface

This directory contains a user-friendly interface for managing legal standards without requiring JSON knowledge.

## Overview

Legal standards define the compliance criteria that contracts are evaluated against during automated analysis. The backend stores these as JSON, but the frontend provides an intuitive form-based interface.

## Components

### AcceptableValuesInput.tsx
Dynamic form builder that converts between user-friendly inputs and JSON storage format.

**Features:**
- 9 pre-built templates for common standards (liability, payment terms, data privacy, etc.)
- Auto-detects template based on category/term name
- Template selector with descriptions
- Form view (user-friendly) vs JSON view (advanced users)
- Auto-populates category, term name, and recommendation when template is selected

**Templates Available:**
1. **Liability Cap** - Min/max liability amounts with currency selection
2. **Payment Terms** - Payment days, methods, advance payment requirements
3. **Termination Notice Period** - Min/max notice days, termination for convenience
4. **Indemnification** - Mutual indemnification, third-party claims, IP coverage
5. **Data Privacy & Security** - GDPR/CCPA compliance, breach notification, jurisdictions
6. **IP Ownership** - Work for hire, background IP, license types
7. **Confidentiality Terms** - Confidentiality period, material handling, exceptions
8. **Insurance Requirements** - General/professional liability minimums, certificates
9. **Custom Standard** - Flexible free-form fields

### AcceptableValuesDisplay.tsx
Displays acceptable values in human-readable format in the table.

**Features:**
- Smart formatting based on field types (currency, dates, arrays, booleans)
- Compact mode for table display (shows summary)
- Full mode for detailed view
- Pattern detection for common standard types

**Examples:**
- `{"min_amount": 0, "max_amount": 1000000, "currency": "USD"}` → "$0 - $1,000,000"
- `{"max_payment_days": 30}` → "Net 30 days"
- `{"min_notice_days": 30, "max_notice_days": 90}` → "30-90 days notice"

## Usage

### Creating a New Standard

1. Click "Add Standard" button
2. Select a template from the dropdown (or choose "Custom Standard")
3. Fill in the user-friendly form fields
4. Category, term name, and recommendation are auto-populated
5. Click "Create Standard"

### Editing an Existing Standard

1. Click "Edit" on any standard
2. Form fields are populated from the JSON data
3. Modify values using the form
4. Switch to "JSON View" for advanced editing if needed
5. Click "Update Standard"

## Extensibility

### Adding New Templates

To add a new template, edit `AcceptableValuesInput.tsx` and add to `STANDARD_TEMPLATES`:

```typescript
{
  id: 'my_template',
  name: 'My Template Name',
  description: 'What this template is for',
  category: 'Default Category',
  fields: [
    {
      key: 'my_field',
      label: 'My Field Label',
      type: 'number', // text, number, select, boolean, array, date, currency
      required: true,
      placeholder: '100',
      helperText: 'Help text shown below field',
      defaultValue: 100,
      min: 0,
      max: 1000
    },
    // ... more fields
  ],
  recommendationTemplate: 'Ensure {my_field} meets requirements'
}
```

### Supported Field Types

- `text` - Single-line text input
- `number` - Numeric input with optional min/max
- `currency` - Numeric input formatted as currency
- `select` - Dropdown with predefined options
- `boolean` - Checkbox
- `array` - Comma-separated list input
- `date` - Date picker

### Adding New Display Patterns

To add custom display logic for new patterns, edit `AcceptableValuesDisplay.tsx`:

```typescript
// In generateSummary() function:
if (value.my_custom_field !== undefined) {
  return `Custom: ${value.my_custom_field}`;
}
```

## Backend Integration

The components seamlessly convert between user-friendly forms and JSON:

**User Input:**
- Minimum Amount: 1000000
- Maximum Amount: 5000000
- Currency: USD

**Stored in Database:**
```json
{
  "min_amount": 1000000,
  "max_amount": 5000000,
  "currency": "USD"
}
```

**Displayed in Table:**
"$1,000,000 - $5,000,000"

## Migration from Old Interface

Existing legal standards with raw JSON will continue to work:
- Display component handles any JSON structure
- Edit form allows switching to JSON view for manual editing
- No database migration required

## Best Practices

1. **Use Templates** - Start with a template when possible
2. **Descriptive Names** - Use clear category and term names
3. **Helper Text** - Templates include built-in help text
4. **Test Display** - Check how values appear in the table
5. **JSON Fallback** - Use JSON view for complex custom structures
