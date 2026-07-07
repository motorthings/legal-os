'use client';

/**
 * Display acceptable values in a human-readable format
 */
export default function AcceptableValuesDisplay({
  value,
  compact = false
}: {
  value: Record<string, any>;
  compact?: boolean;
}) {
  if (!value || Object.keys(value).length === 0) {
    return <span className="text-muted text-sm">No criteria defined</span>;
  }

  // Format currency values
  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  // Format arrays as comma-separated lists
  const formatArray = (arr: any[]) => {
    if (!Array.isArray(arr)) return String(arr);
    return arr.join(', ');
  };

  // Format boolean values
  const formatBoolean = (val: boolean) => {
    return val ? 'Yes' : 'No';
  };

  // Format field name for display
  const formatFieldName = (key: string) => {
    return key
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Smart formatting based on common patterns
  const formatValue = (key: string, val: any): string => {
    if (val === null || val === undefined) return 'Not set';

    // Handle currency amounts
    if (key.includes('amount') || key.includes('min') || key.includes('max') || key.includes('liability')) {
      const currency = value.currency || value.Currency || 'USD';
      if (typeof val === 'number') {
        return formatCurrency(val, currency);
      }
    }

    // Handle arrays
    if (Array.isArray(val)) {
      return formatArray(val);
    }

    // Handle booleans
    if (typeof val === 'boolean') {
      return formatBoolean(val);
    }

    // Handle days/periods
    if (key.includes('days') || key.includes('period') || key.includes('hours')) {
      return `${val} ${key.includes('hours') ? 'hours' : 'days'}`;
    }

    // Handle years
    if (key.includes('years')) {
      return `${val} years`;
    }

    // Default string conversion
    return String(val);
  };

  // Generate summary text for common patterns
  const generateSummary = (): string | null => {
    // Type-based patterns
    const type = value.type;

    // Range pattern
    if (type === 'range' && value.min !== undefined && value.max !== undefined) {
      const unit = value.unit || '';
      const preferred = value.preferred !== undefined ? ` (preferred: ${value.preferred})` : '';
      return `${value.min}-${value.max} ${unit}${preferred}`.trim();
    }

    // List with allowed values
    if (type === 'list' && value.allowed) {
      const items = Array.isArray(value.allowed) ? value.allowed : [];
      const maxItems = value.max_items ? ` (max ${value.max_items})` : '';
      return `Allowed: ${items.join(', ')}${maxItems}`;
    }

    // List with required values
    if (type === 'list' && value.required) {
      const required = Array.isArray(value.required) ? value.required : [];
      const preferred = Array.isArray(value.preferred) ? value.preferred : [];
      let summary = `Required: ${required.join(', ')}`;
      if (preferred.length > 0) {
        summary += ` | Preferred: ${preferred.join(', ')}`;
      }
      return summary;
    }

    // Required clause pattern
    if (type === 'required_clause' && value.must_include) {
      const items = Array.isArray(value.must_include) ? value.must_include : [];
      return `Must include: ${items.join(', ')}`;
    }

    // Boolean required
    if (type === 'boolean' && value.required !== undefined) {
      return value.required ? 'Required: Yes' : 'Required: No';
    }

    // Object with nested insurance values
    if (type === 'object' && (value.general_liability || value.cyber_liability)) {
      const parts = [];
      if (value.general_liability?.min) {
        parts.push(`GL: $${value.general_liability.min.toLocaleString()}`);
      }
      if (value.cyber_liability?.min) {
        parts.push(`Cyber: $${value.cyber_liability.min.toLocaleString()}`);
      }
      return parts.join(' | ');
    }

    // Legacy patterns (backward compatibility)

    // Liability cap pattern
    if (value.min_amount !== undefined && value.max_amount !== undefined) {
      const currency = value.currency || 'USD';
      const min = formatCurrency(value.min_amount, currency);
      const max = formatCurrency(value.max_amount, currency);
      if (value.unlimited_acceptable) {
        return `${min} - ${max} (unlimited acceptable)`;
      }
      return `${min} - ${max}`;
    }

    // Payment terms pattern
    if (value.max_payment_days !== undefined) {
      let summary = `Net ${value.max_payment_days} days`;
      if (value.advance_payment_required) {
        summary += ' (advance payment required)';
      }
      return summary;
    }

    // Notice period pattern
    if (value.min_notice_days !== undefined && value.max_notice_days !== undefined) {
      return `${value.min_notice_days}-${value.max_notice_days} days notice`;
    }

    // Insurance pattern
    if (value.general_liability_min !== undefined) {
      const currency = value.currency || 'USD';
      const amount = formatCurrency(value.general_liability_min, currency);
      return `General liability: ${amount}`;
    }

    // Confidentiality pattern
    if (value.confidentiality_period_years !== undefined) {
      return `${value.confidentiality_period_years} year confidentiality`;
    }

    // Data breach notification
    if (value.data_breach_notification_hours !== undefined) {
      return `Breach notification: ${value.data_breach_notification_hours} hours`;
    }

    return null;
  };

  const summary = generateSummary();

  // Compact mode: show only summary
  if (compact && summary) {
    return (
      <div className="text-sm text-primary">
        {summary}
      </div>
    );
  }

  // Full mode: show all key-value pairs
  return (
    <div className="space-y-1">
      {summary && (
        <div className="text-sm font-medium text-primary mb-2">
          {summary}
        </div>
      )}
      {!compact && (
        <div className="grid grid-cols-1 gap-1 text-xs">
          {Object.entries(value).map(([key, val]) => {
            // Skip currency if it's already shown in amounts
            if (key === 'currency' && summary?.includes(value.currency)) {
              return null;
            }

            return (
              <div key={key} className="flex gap-2">
                <span className="text-muted font-medium min-w-[120px]">
                  {formatFieldName(key)}:
                </span>
                <span className="text-primary">
                  {formatValue(key, val)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
