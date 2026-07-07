'use client';

import { useState, useEffect } from 'react';

/**
 * Field definition for building dynamic forms
 */
export interface FieldDefinition {
  key: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'boolean' | 'array' | 'date' | 'currency';
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  helperText?: string;
  defaultValue?: any;
}

/**
 * Template definition for pre-configured standard types
 */
export interface StandardTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  fields: FieldDefinition[];
  recommendationTemplate?: string;
}

/**
 * Built-in templates for common standard types
 */
export const STANDARD_TEMPLATES: StandardTemplate[] = [
  {
    id: 'liability_cap',
    name: 'Liability Cap',
    description: 'Limits on liability amounts',
    category: 'Liability',
    fields: [
      {
        key: 'min_amount',
        label: 'Minimum Acceptable Amount',
        type: 'currency',
        required: true,
        placeholder: '0',
        helperText: 'Minimum liability cap amount',
        defaultValue: 0
      },
      {
        key: 'max_amount',
        label: 'Maximum Acceptable Amount',
        type: 'currency',
        required: true,
        placeholder: '1000000',
        helperText: 'Maximum liability cap amount',
        defaultValue: 1000000
      },
      {
        key: 'currency',
        label: 'Currency',
        type: 'select',
        required: true,
        options: [
          { value: 'USD', label: 'USD - US Dollar' },
          { value: 'EUR', label: 'EUR - Euro' },
          { value: 'GBP', label: 'GBP - British Pound' },
          { value: 'CAD', label: 'CAD - Canadian Dollar' },
          { value: 'AUD', label: 'AUD - Australian Dollar' }
        ],
        defaultValue: 'USD'
      },
      {
        key: 'unlimited_acceptable',
        label: 'Unlimited Liability Acceptable',
        type: 'boolean',
        required: false,
        helperText: 'Check if unlimited liability is acceptable',
        defaultValue: false
      }
    ],
    recommendationTemplate: 'Ensure liability is capped between {min_amount} and {max_amount} {currency}'
  },
  {
    id: 'payment_terms',
    name: 'Payment Terms',
    description: 'Payment timing and methods',
    category: 'Payment Terms',
    fields: [
      {
        key: 'max_payment_days',
        label: 'Maximum Payment Days',
        type: 'number',
        required: true,
        placeholder: '30',
        helperText: 'Maximum acceptable days for payment (e.g., Net 30)',
        defaultValue: 30,
        min: 0,
        max: 365
      },
      {
        key: 'acceptable_methods',
        label: 'Acceptable Payment Methods',
        type: 'array',
        required: false,
        helperText: 'Comma-separated list (e.g., ACH, Wire Transfer, Check)',
        defaultValue: ['ACH', 'Wire Transfer', 'Check']
      },
      {
        key: 'advance_payment_required',
        label: 'Advance Payment Required',
        type: 'boolean',
        required: false,
        helperText: 'Check if advance payment is required',
        defaultValue: false
      },
      {
        key: 'late_fee_acceptable',
        label: 'Late Fees Acceptable',
        type: 'boolean',
        required: false,
        helperText: 'Check if late fees are acceptable',
        defaultValue: true
      }
    ],
    recommendationTemplate: 'Payment terms should not exceed {max_payment_days} days'
  },
  {
    id: 'termination_notice',
    name: 'Termination Notice Period',
    description: 'Required notice for contract termination',
    category: 'Termination',
    fields: [
      {
        key: 'min_notice_days',
        label: 'Minimum Notice Days',
        type: 'number',
        required: true,
        placeholder: '30',
        helperText: 'Minimum acceptable notice period in days',
        defaultValue: 30,
        min: 0,
        max: 365
      },
      {
        key: 'max_notice_days',
        label: 'Maximum Notice Days',
        type: 'number',
        required: true,
        placeholder: '90',
        helperText: 'Maximum acceptable notice period in days',
        defaultValue: 90,
        min: 0,
        max: 365
      },
      {
        key: 'termination_for_convenience',
        label: 'Termination for Convenience Allowed',
        type: 'boolean',
        required: false,
        helperText: 'Check if termination without cause is acceptable',
        defaultValue: true
      }
    ],
    recommendationTemplate: 'Termination notice should be between {min_notice_days} and {max_notice_days} days'
  },
  {
    id: 'indemnification',
    name: 'Indemnification',
    description: 'Indemnification requirements',
    category: 'Liability',
    fields: [
      {
        key: 'mutual_indemnification',
        label: 'Mutual Indemnification Required',
        type: 'boolean',
        required: true,
        helperText: 'Both parties must indemnify each other',
        defaultValue: true
      },
      {
        key: 'third_party_claims',
        label: 'Third-Party Claims Coverage',
        type: 'boolean',
        required: false,
        helperText: 'Indemnification covers third-party claims',
        defaultValue: true
      },
      {
        key: 'ip_indemnification',
        label: 'IP Indemnification Required',
        type: 'boolean',
        required: false,
        helperText: 'Intellectual property indemnification required',
        defaultValue: true
      }
    ],
    recommendationTemplate: 'Ensure mutual indemnification with third-party claims coverage'
  },
  {
    id: 'data_privacy',
    name: 'Data Privacy & Security',
    description: 'Data handling and privacy requirements',
    category: 'Data Privacy',
    fields: [
      {
        key: 'gdpr_compliance',
        label: 'GDPR Compliance Required',
        type: 'boolean',
        required: false,
        helperText: 'Must comply with GDPR regulations',
        defaultValue: true
      },
      {
        key: 'ccpa_compliance',
        label: 'CCPA Compliance Required',
        type: 'boolean',
        required: false,
        helperText: 'Must comply with CCPA regulations',
        defaultValue: true
      },
      {
        key: 'data_breach_notification_hours',
        label: 'Breach Notification Hours',
        type: 'number',
        required: false,
        placeholder: '72',
        helperText: 'Maximum hours to notify of data breach',
        defaultValue: 72,
        min: 1,
        max: 720
      },
      {
        key: 'acceptable_jurisdictions',
        label: 'Acceptable Data Jurisdictions',
        type: 'array',
        required: false,
        helperText: 'Comma-separated list of acceptable countries/regions',
        defaultValue: ['US', 'EU', 'Canada']
      }
    ],
    recommendationTemplate: 'Ensure GDPR/CCPA compliance with breach notification within {data_breach_notification_hours} hours'
  },
  {
    id: 'ip_ownership',
    name: 'IP Ownership',
    description: 'Intellectual property ownership terms',
    category: 'Intellectual Property',
    fields: [
      {
        key: 'work_for_hire',
        label: 'Work for Hire',
        type: 'boolean',
        required: false,
        helperText: 'Created work belongs to company',
        defaultValue: true
      },
      {
        key: 'background_ip_retained',
        label: 'Background IP Retained',
        type: 'boolean',
        required: false,
        helperText: 'Each party retains their pre-existing IP',
        defaultValue: true
      },
      {
        key: 'license_type',
        label: 'License Type',
        type: 'select',
        required: false,
        options: [
          { value: 'exclusive', label: 'Exclusive' },
          { value: 'non-exclusive', label: 'Non-Exclusive' },
          { value: 'perpetual', label: 'Perpetual' },
          { value: 'limited', label: 'Limited Term' }
        ],
        defaultValue: 'non-exclusive'
      }
    ],
    recommendationTemplate: 'Ensure clear IP ownership with background IP retained by original owner'
  },
  {
    id: 'confidentiality',
    name: 'Confidentiality Terms',
    description: 'Confidentiality and non-disclosure requirements',
    category: 'Confidentiality',
    fields: [
      {
        key: 'confidentiality_period_years',
        label: 'Confidentiality Period (Years)',
        type: 'number',
        required: true,
        placeholder: '5',
        helperText: 'Duration of confidentiality obligation in years',
        defaultValue: 5,
        min: 1,
        max: 20
      },
      {
        key: 'return_destroy_materials',
        label: 'Return/Destroy Materials Required',
        type: 'boolean',
        required: false,
        helperText: 'Confidential materials must be returned or destroyed',
        defaultValue: true
      },
      {
        key: 'permitted_disclosures',
        label: 'Permitted Disclosure Exceptions',
        type: 'array',
        required: false,
        helperText: 'Comma-separated exceptions (e.g., Legal Requirement, Court Order)',
        defaultValue: ['Legal Requirement', 'Court Order']
      }
    ],
    recommendationTemplate: 'Confidentiality period should be at least {confidentiality_period_years} years with material return/destruction'
  },
  {
    id: 'insurance',
    name: 'Insurance Requirements',
    description: 'Required insurance coverage',
    category: 'Insurance',
    fields: [
      {
        key: 'general_liability_min',
        label: 'General Liability Minimum',
        type: 'currency',
        required: true,
        placeholder: '1000000',
        helperText: 'Minimum general liability coverage',
        defaultValue: 1000000
      },
      {
        key: 'professional_liability_min',
        label: 'Professional Liability Minimum',
        type: 'currency',
        required: false,
        placeholder: '1000000',
        helperText: 'Minimum E&O/professional liability coverage',
        defaultValue: 1000000
      },
      {
        key: 'currency',
        label: 'Currency',
        type: 'select',
        required: true,
        options: [
          { value: 'USD', label: 'USD' },
          { value: 'EUR', label: 'EUR' },
          { value: 'GBP', label: 'GBP' }
        ],
        defaultValue: 'USD'
      },
      {
        key: 'certificate_required',
        label: 'Certificate of Insurance Required',
        type: 'boolean',
        required: false,
        helperText: 'Certificate must be provided',
        defaultValue: true
      }
    ],
    recommendationTemplate: 'Require minimum {general_liability_min} {currency} general liability coverage'
  },
  {
    id: 'required_clauses',
    name: 'Required Clauses',
    description: 'Contract must include specific clauses',
    category: 'Compliance',
    fields: [
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'required_clause', label: 'Required Clause' }
        ],
        defaultValue: 'required_clause',
        helperText: 'Type of validation'
      },
      {
        key: 'must_include',
        label: 'Required Clauses (comma-separated)',
        type: 'array',
        required: true,
        helperText: 'E.g., customer_owns_data, export_rights, deletion_rights',
        defaultValue: []
      }
    ],
    recommendationTemplate: 'Ensure contract includes all required clauses: {must_include}'
  },
  {
    id: 'allowed_list',
    name: 'Allowed Values List',
    description: 'Only specific values are acceptable',
    category: 'Compliance',
    fields: [
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'list', label: 'List' }
        ],
        defaultValue: 'list',
        helperText: 'Type of validation'
      },
      {
        key: 'allowed',
        label: 'Allowed Values (comma-separated)',
        type: 'array',
        required: true,
        helperText: 'E.g., gross_negligence, willful_misconduct, ip_infringement',
        defaultValue: []
      },
      {
        key: 'max_items',
        label: 'Maximum Number of Items',
        type: 'number',
        required: false,
        helperText: 'Optional limit on how many from the list',
        min: 1,
        max: 20
      }
    ],
    recommendationTemplate: 'Only the following values are acceptable: {allowed}'
  },
  {
    id: 'required_list',
    name: 'Required Items from List',
    description: 'Must include specific items, may include additional',
    category: 'Compliance',
    fields: [
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'list', label: 'List' }
        ],
        defaultValue: 'list',
        helperText: 'Type of validation'
      },
      {
        key: 'required',
        label: 'Required Items (comma-separated)',
        type: 'array',
        required: true,
        helperText: 'E.g., SOC2, ISO27001',
        defaultValue: []
      },
      {
        key: 'preferred',
        label: 'Preferred Additional Items (comma-separated)',
        type: 'array',
        required: false,
        helperText: 'E.g., GDPR, HIPAA',
        defaultValue: []
      }
    ],
    recommendationTemplate: 'Must include: {required}. Preferably also: {preferred}'
  },
  {
    id: 'range_with_preferred',
    name: 'Range with Preferred Value',
    description: 'Min/max range with preferred target',
    category: 'Financial',
    fields: [
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'range', label: 'Range' }
        ],
        defaultValue: 'range',
        helperText: 'Type of validation'
      },
      {
        key: 'min',
        label: 'Minimum Value',
        type: 'number',
        required: true,
        defaultValue: 0,
        helperText: 'Minimum acceptable value'
      },
      {
        key: 'max',
        label: 'Maximum Value',
        type: 'number',
        required: true,
        defaultValue: 100,
        helperText: 'Maximum acceptable value'
      },
      {
        key: 'preferred',
        label: 'Preferred Value',
        type: 'number',
        required: false,
        helperText: 'Ideal target value within the range'
      },
      {
        key: 'unit',
        label: 'Unit',
        type: 'text',
        required: false,
        helperText: 'E.g., days, months, percent, dollars',
        placeholder: 'days'
      }
    ],
    recommendationTemplate: 'Value should be between {min} and {max} {unit}, preferably {preferred}'
  },
  {
    id: 'security_certifications',
    name: 'Security Certifications',
    description: 'Required security standards and certifications',
    category: 'Security',
    fields: [
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'list', label: 'List' }
        ],
        defaultValue: 'list',
        helperText: 'Type of validation'
      },
      {
        key: 'required',
        label: 'Required Certifications (comma-separated)',
        type: 'array',
        required: true,
        helperText: 'E.g., SOC2, ISO27001',
        defaultValue: ['SOC2', 'ISO27001']
      },
      {
        key: 'preferred',
        label: 'Preferred Additional Certifications (comma-separated)',
        type: 'array',
        required: false,
        helperText: 'E.g., GDPR, HIPAA, PCI-DSS',
        defaultValue: []
      }
    ],
    recommendationTemplate: 'Vendor must maintain {required} certifications. Preferably also: {preferred}'
  },
  {
    id: 'multi_tier_insurance',
    name: 'Multi-Tier Insurance Requirements',
    description: 'Different insurance types with minimum coverage',
    category: 'Insurance',
    fields: [
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        required: true,
        options: [
          { value: 'object', label: 'Object' }
        ],
        defaultValue: 'object',
        helperText: 'Type of validation'
      },
      {
        key: 'general_liability.min',
        label: 'General Liability Minimum',
        type: 'currency',
        required: true,
        defaultValue: 1000000,
        helperText: 'Minimum general liability coverage'
      },
      {
        key: 'general_liability.preferred',
        label: 'General Liability Preferred',
        type: 'currency',
        required: false,
        defaultValue: 2000000,
        helperText: 'Preferred general liability coverage'
      },
      {
        key: 'cyber_liability.min',
        label: 'Cyber Liability Minimum',
        type: 'currency',
        required: false,
        defaultValue: 1000000,
        helperText: 'Minimum cyber liability coverage'
      },
      {
        key: 'cyber_liability.preferred',
        label: 'Cyber Liability Preferred',
        type: 'currency',
        required: false,
        defaultValue: 5000000,
        helperText: 'Preferred cyber liability coverage'
      }
    ],
    recommendationTemplate: 'Require minimum ${general_liability.min} general liability and ${cyber_liability.min} cyber liability coverage'
  },
  {
    id: 'custom',
    name: 'Custom Standard',
    description: 'Create a custom standard with flexible fields',
    category: 'Custom',
    fields: [
      {
        key: 'custom_rules',
        label: 'Custom Rules',
        type: 'text',
        required: false,
        helperText: 'Define custom rules as free-form text or key-value pairs',
        defaultValue: ''
      }
    ],
    recommendationTemplate: 'Review custom terms with legal team'
  }
];

interface AcceptableValuesInputProps {
  value: Record<string, any>;
  onChange: (value: Record<string, any>) => void;
  category?: string;
  termName?: string;
  onTemplateSelect?: (template: StandardTemplate | null) => void;
}

export default function AcceptableValuesInput({
  value,
  onChange,
  category = '',
  termName = '',
  onTemplateSelect
}: AcceptableValuesInputProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<StandardTemplate | null>(null);
  const [showJsonEditor, setShowJsonEditor] = useState(false);
  const [jsonText, setJsonText] = useState(JSON.stringify(value || {}, null, 2));

  // Auto-detect template based on category and term name
  useEffect(() => {
    if (!selectedTemplate && (category || termName)) {
      const detected = STANDARD_TEMPLATES.find(t =>
        t.category.toLowerCase() === category.toLowerCase() ||
        t.name.toLowerCase() === termName.toLowerCase()
      );
      if (detected) {
        setSelectedTemplate(detected);
        // Initialize with default values if value is empty
        if (!value || Object.keys(value).length === 0) {
          const defaults: Record<string, any> = {};
          detected.fields.forEach(field => {
            if (field.defaultValue !== undefined) {
              defaults[field.key] = field.defaultValue;
            }
          });
          onChange(defaults);
        }
      }
    }
  }, [category, termName, selectedTemplate, value, onChange]);

  const handleTemplateChange = (templateId: string) => {
    const template = STANDARD_TEMPLATES.find(t => t.id === templateId);
    setSelectedTemplate(template || null);

    if (template) {
      // Initialize with default values
      const defaults: Record<string, any> = {};
      template.fields.forEach(field => {
        if (field.defaultValue !== undefined) {
          defaults[field.key] = field.defaultValue;
        }
      });
      onChange(defaults);

      // Notify parent component of template selection
      if (onTemplateSelect) {
        onTemplateSelect(template);
      }
    } else {
      onChange({});
      if (onTemplateSelect) {
        onTemplateSelect(null);
      }
    }
  };

  const handleFieldChange = (key: string, fieldValue: any) => {
    // Handle nested keys like "general_liability.min"
    if (key.includes('.')) {
      const parts = key.split('.');
      const newValue = { ...value };

      // Navigate to the nested object
      let current = newValue;
      for (let i = 0; i < parts.length - 1; i++) {
        if (!current[parts[i]] || typeof current[parts[i]] !== 'object') {
          current[parts[i]] = {};
        }
        current = current[parts[i]];
      }

      // Set the final value
      current[parts[parts.length - 1]] = fieldValue;
      onChange(newValue);
    } else {
      onChange({
        ...value,
        [key]: fieldValue
      });
    }
  };

  const handleJsonChange = (newJson: string) => {
    setJsonText(newJson);
    try {
      const parsed = JSON.parse(newJson);
      onChange(parsed);
    } catch {
      // Allow invalid JSON while typing
    }
  };

  const renderField = (field: FieldDefinition) => {
    // Handle nested keys like "general_liability.min"
    let currentValue = field.defaultValue;
    if (field.key.includes('.')) {
      const parts = field.key.split('.');
      let current: any = value;
      for (const part of parts) {
        if (current && typeof current === 'object' && part in current) {
          current = current[part];
        } else {
          current = undefined;
          break;
        }
      }
      currentValue = current ?? field.defaultValue;
    } else {
      currentValue = value?.[field.key] ?? field.defaultValue;
    }

    switch (field.type) {
      case 'boolean':
        return (
          <div key={field.key} className="flex items-center gap-2">
            <input
              type="checkbox"
              id={field.key}
              checked={currentValue || false}
              onChange={(e) => handleFieldChange(field.key, e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor={field.key} className="text-sm font-medium">
              {field.label}
            </label>
            {field.helperText && (
              <span className="text-xs text-muted ml-2">({field.helperText})</span>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.key}>
            <label className="label">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <select
              value={currentValue || ''}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              className="input-field"
              required={field.required}
            >
              <option value="">Select...</option>
              {field.options?.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {field.helperText && (
              <p className="text-xs text-muted mt-1">{field.helperText}</p>
            )}
          </div>
        );

      case 'currency':
      case 'number':
        return (
          <div key={field.key}>
            <label className="label">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <input
              type="number"
              value={currentValue ?? ''}
              onChange={(e) => handleFieldChange(field.key, parseFloat(e.target.value) || 0)}
              className="input-field"
              placeholder={field.placeholder}
              required={field.required}
              min={field.min}
              max={field.max}
            />
            {field.helperText && (
              <p className="text-xs text-muted mt-1">{field.helperText}</p>
            )}
          </div>
        );

      case 'array':
        return (
          <div key={field.key}>
            <label className="label">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <input
              type="text"
              value={Array.isArray(currentValue) ? currentValue.join(', ') : currentValue || ''}
              onChange={(e) => handleFieldChange(
                field.key,
                e.target.value.split(',').map(v => v.trim()).filter(v => v)
              )}
              className="input-field"
              placeholder={field.placeholder}
              required={field.required}
            />
            {field.helperText && (
              <p className="text-xs text-muted mt-1">{field.helperText}</p>
            )}
          </div>
        );

      case 'date':
        return (
          <div key={field.key}>
            <label className="label">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <input
              type="date"
              value={currentValue || ''}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              className="input-field"
              required={field.required}
            />
            {field.helperText && (
              <p className="text-xs text-muted mt-1">{field.helperText}</p>
            )}
          </div>
        );

      case 'text':
      default:
        return (
          <div key={field.key}>
            <label className="label">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <input
              type="text"
              value={currentValue || ''}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              className="input-field"
              placeholder={field.placeholder}
              required={field.required}
            />
            {field.helperText && (
              <p className="text-xs text-muted mt-1">{field.helperText}</p>
            )}
          </div>
        );
    }
  };

  return (
    <div className="space-y-4">
      {/* Template Selector */}
      <div>
        <label className="label">
          Standard Template
        </label>
        <select
          value={selectedTemplate?.id || ''}
          onChange={(e) => handleTemplateChange(e.target.value)}
          className="input-field"
        >
          <option value="">Select a template...</option>
          {STANDARD_TEMPLATES.map(template => (
            <option key={template.id} value={template.id}>
              {template.name} - {template.description}
            </option>
          ))}
        </select>
        <p className="text-xs text-muted mt-1">
          Choose a pre-configured template or create a custom standard
        </p>
      </div>

      {/* Toggle between form and JSON */}
      <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <span className="text-xs font-medium text-gray-600 mr-2">View Mode:</span>
        <button
          type="button"
          onClick={() => setShowJsonEditor(false)}
          className={`text-sm px-4 py-2 rounded-md font-medium transition-all ${
            !showJsonEditor
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
          }`}
        >
          Form View
        </button>
        <button
          type="button"
          onClick={() => {
            setShowJsonEditor(true);
            setJsonText(JSON.stringify(value || {}, null, 2));
          }}
          className={`text-sm px-4 py-2 rounded-md font-medium transition-all ${
            showJsonEditor
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
          }`}
        >
          JSON View (Advanced)
        </button>
      </div>

      {/* Form Fields or JSON Editor */}
      {showJsonEditor ? (
        <div>
          <label className="label">
            Acceptable Values (JSON)
          </label>
          <textarea
            value={jsonText}
            onChange={(e) => handleJsonChange(e.target.value)}
            className="input-field font-mono text-sm"
            rows={8}
            placeholder='{"key": "value"}'
          />
          <p className="text-xs text-muted mt-1">
            Advanced: Edit the raw JSON structure
          </p>
        </div>
      ) : selectedTemplate ? (
        <div className="space-y-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
          <div className="text-sm font-medium text-gray-700">
            {selectedTemplate.name} Fields
          </div>
          {selectedTemplate.fields.map(field => renderField(field))}
        </div>
      ) : (
        <div className="p-4 border border-gray-200 rounded-lg bg-gray-50 text-center text-muted">
          Select a template above to configure acceptable values
        </div>
      )}
    </div>
  );
}
